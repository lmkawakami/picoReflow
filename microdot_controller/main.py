print("Microdot Controller is running...")
from wifi_utils import connect_to_wifi
from machine import Pin
from microdot import Microdot, send_file
from microdot.websocket import with_websocket
import time

LED = Pin(15, Pin.OUT)    # create output pin on GPIO0


app = Microdot()

@app.route('/')
async def index(request):
    return 'Hello, world!'

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

# while True:
#     LED.value(not LED.value())  # toggle the LED state
#     time.sleep(0.1)             # wait for 500 milliseconds