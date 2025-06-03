import asyncio
import logging, json, datetime
from oven import Oven
from timezone import BRT_TZ
from influxdb import InfluxDB

log = logging.getLogger(__name__)
log.info("Initializing OvenWatcher")

class OvenWatcher:
    def __init__(self, oven: Oven):
        self.last_profile = None
        self.last_log = []
        self.started = None
        self.recording = False
        self.observers = []
        self.log_skip_counter = 0
        self.influxdb = InfluxDB()
        self.oven = oven
        # Schedule the watcher loop as an asyncio task.
        asyncio.create_task(self.run_loop())

    async def run_loop(self):
        while True:
            log.debug("    OvenWatcher loop running...   ")
            oven_state = self.oven.get_state()

            tags = {"stage": "get_state"}
            # log.debug("Writing oven state to InfluxDB: %s", oven_state)
            # # result = await self.influxdb.async_write(fields=oven_state, tags=tags)
            # result = self.influxdb.write(fields=oven_state, tags=tags)
            # log.debug("InfluxDB write result: %s", result)
            self._write_influx(oven_state, tags={"stage": "get_state"})

            if oven_state.get("state") == Oven.STATE_RUNNING:
                if self.log_skip_counter == 0:
                    self.last_log.append(oven_state)
            else:
                self.recording = False

            await self.notify_all(oven_state)

            self.log_skip_counter = (self.log_skip_counter + 1) % 20
            await asyncio.sleep(self.oven.time_step)

    async def record(self, profile):
        self.last_profile = profile
        self.last_log = []
        self.started = datetime.datetime.now(BRT_TZ)
        self.recording = True
        # Add first state for a nice graph.
        self.last_log.append(self.oven.get_state())

    async def add_observer(self, observer):
        log.debug("OvenWatcher add_observer %s", observer)
        # Send backlog to new observer
        if self.last_profile:
            p = {
                "name": self.last_profile.name,
                "data": self.last_profile.data,
                "type": "profile"
            }
        else:
            p = None

        backlog = {
            'type': "backlog",
            'profile': p,
            'log': self.last_log,
            # 'started': self.started  # uncomment if needed
        }
        backlog_json = json.dumps(backlog)
        try:
            await observer.send(backlog_json)
        except Exception as e:
            log.error("Could not send backlog to new observer: %s", e)
        self.observers.append(observer)
        log.debug("OvenWatcher added observer %s, total observers: %d", observer, len(self.observers))

    async def notify_all(self, message):
        message_json = json.dumps(message)
        # Iterate over a copy of the observers list as it may change during iteration.
        for wsock in self.observers.copy():
            if wsock:
                try:
                    await wsock.send(message_json)
                except Exception as e:
                    log.error("could not write to socket %s: %s", wsock, e)
                    self.observers.remove(wsock)
            else:
                self.observers.remove(wsock)

    def _write_influx(self, oven_state, tags={}):
        async def write_influx_and_log(oven_state, tags):
            result = await self.influxdb.async_write(fields=oven_state, tags=tags)
            log.debug("InfluxDB write result: %s", result)

        asyncio.create_task(
            write_influx_and_log(oven_state, tags)
        )