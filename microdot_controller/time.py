from utime import *

def strftime(_datefmt, localtime):
    year, month, mday, hour, minute, second, _wday, _yday = localtime
    return f"{year:04d}-{month:02d}-{mday:02d} {hour:02d}:{minute:02d}:{second:02d}"