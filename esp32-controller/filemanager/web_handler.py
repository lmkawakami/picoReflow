import gc
import os
import json
import socket
import binascii
import sys
import machine
from filemanager.filemanager_utils import (
	is_directory,
	read_in_chunks,
	convert_file_size,
	file_path_exists,
	decode_percent_encoded_string
)
from filemanager.wifi_utils import disconnect_wifi
from filemanager.web_server import (
	FM_500,
	FM_200_JSON,
	FM_200_TEXT
)


def build_download_response_200_headers(file_name, file_path):
	return f"""HTTP/1.1 200 OK
Content-Type: application/octet-stream
Content-Disposition: attachment; filename=\"{file_name}\"
Content-Length: {os.stat(file_path)[6]}
Access-Control-Allow-Origin: *
Access-Control-Allow-Credentials: true
Access-Control-Allow-Methods: 'GET, POST, OPTIONS'
Access-Control-Allow-Headers: X-Requested-With, Content-type

"""

def urldecode(str: str):
	dic = {"%21":"!","%22":'"',"%23":"#","%24":"$","%26":"&","%27":"'","%28":"(","%29":")","%2A":"*","%2B":"+","%2C":",","%2F":"/","%3A":":","%3B":";","%3D":"=","%3F":"?","%40":"@","%5B":"[","%5D":"]","%7B":"{","%7D":"}"}
	for k,v in dic.items(): str=str.replace(k,v)
	return str

def parse_query_string(query_string: str):
	query = query_string.split('?')[1]
	params = query.split('&')
	param_dict = {}

	for param in params:
		key, value = param.split('=')
		param_dict[key] = value
	
	return param_dict

def list_directory_contents(base_path: str):
	contents = []

	try:
		for entry in os.listdir(base_path):
			if base_path == '/':
				entry_path = '/' + entry
			else:
				entry_path = base_path + '/' + entry
			
			#print(entry_path)
			
			if is_directory(entry_path):
				contents.append({
					'name': entry,
					'path': entry_path,
					'isDirectory': True
				})
			else:
				contents.append({
					'name': entry,
					'path': entry_path,
					'isDirectory': False,
					'size': convert_file_size(os.stat(entry_path)[6])
				})
	except OSError as e:
		print("OSError:", e)

	return contents

def delete_path(path: str):
	if not file_path_exists(path):
		print(f"Path {path} does not exist.")
		return

	stack = [path]

	while stack:
		current_path = stack.pop()

		if is_directory(current_path):
			try:
				entries = list(os.ilistdir(current_path))
				if not entries:
					# Directory is empty, we can delete it
					os.rmdir(current_path)
					#print(f"Deleted directory: {current_path}")
				else:
					# Add directory back to stack to try again later
					stack.append(current_path)
					# Add entries to stack
					for entry in entries:
						entry_path = current_path + '/' + entry[0]
						stack.append(entry_path)
			except Exception as e:
				print(f"Error accessing directory {current_path}: {e}")
		else:
			try:
				os.remove(current_path)
				#print(f"Deleted file: {current_path}")
			except Exception as e:
				print(f"Error deleting file {current_path}: {e}")

def handle_update(client: socket.socket, path: str, request):
	try:
		filepath = path.split('?path=')[1] if '?path=' in path else '/'
		filepath = decode_percent_encoded_string(filepath)
		data = request[request.find(b'\r\n\r\n') + 4:]
		with open(filepath, 'wb') as file:
			file.write(data)
		response = json.dumps({"file": filepath, "status": "update complete"})
		client.send(FM_200_JSON)
		client.send(response)
	except Exception as e:
		print("Error:", e)
		response = json.dumps({"file": filepath, "status": "update fails"})
		client.send(FM_500)
		client.send(response)

def handle_contents(client: socket.socket, path: str, request):
	try:
		query_params = path.split('?path=')[1] if '?path=' in path else '/'
		full_path = query_params
		
		contents = list_directory_contents(full_path)
		response = json.dumps({"contents": contents})
		client.send(FM_200_JSON)
		client.send(response)
	except Exception as e:
		print("Error:", e)
		client.send(FM_500)
		client.send("Internal Server Error")

def handle_upload(client: socket.socket, path: str, request):
	try:
		_, filepath, filesize = path.split(';')
		filesize = int(filesize) * 2
		data_read = 0

		#print("Upload: " + str(filepath) + "    size: "  + str(filesize))
		#print("0%")

		with open(filepath, 'wb') as file:
			data = request[request.find(b'\r\n\r\n') + 4:]

			if data:
				data_read = len(data)

				if data_read % 2 == 0:
					file.write(binascii.unhexlify(data))
				else:
					data = data + client.read(1)
					file.write(binascii.unhexlify(data))

				data_read = len(data)

			while data_read < filesize:
				try:
					chunk_size = min(1024, filesize - data_read)
					chunk = client.read(chunk_size)
					file.write(binascii.unhexlify(chunk))
					data_read = data_read + chunk_size
					percentage = (data_read / filesize) * 100
					#print(f"{percentage:.1f}%")

					if not chunk:
						break
				except OSError as e:
					if e.args[0] == 116:  # ETIMEDOUT
						break
					else:
						raise e

		#print("File Saved")
		client.send(FM_200_TEXT)
		client.send("Upload successful")
	except Exception as e:
		print("Error during file upload:", e)
		client.send(FM_500)
		client.send("Upload failed")

def handle_download(client: socket.socket, path: str, request):
	try:
		file_path = urldecode(path).split('?path=')[1]
		file_name = file_path.split('/')[-1]

		if file_path_exists(file_path):
			headers_200 = build_download_response_200_headers(file_name, file_path)
			client.send(headers_200)
			with open(file_path, 'rb') as f:
				for piece in read_in_chunks(f):
					client.write(piece)
		else:
			client.send("HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\n")
			client.send("File not found.")
	except OSError as e:
		print("OSError:", e)
		client.send(FM_500)
		client.send("Internal Server Error")

def handle_delete(client: socket.socket, path: str, request):
	try:
		files = json.loads(urldecode(path).split('?files=')[1])

		for file_path in files:
			delete_path(file_path) 

		client.send(FM_200_TEXT)
		client.send("Files deleted successfully.")
	except OSError as e:
		print("OSError:", e)
		client.send(FM_500)
		client.send("Internal Server Error")

def handle_rename(client: socket.socket, path: str, request):
	try:
		query_params = json.loads(urldecode(path).split('?data=')[1])
		old_name = query_params['old_name']
		new_name = query_params['new_name']
		os.rename(old_name, new_name)
		client.send(FM_200_TEXT)
		client.send("File renamed successfully.")
	except OSError as e:
		print("OSError:", e)
		client.send(FM_500)
		client.send("Internal Server Error")

def handle_newfolder(client: socket.socket, path: str, request):
	try:
		query_params = json.loads(urldecode(path).split('?data=')[1])
		folderpath = query_params['foldername']
		os.mkdir(folderpath)
		client.send(FM_200_TEXT)
		client.send("New folder created successfully.")
	except OSError as e:
		print("OSError:", e)
		client.send(FM_500)
		client.send("Internal Server Error")

def handle_copy(client: socket.socket, path: str, request):
	try:
		query_params = json.loads(urldecode(path).split('?data=')[1])
		src_files = query_params['src']
		dest_path = query_params['dest']
		stack = []

		for src in src_files:
			stack.append((src, dest_path))

		while stack:
			current_src, current_dest = stack.pop()
			if is_directory(current_src):
				new_dir_path = current_dest + '/' + current_src.split('/')[-1]
				os.mkdir(new_dir_path)

				for entry in os.listdir(current_src):
					stack.append((current_src + '/' + entry, new_dir_path))
			else:
				with open(current_src, 'rb') as f_src:
					with open(current_dest + '/' + current_src.split('/')[-1], 'wb') as f_dest:
						for piece in read_in_chunks(f_src):
							f_dest.write(piece)

		client.send(FM_200_TEXT)
		client.send("Files copied successfully.")
	except OSError as e:
		print("OSError:", e)
		client.send(FM_500)
		client.send("Internal Server Error")

def handle_move(client: socket.socket, path: str, request):
	try:
		query_params = json.loads(urldecode(path).split('?data=')[1])
		src_files = query_params['src']
		dest_path = query_params['dest']
		stack = []

		for src in src_files:
			stack.append((src, dest_path))

		# Přesun souborů a adresářů
		while stack:
			current_src, current_dest = stack.pop()
			if is_directory(current_src):
				new_dir_path = current_dest + '/' + current_src.split('/')[-1]

				if not file_path_exists(new_dir_path):
					os.mkdir(new_dir_path)

				for entry in os.listdir(current_src):
					stack.append((current_src + '/' + entry, new_dir_path))
			else:
				os.rename(current_src, current_dest + '/' + current_src.split('/')[-1])

		# Smazání prázdných původních adresářů
		for src in src_files:
			delete_path(src)

		client.send(FM_200_TEXT)
		client.send("Files moved successfully.")
	except OSError as e:
		print("OSError:", e)
		client.send(FM_500)
		client.send("Internal Server Error")

def delete_path(path):
	if not file_path_exists(path):
		#print(f"Path {path} does not exist.")
		return

	stack = [path]

	# Iterační průchod pro mazání souborů a podadresářů
	while stack:
		current_path = stack.pop()

		if is_directory(current_path):
			try:
				entries = list(os.ilistdir(current_path))
				if not entries:
					os.rmdir(current_path)
				else:
					stack.append(current_path)

					for entry in entries:
						entry_path = current_path + '/' + entry[0]
						stack.append(entry_path)
			except Exception as e:
				print(f"Error accessing directory {current_path}: {e}")
		else:
			try:
				os.remove(current_path)
			except Exception as e:
				print(f"Error deleting file {current_path}: {e}")

def handle_disk_status(client: socket.socket, path: str, request):
	try:
		s = os.statvfs('//')
		flash_total = (s[0] * s[2]) / 1024
		flash_used = flash_total - (s[0] * s[3]) / 1024
		usage_percent = flash_used / flash_total * 100

		contents = ({
			'progress': '{0:.1f}'.format(usage_percent),
			'memoryUsed': '{0:.1f}'.format(flash_used),
			'memoryTotal': '{0:.1f}'.format(flash_total)
		})

		response = json.dumps(contents)
		client.send(FM_200_JSON)
		client.send(response)
		#print(response)
	except Exception as e:
		print("Error:", e)
		client.send(FM_500)
		client.send("Internal Server Error")

def handle_memory_status(client: socket.socket, path: str, request):
	try:
		gc.collect()
		memory_free = gc.mem_free()
		memory_allocated = gc.mem_alloc()
		memory_total = memory_free+memory_allocated
		usage_percent = memory_allocated/memory_total*100
		contents = ({
			'progress': '{0:.1f}'.format(usage_percent),
			'memoryUsed': '{0:.1f}'.format(memory_allocated),
			'memoryTotal': '{0:.1f}'.format(memory_total)
		})

		response = json.dumps(contents)
		client.send(FM_200_JSON)
		client.send(response)
		#print(response)
	except Exception as e:
		print("Error:", e)
		client.send(FM_500)
		client.send("Internal Server Error")

def handle_soft_reset(client: socket.socket, _path, _req):
	client.send(FM_200_TEXT)
	client.send("Soft resseting the device")
	sys.exit()

def handle_hard_reset(client: socket.socket, _path, _req):
	client.send(FM_200_TEXT)
	client.send("Hard resseting the device")
	disconnect_wifi()
	machine.reset()
