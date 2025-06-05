import time
import config
from max31855 import MAX31855, Thermocouple

D_3V3_PIN = 6
D_GND_PIN = 7
D_DO_PIN = 8 # MISO / DO
D_CS_PIN = 9 # CHIP_SELECT
D_CLK_PIN = 10 # CLK / SCK
D_MOSI_PIN = 11 # NOT_CONNECTED / MOSI

# thermocouple = Thermocouple(
#     d_3v3_pin=D_3V3_PIN,
#     d_gnd_pin=D_GND_PIN,
#     d_do_pin=D_DO_PIN,
#     d_cs_pin=D_CS_PIN,
#     d_clk_pin=D_CLK_PIN,
#     d_mosi_pin=D_MOSI_PIN
# )

thermocouple = MAX31855(
    config.gpio_sensor_cs,
    config.gpio_sensor_clock,
    config.gpio_sensor_data,
    config.gpio_thermocouple_vdd,
    config.gpio_thermocouple_gnd,
    config.temp_scale
)
while True:
    time.sleep(1)
    print(thermocouple.get())