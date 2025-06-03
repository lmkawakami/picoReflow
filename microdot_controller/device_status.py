import esp32
import os
import gc

def get_board_temperature() -> int:
    temp = esp32.mcu_temperature()
    return temp


def get_disk_status():
    s = os.statvfs('//')
    flash_total = (s[0] * s[2]) / 1024
    flash_used = flash_total - (s[0] * s[3]) / 1024

    return {
        'diskUsed': flash_used,
        'diskTotal': flash_total
    }

def get_memory_status():
    gc.collect()
    memory_free = gc.mem_free()
    memory_allocated = gc.mem_alloc()
    memory_total = memory_free+memory_allocated
    return {
        'memoryUsed': memory_allocated,
        'memoryTotal': memory_total
    }
