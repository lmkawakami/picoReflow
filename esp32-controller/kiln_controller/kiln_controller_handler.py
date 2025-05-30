import esp32
from filemanager.web_server import (
    FM_200_JSON,
    FM_200_TEXT,
)
from filemanager.web_server_plugin import (
    WebServerPlugin
)
import json


class KilnControllerHandler(WebServerPlugin):
    @staticmethod
    @WebServerPlugin.handler('/status')
    def get_controller_status(client, path, request):
        response = {
            "Board temperature": "OK"
        }
        client.send(FM_200_JSON)
        client.send(json.dumps(response))