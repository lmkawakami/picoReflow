import gc
from micropython import alloc_emergency_exception_buf
from filemanager.wifi_utils import connect_to_wifi
from filemanager.web_server import WebServer
from filemanager.filemanager_handler import FilemanagerHandler
from board_temp import BoardTemperatureHandler

__version__ = '0.0.2'
module_folder = ''

try:
	module_folder = __file__.rsplit('/', 1)[0]

	if module_folder == __file__:
		module_folder = ''
except NameError:
	pass


alloc_emergency_exception_buf(128)
gc.collect()

# Start WWW serveru
webserver = WebServer(web_folder=f'/{module_folder}/www', port=80)

#region Handlers for web_handlers
FilemanagerHandler()
BoardTemperatureHandler()
#endregion

if connect_to_wifi():
	webserver.start()
	gc.collect()
