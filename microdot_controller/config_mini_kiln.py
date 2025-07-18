SSID = "PAULINHA"
PASSWORD = "makoto25"
USE_CUSTOM_IP = True
GATEWAY_IP = "192.168.0.1"
DEVICE_IP = "192.168.0.25"


from machine import Pin
import logging

########################################################################
#
#   General options


kiln_name = "mini_test_kiln"

### Logging
log_level = logging.DEBUG
# log_format = '%(asctime)s %(levelname)s %(name)s: %(message)s'
# log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
log_format = '%(asctime)s.%(msecs)03d | %(name)s | %(levelname)s | %(message)s'

### Server
# listening_ip = "0.0.0.0"
# listening_port = 8081

### Cost Estimate
kwh_rate        = 0.26  # Rate in currency_type to calculate cost to run job
currency_type   = "EUR"   # Currency Symbol to show when calculating cost to run job

########################################################################
#
#   GPIO Setup (BCM SoC Numbering Schema)
#
#   Check the RasPi docs to see where these GPIOs are
#   connected on the P1 header for your board type/rev.
#   These were tested on a Pi B Rev2 but of course you
#   can use whichever GPIO you prefer/have available.

### Outputs
gpio_heat = 3  # Switches zero-cross solid-state-relay
# gpio_heat_gnd = 39
# Pin(gpio_heat_gnd, Pin.OUT).off()  # Set the ground pin for the heater to low
gpio_cool = 10  # Regulates PWM for 12V DC Blower
gpio_air  = 9   # Switches 0-phase det. solid-state-relay

heater_invert = 0 # switches the polarity of the heater control

### Inputs
gpio_door = 18

### Thermocouple SPI Connection
gpio_sensor_clock = 18
gpio_sensor_cs = 33
gpio_sensor_data = 35
gpio_thermocouple_vdd = 39
gpio_thermocouple_gnd = 37

### Thermocouple SPI Connection (using adafrut drivers + kernel SPI interface)
spi_sensor_chip_id = 0

### amount of time, in seconds, to wait between reads of the thermocouple
sensor_time_wait = 1
# sensor_time_wait = 5

## Temperature oversampling rate to get more stable readings
temperature_oversamples = 10 # Number of samples observed between each "sensor_time_wait"

### Number of samples to average for the temperature reading
temperature_averaging_window = 30

### Number of attempts to read the thermocouple before giving up
sensor_retry_attempts = 5

########################################################################
#
#   PID parameters

# pid_ki = 0.1  # Integration
# pid_kd = 0.4  # Derivative
# pid_kp = 0.5  # Proportional

# pid_ki = 0.00000001  # Integration
# pid_kd = 0.004  # Derivative
# pid_kp = 0.005  # Proportional


# pid_ki = 0.01  # Integration
# pid_kd = 5  # Derivative
# pid_kp = 0.2  # Proportional


########################################################################
#
#   Simulation parameters

sim_t_env      = 25.0   # deg C
sim_c_heat     = 100.0  # J/K  heat capacity of heat element
sim_c_oven     = 2000.0 # J/K  heat capacity of oven
sim_p_heat     = 3500.0 # W    heating power of oven
sim_R_o_nocool = 1.0    # K/W  thermal resistance oven -> environment
sim_R_o_cool   = 0.05   # K/W  " with cooling
sim_R_ho_noair = 0.1    # K/W  thermal resistance heat element -> oven
sim_R_ho_air   = 0.05   # K/W  " with internal air circulation


########################################################################
#
#   Time and Temperature parameters

temp_scale          = "c" # c = Celsius | f = Fahrenheit - Unit to display 
time_scale_slope    = "m" # s = Seconds | m = Minutes | h = Hours - Slope displayed in temp_scale per time_scale_slope
time_scale_profile  = "m" # s = Seconds | m = Minutes | h = Hours - Enter and view target time in time_scale_profile

########################################################################
#
#    InfluxDB proxy configuration
influxdb_base_url = "http://192.168.0.3:8086"
influxdb_api_token = "ifJmQfGoF0eaVQQCFNk7BnmUqtiSC1n4Q7YuGlggIvJiLW9cKBh0zMVw5v9NmAR0Dx1haQYVSbTYa5bOfj01Qg=="
influxdb_organization = "danko"
influxdb_bucket = "sandbox"
# influxdb_instance_name = "development_fake_kiln"
influxdb_instance_name = "my_test_kiln_go"
