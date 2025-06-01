import asyncio
import time
import random
import datetime
import logging
import json
import config

log = logging.getLogger(__name__)
log.info("Initializing Oven")

try:
    if config.max31855 + config.max6675 + config.max31855spi > 1:
        log.error("choose (only) one converter IC")
        exit()
    if config.max31855:
        from max31855 import MAX31855, MAX31855Error
        log.info("import MAX31855")
    if config.max31855spi:
        import Adafruit_GPIO.SPI as SPI
        from max31855spi import MAX31855SPI, MAX31855SPIError
        log.info("import MAX31855SPI")
        spi_reserved_gpio = [7, 8, 9, 10, 11]
        if config.gpio_air in spi_reserved_gpio:
            raise Exception("gpio_air pin %s collides with SPI pins %s" % (config.gpio_air, spi_reserved_gpio))
        if config.gpio_cool in spi_reserved_gpio:
            raise Exception("gpio_cool pin %s collides with SPI pins %s" % (config.gpio_cool, spi_reserved_gpio))
        if config.gpio_door in spi_reserved_gpio:
            raise Exception("gpio_door pin %s collides with SPI pins %s" % (config.gpio_door, spi_reserved_gpio))
        if config.gpio_heat in spi_reserved_gpio:
            raise Exception("gpio_heat pin %s collides with SPI pins %s" % (config.gpio_heat, spi_reserved_gpio))
    if config.max6675:
        from max6675 import MAX6675, MAX6675Error
        log.info("import MAX6675")
    sensor_available = True
except ImportError:
    log.exception("Could not initialize temperature sensor, using dummy values!")
    sensor_available = False

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(config.gpio_heat, GPIO.OUT)
    GPIO.setup(config.gpio_cool, GPIO.OUT)
    GPIO.setup(config.gpio_air, GPIO.OUT)
    GPIO.setup(config.gpio_door, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    gpio_available = True
except ImportError:
    log.warning("Could not initialize GPIOs, oven operation will only be simulated!")
    gpio_available = False


class Oven:
    STATE_IDLE = "IDLE"
    STATE_RUNNING = "RUNNING"

    def __init__(self, simulate=False, time_step=config.sensor_time_wait):
        self.simulate = simulate
        self.time_step = time_step
        self.reset()
        self.runtime = 0
        # Initialize temperature sensor based on availability
        if simulate:
            self.temp_sensor = TempSensorSimulate(self, 0.5, self.time_step)
        elif sensor_available:
            self.temp_sensor = TempSensorReal(self.time_step)
        else:
            self.temp_sensor = TempSensorSimulate(self, self.time_step, self.time_step)
        # Start tasks for the sensor and oven loop
        asyncio.create_task(self.temp_sensor.run())
        asyncio.create_task(self.run())

    def reset(self):
        self.profile = None
        self.start_time = datetime.datetime.now()
        self.runtime = 0
        self.totaltime = 0
        self.target = 0
        self.door = self.get_door_state()
        self.state = Oven.STATE_IDLE
        self.heat = 0.0
        self.cool = 0.0
        self.air = 0.0
        self.pid = PID(ki=config.pid_ki, kd=config.pid_kd, kp=config.pid_kp)
        # Reset actuators
        self.set_heat(0)
        self.set_cool(False)
        self.set_air(False)

    def run_profile(self, profile):
        log.info("Running profile %s" % profile.name)
        self.profile = profile
        self.totaltime = profile.get_duration()
        self.state = Oven.STATE_RUNNING
        self.start_time = datetime.datetime.now()
        log.info("Starting")

    def abort_run(self):
        self.reset()

    async def run(self):
        temperature_count = 0
        last_temp = 0
        pid_value = 0
        while True:
            self.door = self.get_door_state()

            if self.state == Oven.STATE_RUNNING:
                if self.simulate:
                    self.runtime += 0.5
                else:
                    runtime_delta = (datetime.datetime.now() - self.start_time).total_seconds()
                    self.runtime = runtime_delta
                log.info("running at %.1f deg C (Target: %.1f), heat %.2f, cool %.2f, air %.2f, door %s (%.1fs/%.0f)" %
                         (self.temp_sensor.temperature, self.target, self.heat, self.cool, self.air, self.door, self.runtime, self.totaltime))
                self.target = self.profile.get_target_temperature(self.runtime) if self.profile else 0
                pid_value = self.pid.compute(self.target, self.temp_sensor.temperature)

                log.info("pid: %.3f" % pid_value)

                self.set_cool(pid_value <= -1)
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

                self.set_heat(pid_value)

                if self.temp_sensor.temperature > 200:
                    self.set_air(False)
                elif self.temp_sensor.temperature < 180:
                    self.set_air(True)

                if self.runtime >= self.totaltime and self.totaltime > 0:
                    self.reset()

            if pid_value > 0:
                await asyncio.sleep(self.time_step * (1 - pid_value))
            else:
                await asyncio.sleep(self.time_step)

    def set_heat(self, value):
        if value > 0:
            self.heat = 1.0
            if gpio_available:
                if config.heater_invert:
                    GPIO.output(config.gpio_heat, GPIO.LOW)
                    # For blocking operations inside an async loop, consider using asyncio.sleep()
                    time.sleep(self.time_step * value)
                    GPIO.output(config.gpio_heat, GPIO.HIGH)
                else:
                    GPIO.output(config.gpio_heat, GPIO.HIGH)
                    time.sleep(self.time_step * value)
                    GPIO.output(config.gpio_heat, GPIO.LOW)
        else:
            self.heat = 0.0
            if gpio_available:
                if config.heater_invert:
                    GPIO.output(config.gpio_heat, GPIO.HIGH)
                else:
                    GPIO.output(config.gpio_heat, GPIO.LOW)

    def set_cool(self, value):
        if value:
            self.cool = 1.0
            if gpio_available:
                GPIO.output(config.gpio_cool, GPIO.LOW)
        else:
            self.cool = 0.0
            if gpio_available:
                GPIO.output(config.gpio_cool, GPIO.HIGH)

    def set_air(self, value):
        if value:
            self.air = 1.0
            if gpio_available:
                GPIO.output(config.gpio_air, GPIO.LOW)
        else:
            self.air = 0.0
            if gpio_available:
                GPIO.output(config.gpio_air, GPIO.HIGH)

    def get_state(self):
        return {
            'runtime': self.runtime,
            'temperature': self.temp_sensor.temperature,
            'target': self.target,
            'state': self.state,
            'heat': self.heat,
            'cool': self.cool,
            'air': self.air,
            'totaltime': self.totaltime,
            'door': self.door
        }

    def get_door_state(self):
        if gpio_available:
            return "OPEN" if GPIO.input(config.gpio_door) else "CLOSED"
        else:
            return "UNKNOWN"


class TempSensor:
    def __init__(self, time_step):
        self.temperature = 0
        self.time_step = time_step

    async def run(self):
        # To be implemented by subclasses
        pass


class TempSensorReal(TempSensor):
    def __init__(self, time_step):
        super().__init__(time_step)
        if config.max6675:
            log.info("init MAX6675")
            self.thermocouple = MAX6675(config.gpio_sensor_cs,
                                        config.gpio_sensor_clock,
                                        config.gpio_sensor_data,
                                        config.temp_scale)
        elif config.max31855:
            log.info("init MAX31855")
            self.thermocouple = MAX31855(config.gpio_sensor_cs,
                                         config.gpio_sensor_clock,
                                         config.gpio_sensor_data,
                                         config.temp_scale)
        elif config.max31855spi:
            log.info("init MAX31855-spi")
            self.thermocouple = MAX31855SPI(spi_dev=SPI.SpiDev(port=0, device=config.spi_sensor_chip_id))

    async def run(self):
        while True:
            try:
                self.temperature = self.thermocouple.get()
            except Exception:
                log.exception("problem reading temp")
            await asyncio.sleep(self.time_step)


class TempSensorSimulate(TempSensor):
    def __init__(self, oven, time_step, sleep_time):
        super().__init__(time_step)
        self.oven = oven
        self.sleep_time = sleep_time

    async def run(self):
        t_env      = config.sim_t_env
        c_heat     = config.sim_c_heat
        c_oven     = config.sim_c_oven
        p_heat     = config.sim_p_heat
        R_o_nocool = config.sim_R_o_nocool
        R_o_cool   = config.sim_R_o_cool
        R_ho_noair = config.sim_R_ho_noair
        R_ho_air   = config.sim_R_ho_air

        t = t_env   # Oven temperature
        t_h = t     # Heat element temperature
        while True:
            Q_h = p_heat * self.time_step * self.oven.heat
            t_h += Q_h / c_heat
            R_ho = R_ho_air if self.oven.air else R_ho_noair
            p_ho = (t_h - t) / R_ho
            t   += p_ho * self.time_step / c_oven
            t_h -= p_ho * self.time_step / c_heat
            p_env = ((t - t_env) / R_o_cool) if self.oven.cool else ((t - t_env) / R_o_nocool)
            t -= p_env * self.time_step / c_oven
            log.debug("energy sim: -> %dW heater: %.0f -> %dW oven: %.0f -> %dW env" %
                      (int(p_heat * self.oven.heat), t_h, int(p_ho), t, int(p_env)))
            self.temperature = t
            await asyncio.sleep(self.sleep_time)


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
        if time_val > self.get_duration():
            return 0
        (prev_point, next_point) = self.get_surrounding_points(time_val)
        incl = float(next_point[1] - prev_point[1]) / float(next_point[0] - prev_point[0])
        temp = prev_point[1] + (time_val - prev_point[0]) * incl
        return temp


class PID:
    def __init__(self, ki=1, kp=1, kd=1):
        self.ki = ki
        self.kp = kp
        self.kd = kd
        self.lastNow = datetime.datetime.now()
        self.iterm = 0
        self.lastErr = 0

    def compute(self, setpoint, ispoint):
        now = datetime.datetime.now()
        timeDelta = (now - self.lastNow).total_seconds()
        error = float(setpoint - ispoint)
        self.iterm += (error * timeDelta * self.ki)
        self.iterm = sorted([-1, self.iterm, 1])[1]
        dErr = (error - self.lastErr) / timeDelta
        output = self.kp * error + self.iterm + self.kd * dErr
        output = sorted([-1, output, 1])[1]
        self.lastErr = error
        self.lastNow = now
        return output
