import network
from time import sleep_ms
import machine
import config

def initing():
    machine.PWM(machine.Pin(15), freq=5, duty=200)

def connecting():
    machine.PWM(machine.Pin(15), freq=1, duty=512)

def connected():
    machine.PWM(machine.Pin(15), freq=1, duty=1000)

def failed():
    machine.PWM(machine.Pin(15), freq=1, duty=24)

def set_ip_address(sta):
	default_gateway_ip = '192.168.0.1'
	default_device_ip = '192.168.0.25'
	gateway_ip = config.GATEWAY_IP or default_gateway_ip
	device_ip = config.DEVICE_IP or default_device_ip

	ip = device_ip
	subnet = '255.255.255.0'
	gateway = gateway_ip
	dns = '8.8.8.8'
	sta.ifconfig((ip, subnet, gateway, dns))

def disconnect_wifi():
	sta = network.WLAN(network.STA_IF)
	sta.disconnect()
	sleep_ms(1000)

def connect_to_wifi() -> bool:
	initing()
	sta = network.WLAN(network.STA_IF)
	sta.active(True)

	if sta.isconnected():
		return True

	wifi_list = sta.scan()

	print('Wifi List:')
	for index, wifi in enumerate(wifi_list, start=1):
		print(f'    [{index}] {wifi[0].decode()}')

	ssid = config.SSID
	password = config.PASSWORD

	sta.connect(ssid, password)
	connecting()

	while (not sta.isconnected()):
		status = sta.status()

		if status in [network.STAT_IDLE, network.STAT_GOT_IP, network.STAT_NO_AP_FOUND, network.STAT_WRONG_PASSWORD]:
			break
		elif status == network.STAT_CONNECTING:
			pass

		sleep_ms(200)

	sleep_ms(1000)
	status = sta.status()

	if status == network.STAT_GOT_IP:
		if config.USE_CUSTOM_IP:
			set_ip_address(sta)

		connected()
		print("Wifi connected, network config:", sta.ifconfig())
		return True
	else:
		failed()
		print(f'Connect wifi failed with status code: {status}')
		return False
