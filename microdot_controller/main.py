import logging
try:
    import config
except:
    print("Could not import config file.")
    print("Copy config.py.EXAMPLE to config.py and adapt it for your setup.")
    exit(1)

log_level = config.log_level
log_format = config.log_format
print(f"Configging logging... Level: {log_level}, Format: {log_format}")
logging.basicConfig(level=log_level, format=log_format)

print("Microdot Controller is running...")

from wifi_utils import connect_to_wifi
from machine import Pin
from microdot import Microdot, send_file, redirect
from microdot.websocket import with_websocket
import time
import ntptime
from oven import Oven, Profile
from ovenWatcher import OvenWatcher


log = logging.getLogger("picoreflowd")
log.info("Starting picoreflowd")

log.debug("Connecting to WiFi...")
connect_to_wifi()
log.info("Connected to WiFi")

log.debug("Synchronizing time with NTP server...")
ntptime.settime()
log.info("Time synchronized with NTP server")

LED = Pin(15, Pin.OUT)    # create output pin on GPIO0


app = Microdot()
oven = Oven()
ovenWatcher = OvenWatcher(oven)

@app.route('/')
async def index(request):
    # return 'Hello, world!'
    return redirect('/public/index.html')

@app.route('/status')
@with_websocket
async def status(request, ws):
    while True:
        message = await ws.receive()
        await ws.send(message)

@app.route('/public/<path:path>')
async def public(request, path):
    if '..' in path:
        # directory traversal is not allowed
        return 'Not found', 404
    return send_file('public/' + path, max_age=86400)

if connect_to_wifi():
    print("Connected to WiFi")
    app.run()



# import asyncio
# from oven import Oven

# async def main():
#     oven = Oven(simulate=True)  # or False if using real sensors
#     # The oven tasks are running in the background.
#     while True:
#         await asyncio.sleep(1)

# asyncio.run(main())