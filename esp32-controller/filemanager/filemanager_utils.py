import os


def file_path_exists(path: str) -> bool:
	try:
		os.stat(path)
		return True
	except OSError:
		return False

def is_directory(path: str) -> bool:
	try:
		return os.stat(path)[0] & 0x4000 != 0
	except OSError:
		return False

def read_in_chunks(file_object, chunk_size: int = 1024):
	while True:
		data = file_object.read(chunk_size)

		if not data:
			break

		yield data

def convert_file_size(size: int) -> str:
	units = 'Bytes', 'KB', 'MB', 'GB', 'TB'
	unit = units[0]

	for i in range(1, len(units)):
		if size >= 1024:
			size /= 1024
			unit = units[i]
		else:
			break

	return f'{size:.2f} {unit}'

def decode_percent_encoded_string(s):
	result = []
	i = 0
	while i < len(s):
		if s[i] == '%' and i + 2 < len(s):
			hex_value = s[i+1:i+3]
			result.append(chr(int(hex_value, 16)))
			i += 3
		else:
			result.append(s[i])
			i += 1
	return ''.join(result)
