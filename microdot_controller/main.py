print("Microdot Controller is running...")
from wifi_utils import connect_to_wifi
from machine import Pin
from microdot import Microdot, send_file
import time

LED = Pin(15, Pin.OUT)    # create output pin on GPIO0


app = Microdot()

@app.route('/')
async def index(request):
    return 'Hello, world!'

@app.route('/public/<path:path>')
async def public(request, path):
    if '..' in path:
        # directory traversal is not allowed
        return 'Not found', 404
    return send_file('public/' + path, max_age=86400)

@app.route('/led_toggle')
async def led_toggle(request):
    LED.value(not LED.value())
    print("led toggled")
    return 'OK'

@app.route('/led_on')
async def led_on(request):
    LED.value(0)
    print("led on")
    return 'OK - ON'

@app.route('/led_off')
async def led_off(request):
    LED.value(1)
    print("led off")
    return 'OK - OFF'

if connect_to_wifi():
    print("Connected to WiFi")
    app.run()

# while True:
#     LED.value(not LED.value())  # toggle the LED state
#     time.sleep(0.1)             # wait for 500 milliseconds