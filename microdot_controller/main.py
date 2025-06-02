import os
import logging
try:
    import config
except:
    logging.error("Could not import config file.")
    logging.error("Copy config.py.EXAMPLE to config.py and adapt it for your setup.")
    exit(1)

log_level = config.log_level
log_format = config.log_format
logging.basicConfig(level=log_level, format=log_format)
logging.info(f"Configured logging... Level: {log_level}, Format: {log_format}")

from wifi_utils import connect_to_wifi
from machine import Pin
from microdot import Microdot, send_file, redirect
from microdot.websocket import with_websocket, WebSocketError
import time
import json
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
script_dir = os.getcwd()
profile_path = script_dir+("/").join(["storage", "profiles"])

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

@app.route('/control')
@with_websocket
async def control(request, ws):
    log.info("websocket (control) opened")
    while True:
        try:
            message = await ws.receive()
            log.info("Received (control): %s" % message)
            msgdict = json.loads(message)
            if msgdict.get("cmd") == "RUN":
                log.info("RUN command received")
                profile_obj = msgdict.get('profile')
                if profile_obj:
                    profile_json = json.dumps(profile_obj)
                    profile = Profile(profile_json)
                oven.run_profile(profile)
                ovenWatcher.record(profile)
            elif msgdict.get("cmd") == "SIMULATE":
                log.info("SIMULATE command received")
                profile_obj = msgdict.get('profile')
                if profile_obj:
                    profile_json = json.dumps(profile_obj)
                    profile = Profile(profile_json)
                simulated_oven = Oven(simulate=True, time_step=0.05)
                simulation_watcher = OvenWatcher(simulated_oven)
                simulation_watcher.add_observer(ws)
                #simulated_oven.run_profile(profile)
                #simulation_watcher.record(profile)
            elif msgdict.get("cmd") == "STOP":
                log.info("Stop command received")
                oven.abort_run()
        except WebSocketError:
            break
    log.info("websocket (control) closed")


@app.route('/storage')
@with_websocket
async def handle_storage(request, ws):
    log.info("websocket (storage) opened")
    while True:
        try:
            message = await ws.receive()
            if not message:
                break
            log.debug("websocket (storage) received: %s" % message)

            try:
                msgdict = json.loads(message)
            except:
                msgdict = {}

            if message == "GET":
                log.info("GET command recived")
                await ws.send(get_profiles())
            elif msgdict.get("cmd") == "DELETE":
                log.info("DELETE command received")
                profile_obj = msgdict.get('profile')
                if delete_profile(profile_obj):
                  msgdict["resp"] = "OK"
                await ws.send(json.dumps(msgdict))
                #wsock.send(get_profiles())
            elif msgdict.get("cmd") == "PUT":
                log.info("PUT command received")
                profile_obj = msgdict.get('profile')
                force = msgdict.get('force', False)
                if profile_obj:
                    #del msgdict["cmd"]
                    if save_profile(profile_obj, force):
                        msgdict["resp"] = "OK"
                    else:
                        msgdict["resp"] = "FAIL"
                    log.debug("websocket (storage) sent: %s" % message)

                    await ws.send(json.dumps(msgdict))
                    await ws.send(get_profiles())
        except WebSocketError:
            break
    log.info("websocket (storage) closed")

@app.route('/config')
@with_websocket
async def handle_config(request, ws):
    log.info("websocket (config) opened")
    while True:
        try:
            message = await ws.receive()
            print("Received message (config):", message)
            await ws.send(get_config())
        except WebSocketError:
            break
    log.info("websocket (config) closed")


def get_profiles():
    try:
        profile_files = os.listdir(profile_path)
    except:
        profile_files = []
    profiles = []
    for filename in profile_files:
        with open((profile_path+"/"+filename), 'r') as f:
            profiles.append(json.load(f))
    return json.dumps(profiles)

def exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False

def save_profile(profile, force=False):
    profile_json = json.dumps(profile)
    filename = profile['name']+".json"
    filepath = profile_path+"/"+filename
    log.debug("Saving profile to %s" % filepath)
    if not force and exists(filepath):
        log.error("Could not write, %s already exists" % filepath)
        return False
    with open(filepath, 'w+') as f:
        f.write(profile_json)
        f.close()
    log.info("Wrote %s" % filepath)
    return True

def delete_profile(profile):
    profile_json = json.dumps(profile)
    filename = profile['name']+".json"
    filepath = profile_path+"/"+filename
    # TODO: delete the file
    # os.remove(filepath)
    log.info("Deleted %s" % filepath)
    return True

def get_config():
    print("Getting config")
    return json.dumps({"temp_scale": config.temp_scale,
        "time_scale_slope": config.time_scale_slope,
        "time_scale_profile": config.time_scale_profile,
        "kwh_rate": config.kwh_rate,
        "currency_type": config.currency_type})    

def main():
    log.debug("Starting main function")
    if connect_to_wifi():
        log.debug("Connected to WiFi")
        log.debug("Stating web server...")
        app.run()
    log.debug("Web server stopped")

log.debug("Stating main function...")
main()
log.debug
# if __name__ == '__main__':
#     print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
#     main()

# import asyncio
# from oven import Oven

# async def main():
#     oven = Oven(simulate=True)  # or False if using real sensors
#     # The oven tasks are running in the background.
#     while True:
#         await asyncio.sleep(1)

# asyncio.run(main())