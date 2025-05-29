from filemanager.web_server_plugin import WebServerPlugin
from filemanager.web_handler import (
	handle_contents,
	handle_upload,
	handle_update,
	handle_download,
	handle_delete,
	handle_rename,
	handle_newfolder,
	handle_move,
	handle_copy,
	handle_disk_status,
	handle_memory_status,
	handle_soft_reset,
    handle_hard_reset,
)


class FilemanagerHandler(WebServerPlugin):
    def __init__(self) -> None:
        self.create_handlers({
            '/contents': handle_contents,
            '/upload': handle_upload,
            '/update': handle_update,
            '/download': handle_download,
            '/delete': handle_delete,
            '/rename': handle_rename,
            '/newfolder': handle_newfolder,
            '/move': handle_move,
            '/copy': handle_copy,
            '/disk_status': handle_disk_status,
            '/memory_status': handle_memory_status,
            '/soft_reset': handle_soft_reset,
            '/hard_reset': handle_hard_reset,
        })
