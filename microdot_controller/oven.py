import asyncio
import time
import random
import datetime
import logging
import json
import config
from max31855 import MAX31855, MAX31855Error
from timezone import BRT_TZ
from device_status import get_board_temperature, get_disk_status, get_memory_status
from ring_buffer import RingBuffer

log = logging.getLogger(__name__)
log.info("Initializing Oven")

from machine import Pin, PWM
gpio_heat = Pin(config.gpio_heat, Pin.OUT)
pwm_heat = PWM(gpio_heat)
pwm_heat.freq(60)
pwm_heat.duty(0)  # Set initial duty cycle to 0

def set_heat_duty(value: float):
    log.info("Setting heat duty to %.2f" % value)
    value*=1023
    if value < 0:
        value = 0
    elif value > 1023:
        value = 1023
    pwm_heat.duty(int(value))

class Oven:
    STATE_IDLE = "IDLE"
    STATE_RUNNING = "RUNNING"

    def __init__(
        self,
        time_step=config.sensor_time_wait,
        temperature_oversamples=config.temperature_oversamples,
        temperature_averaging_window=config.temperature_averaging_window
    ):
        self.time_step = time_step
        self.reset()
        self.runtime = 0

        self.temp_sensor = TempSensorReal(
            self.time_step,
            temperature_oversamples=temperature_oversamples,
            temperature_averaging_window=temperature_averaging_window
        )
        # Start tasks for the sensor and oven loop
        asyncio.create_task(self.temp_sensor.run())
        asyncio.create_task(self.run())

    @property
    def heat(self):
        return pwm_heat.duty()/1023

    @heat.setter
    def heat(self, value):
        return set_heat_duty(value)

    def reset(self):
        self.profile = None
        self.start_time = datetime.datetime.now(BRT_TZ)
        self.runtime = 0
        self.totaltime = 0
        self.target = 0
        self.state = Oven.STATE_IDLE
        self.heat = 0.0
        self.cool = 0.0
        self.air = 0.0
        self.pid = PID(ki=config.pid_ki, kd=config.pid_kd, kp=config.pid_kp)

    def run_profile(self, profile):
        log.info("Running profile %s" % profile.name)
        self.profile = profile
        self.totaltime = profile.get_duration()
        self.state = Oven.STATE_RUNNING
        self.start_time = datetime.datetime.now(BRT_TZ)
        log.info("Starting")

    def abort_run(self):
        self.reset()

    async def run(self):
        temperature_count = 0
        last_temp = 0
        pid_value = 0
        while True:
            if self.state == Oven.STATE_RUNNING:
                runtime_delta = (datetime.datetime.now(BRT_TZ) - self.start_time).total_seconds()
                self.runtime = runtime_delta
                log.info("running at %.1f deg C (Target: %.1f), heat %.2f, cool %.2f, air %.2f (%.1fs/%.0f)" %
                         (self.temp_sensor.temperature, self.target, self.heat, self.cool, self.air, self.runtime, self.totaltime))
                log.debug(f" >>> Profile <<<  {self.profile}")
                log.debug(f" >>> Runtime <<<  {self.runtime}")
                self.target = self.profile.get_target_temperature(self.runtime) if self.profile else 0
                pid_value = self.pid.compute(self.target, self.temp_sensor.temperature)

                log.info("pid: %.3f" % pid_value)

                if pid_value > 0:
                    if last_temp == self.temp_sensor.temperature:
                        temperature_count += 1
                    else:
                        temperature_count = 0
                    if temperature_count > 20:
                        log.info("Error reading sensor, oven temp not responding to heat.")
                        self.reset()
                else:
                    temperature_count = 0

                last_temp = self.temp_sensor.temperature

                self.heat = pid_value

                log.debug(f"+++ Debug_times +++ runtime: {self.runtime}, totaltime: {self.totaltime}")
                if self.runtime >= self.totaltime and self.totaltime > 0:
                    log.info("Profile finished, resetting oven")
                    self.reset()

            await asyncio.sleep(self.time_step)

    def get_state(self):
        oven_state = {
            'runtime': self.runtime,
            'temperature': self.temp_sensor.temperature,
            'target': self.target,
            'state': self.state,
            'heat': self.heat,
            'cool': self.cool,
            'air': self.air,
            'totaltime': self.totaltime,
        }
        oven_state["boardTemperature"] = get_board_temperature()
        oven_state.update(get_disk_status())
        oven_state.update(get_memory_status())
        pid_state = self.pid.state.to_dict() if (self.pid and self.pid.state) else {}
        oven_state.update(pid_state)
        return oven_state


class TempSensorReal:
    def __init__(self, time_step, temperature_oversamples, temperature_averaging_window):
        self.temperature = 0
        self.time_step = time_step
        self.temperature_oversamples = temperature_oversamples
        self.temperature_averaging_window = temperature_averaging_window
        self.thermocouple = MAX31855(
            config.gpio_sensor_cs,
            config.gpio_sensor_clock,
            config.gpio_sensor_data,
            config.gpio_thermocouple_vdd,
            config.gpio_thermocouple_gnd,
            config.temp_scale
        )
        self.ring_buffer = RingBuffer(self.temperature_averaging_window)
    async def run(self):
        while True:
            try:
                self.ring_buffer.add(self.thermocouple.get())
                self.temperature = self.ring_buffer.average()
            except Exception as e:
                log.exception("problem reading temp", exc_info=e)
            await asyncio.sleep(self.time_step/self.temperature_oversamples)

class Profile:
    def __init__(self, json_data):
        obj = json.loads(json_data)
        self.name = obj["name"]
        self.data = sorted(obj["data"])

    def get_duration(self):
        return max([t for (t, x) in self.data])

    def get_surrounding_points(self, time_val):
        if time_val > self.get_duration():
            return (None, None)
        prev_point = None
        next_point = None
        for i in range(len(self.data)):
            if time_val < self.data[i][0]:
                prev_point = self.data[i-1]
                next_point = self.data[i]
                break
        return (prev_point, next_point)

    def is_rising(self, time_val):
        (prev_point, next_point) = self.get_surrounding_points(time_val)
        if prev_point and next_point:
            return prev_point[1] < next_point[1]
        else:
            return False

    def get_target_temperature(self, time_val):
        log.debug(f"=== entering get_target_temperature with time_val: {time_val} ===")
        if time_val > self.get_duration():
            return 0
        (prev_point, next_point) = self.get_surrounding_points(time_val)
        if (prev_point is None) and (next_point is None):
            log.debug("No surrounding points found, returning 0")
            return 0
        incl = float(next_point[1] - prev_point[1]) / float(next_point[0] - prev_point[0])
        temp = prev_point[1] + (time_val - prev_point[0]) * incl
        return temp

class PIDState:
    def __init__(self, kp, kd, ki, err, dErr, iErr, pTerm, dTerm, iTerm, raw_out, bounded_out):
        self.kp = kp
        self.kd = kd
        self.ki = ki
        self.err = err
        self.dErr = dErr
        self.iErr = iErr
        self.pTerm = pTerm
        self.dTerm = dTerm
        self.iTerm = iTerm
        self.raw_out = raw_out
        self.bounded_out = bounded_out

    def to_dict(self):
        return {
            'kp': self.kp,
            'kd': self.kd,
            'ki': self.ki,
            'err': self.err,
            'dErr': self.dErr,
            'iErr': self.iErr,
            'pTerm': self.pTerm,
            'dTerm': self.dTerm,
            'iTerm': self.iTerm,
            'raw_out': self.raw_out,
            'bounded_out': self.bounded_out
        }
class PID:
    def __init__(self, ki=1, kp=1, kd=1):
        self.ki = ki
        self.kp = kp
        self.kd = kd
        self.lastNow = datetime.datetime.now(BRT_TZ)
        self.iterm = 0
        self.lastErr = 0
        self._iErr = 0
        self.state: PIDState = None

    def compute(self, setpoint, ispoint):
        now = datetime.datetime.now(BRT_TZ)
        timeDelta = (now - self.lastNow).total_seconds()
        error = float(setpoint - ispoint)
        self.iterm += (error * timeDelta * self.ki)
        self.iterm = sorted([-1, self.iterm, 1])[1]
        self._iErr += error * timeDelta
        dErr = (error - self.lastErr) / timeDelta
        pTerm = self.kp * error
        dTerm = self.kd * dErr
        output = pTerm + self.iterm + dTerm
        output = sorted([-1, output, 1])[1]
        self.lastErr = error
        self.lastNow = now
        self.state = PIDState(
            kp=self.kp,
            kd=self.kd,
            ki=self.ki,
            err=error,
            dErr=dErr,
            iErr=self._iErr,
            pTerm=pTerm,
            dTerm=dTerm,
            iTerm=self.iterm,
            raw_out=self.kp * error + self._iErr * self.ki + self.kd * dErr,
            bounded_out=output
        )
        return output
