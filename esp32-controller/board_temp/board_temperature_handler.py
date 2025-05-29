import esp32
from filemanager.web_server import (
    FM_200_JSON,
    FM_200_TEXT,
)
from filemanager.web_server_plugin import (
    WebServerPlugin
)
import json

def get_board_temperature() -> int:
    temp = esp32.mcu_temperature()
    return temp


class BoardTemperatureHandler(WebServerPlugin):
    @staticmethod
    @WebServerPlugin.handler('/get_board_temperature')
    def get_board_temperature(client, path, request):
        response = {
            "Board temperature": get_board_temperature()
        }
        client.send(FM_200_JSON)
        client.send(json.dumps(response))