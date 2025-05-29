import network
import socket
import _thread
from filemanager.filemanager_utils import (
	file_path_exists,
	read_in_chunks,
)
from singleton import singleton

FM_500 = """HTTP/1.1 500 Internal Server Error
Content-Type: text/plain

"""
FM_200_JSON = """HTTP/1.1 200 OK
Content-Type: application/json
Access-Control-Allow-Origin: *
Access-Control-Allow-Credentials: true
Access-Control-Allow-Methods: 'GET, POST, OPTIONS'
Access-Control-Allow-Headers: X-Requested-With, Content-type

"""
FM_200_TEXT = """HTTP/1.1 200 OK
Content-Type: text/plain
Access-Control-Allow-Origin: *
Access-Control-Allow-Credentials: true
Access-Control-Allow-Methods: 'GET, POST, OPTIONS'
Access-Control-Allow-Headers: X-Requested-With, Content-type

"""


@singleton
class WebServer:
	MIMETYPES = {
		"txt"   : "text/plain",
		"htm"   : "text/html",
		"html"  : "text/html",
		"css"   : "text/css",
		"csv"   : "text/csv",
		"js"    : "application/javascript",
		"xml"   : "application/xml",
		"xhtml" : "application/xhtml+xml",
		"json"  : "application/json",
		"zip"   : "application/zip",
		"pdf"   : "application/pdf",
		"ts"    : "application/typescript",
		"ttf"   : "font/ttf",
		"jpg"   : "image/jpeg",
		"jpeg"  : "image/jpeg",
		"png"   : "image/png",
		"gif"   : "image/gif",
		"svg"   : "image/svg+xml",
		"ico"   : "image/x-icon",
		"cur"   : "application/octet-stream",
		"tar"   : "application/tar",
		"tar.gz": "application/tar+gzip",
		"gz"    : "application/gzip",
		"mp3"   : "audio/mpeg",
		"wav"   : "audio/wav",
		"ogg"   : "audio/ogg"
	}

	def __init__(self, web_folder: str = '/www', port: int = 80):
		self.__web_folder = web_folder
		self.__webserv_sock = None
		self.__url_handlers = {}
		self.__port = port

	@property
	def url_handlers(self):
		"""Getter method for the url_handlers attribute."""
		return self.__url_handlers

	def get_mime_type(self, filename: str):
		try:
			_, ext = filename.rsplit(".", 1)
			return self.MIMETYPES.get(ext, "application/octet-stream")
		except:
			return "application/octet-stream"

	def serve_file(self, client: socket.socket, path: str):
		try:
			if path.startswith("/*GET_FILE"):
				file_path = path.replace("/*GET_FILE", "")
			else:
				if path == "/":
					path = "/index.html"

				file_path = self.__web_folder + path

			mime_type = self.get_mime_type(file_path)
			filestatus = 0 # 0=Not found  1=Found  2=found in GZip

			if file_path_exists(file_path + '.gz'):
				filestatus = 2
				file_path += '.gz'
			elif file_path_exists(file_path):
				filestatus = 1

			if filestatus > 0:
				with open(file_path, 'rb') as file:
					client.write(b'HTTP/1.1 200 OK\r\n')
					client.write(b"Content-Type: " + mime_type.encode() + b"\r\n")

					if filestatus == 2:
						client.write(b'Content-Encoding: gzip\r\n')

					client.write(b'\r\n')

					for piece in read_in_chunks(file):
						client.write(piece)
			else:
				client.write(b"HTTP/1.0 404 Not Found\r\n\r\nFile not found.")
		except OSError as e:
			print("OSError:", e)
			client.write(b"HTTP/1.0 500 Internal Server Error\r\n\r\nInternal error.")
		except Exception as e:
			print("Exception:", e)
			client.write(b"HTTP/1.0 500 Internal Server Error\r\n\r\nInternal error.")

	def handle(self, pattern):
		"""Decorator to register a handler for a specific URL pattern."""
		def decorator(func):
			self.__url_handlers[pattern] = func
			return func

		return decorator

	def client_handler(self, client: socket.socket):
		try:
			request = client.recv(2048)

			if request:
				_, path, _ = request.decode("utf-8").split(" ", 2)

				for pattern, handler in self.__url_handlers.items():
					base_path = path.split("?")[0]
					if base_path == pattern:
						try:
							handler(client, path, request)
						except Exception as e:
							print("Handler Exception:", e)
						client.close()

						return
				# Default file serving if no handler matches
				self.serve_file(client, path)
		except Exception as e:
			#print("Webserver Exception:", e)
			pass
		finally:
			client.close()

	def web_thread(self):
		while True:
			try:
				cl, _ = self.__webserv_sock.accept()
				cl.settimeout(2)  # time in seconds
				self.client_handler(cl)
			except Exception as e:
				#print("Webserver Exception:", e)
				pass

	def start(self):
		addr = socket.getaddrinfo('0.0.0.0', self.__port)[0][-1]
		self.__webserv_sock = socket.socket()
		self.__webserv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.__webserv_sock.bind(addr)
		self.__webserv_sock.listen(5)

		_thread.start_new_thread(self.web_thread, ())

		for interface in [network.AP_IF, network.STA_IF]:
			wlan = network.WLAN(interface)

			if not wlan.active():
				continue

			ifconfig = wlan.ifconfig()
			print(f"Web server running at {ifconfig[0]}:{self.__port}")

	def stop(self):
		if self.__webserv_sock:
			self.__webserv_sock.close()
