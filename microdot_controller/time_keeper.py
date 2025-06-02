# time_keeper.py
import time
import ntptime
import utime
import asyncio
from singleton import singleton

@singleton
class TimeKeeper:
    def __init__(self):
        self._syncronized = False
        self._last_tick = utime.ticks_ms()

    def syncronize_time(self):
        if not self._syncronized:
            ntptime.settime()
            self._syncronized = True
    
    def get_epoch(self):
        """
        Get the current epoch time adjusted for the offset between 1970 and 2000.

        Returns:
            float: The current time in seconds since the epoch (2000-01-01 00:00:00 UTC).
        """
        EPOCHS_OFFSET = 946684800 #difference between 1970 and 2000
        return time.time()+EPOCHS_OFFSET
    
    def get_date(self):
        utc_time = time.time()
        local_time = utc_time - 3 * 3600
        Y,M,D,_h,_m,_s,_ms,_us = time.localtime(local_time)
        return f'{D}/{M}/{Y}'

    async def sleep_until_next_interval(self, interval_ms: int):
        """
        Wait until the next interval (in ms) is completed from the last tick.
        This ensures that even if the reading execution is delayed a bit, the intervals
        remain regular.
        """
        next_tick = utime.ticks_add(self._last_tick, interval_ms)
        now = utime.ticks_ms()
        remaining = utime.ticks_diff(next_tick, now)
        if remaining > 0:
            await asyncio.sleep(remaining / 1000)
        self._last_tick = next_tick
