import uasyncio as asyncio
import json


class KilnControllerHandler:
    def __init__(self, webserver):
        self.webserver = webserver
        # Registra a rota /status para conexões WebSocket
        self.webserver.add_websocket_route('/status', self.websocket_handler)
