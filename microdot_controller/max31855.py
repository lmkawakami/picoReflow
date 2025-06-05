from machine import Pin, SoftSPI
import math
import time

D_MOSI_PIN = 15 # NOT_CONNECTED / MOSI / BOARD_LED


class RawTemperatures:
    def __init__(self, raw_temperature, junction_temperature):
        self.raw_temperature = raw_temperature
        self.junction_temperature = junction_temperature

    @property
    def dict(self) -> str:
        return ({
            "raw_temperature": self.raw_temperature,
            "junction_temperature": self.junction_temperature
        })

class CompensatedTemperatures(RawTemperatures):
    def __init__(self, compensated_temperature, raw_temperature, junction_temperature):
        self.compensated_temperature = compensated_temperature
        super().__init__(raw_temperature, junction_temperature)

    @property
    def dict(self) -> str:
        return ({
            "compensated_temperature": self.compensated_temperature,
            "raw_temperature": self.raw_temperature,
            "junction_temperature": self.junction_temperature
        })


class ThermocoupleError(Exception):
    def __init__(self, message):
        super().__init__(message)


class Thermocouple:
    def __init__(
        self,
        d_do_pin,
        d_cs_pin,
        d_clk_pin,
        d_mosi_pin=D_MOSI_PIN,
        d_3v3_pin=None,
        d_gnd_pin=None,
    ) -> None:
        print("           Initializing Thermocouple...")
        if not d_3v3_pin is None:
            print("           Setting up 3.3V pin...")
            d_3v3 = Pin(d_3v3_pin, Pin.OUT)
            d_3v3.on()

        if not d_gnd_pin is None:
            print("           Setting up GND pin...")
            d_gnd = Pin(d_gnd_pin, Pin.OUT)
            d_gnd.off()

        self.chip_select = Pin(d_cs_pin, Pin.OUT)
        self.chip_select.off()

        # chip_select.on()
        self.spi = SoftSPI(baudrate=100000, polarity=1, phase=0, sck=Pin(d_clk_pin), mosi=Pin(d_mosi_pin), miso=Pin(d_do_pin))
        self.spi.init(baudrate=100000) # set the baudrate
        self.chip_select.on()
        time.sleep(1)

    def read_temps(self) -> RawTemperatures:
        self.chip_select.off()
        buf = bytearray(4)     # create a buffer
        self.spi.readinto(buf)       # read into the given buffer (reads 50 bytes in this case)
        # print('buf:', buf)
        bits = (buf[0] << 24) | (buf[1] << 16) | (buf[2] << 8) | (buf[3] << 0)
        # print('bin:', bin(bits))

        sign_bit = bits >> 31
        if sign_bit:
            raise ThermocoupleError("Negative temp!!!")

        fault_mask = 0b1 << 16
        fault = bits & fault_mask
        if fault:
            print("Fault")

        shorted_to_vcc = bits & 0b100
        if shorted_to_vcc:
            raise ThermocoupleError("Shorted to vcc!!!")

        shorted_to_gnd = bits & 0b10
        if shorted_to_gnd:
            raise ThermocoupleError("Shorted to gnd!!!")

        open_connection = bits & 0b1
        if open_connection:
            raise ThermocoupleError("open connection!!!")

        temp_digits = bits >> 18
        temperature = temp_digits/4
        # print(f"termocouple tempo: {temperature}°C")

        junction_temp_mask = 0b1111111111110000
        junction_temp_bits = (bits & junction_temp_mask) >> 4
        junction_temp = junction_temp_bits/16
        # print(f"junction tempo: {junction_temp}°C")
        self.chip_select.on()

        #return (temperature, junction_temp)
        return RawTemperatures(temperature, junction_temp)

    def temperature_NIST(self) -> CompensatedTemperatures:
        raw_temps = self.read_temps()
        raw_temperature = raw_temps.raw_temperature
        junction_temp = raw_temps.junction_temperature
        TR = raw_temperature
        # temperature of device (cold junction)
        TAMB = junction_temp
        # thermocouple voltage based on MAX31855's uV/degC for type K (table 1)
        VOUT = 0.041276 * (TR - TAMB)
        # cold junction equivalent thermocouple voltage
        if TAMB >= 0:
            VREF = (
                -0.176004136860e-01
                + 0.389212049750e-01 * TAMB
                + 0.185587700320e-04 * math.pow(TAMB, 2)
                + -0.994575928740e-07 * math.pow(TAMB, 3)
                + 0.318409457190e-09 * math.pow(TAMB, 4)
                + -0.560728448890e-12 * math.pow(TAMB, 5)
                + 0.560750590590e-15 * math.pow(TAMB, 6)
                + -0.320207200030e-18 * math.pow(TAMB, 7)
                + 0.971511471520e-22 * math.pow(TAMB, 8)
                + -0.121047212750e-25 * math.pow(TAMB, 9)
                + 0.1185976
                * math.exp(-0.1183432e-03 * math.pow(TAMB - 0.1269686e03, 2))
            )
        else:
            VREF = (
                0.394501280250e-01 * TAMB
                + 0.236223735980e-04 * math.pow(TAMB, 2)
                + -0.328589067840e-06 * math.pow(TAMB, 3)
                + -0.499048287770e-08 * math.pow(TAMB, 4)
                + -0.675090591730e-10 * math.pow(TAMB, 5)
                + -0.574103274280e-12 * math.pow(TAMB, 6)
                + -0.310888728940e-14 * math.pow(TAMB, 7)
                + -0.104516093650e-16 * math.pow(TAMB, 8)
                + -0.198892668780e-19 * math.pow(TAMB, 9)
                + -0.163226974860e-22 * math.pow(TAMB, 10)
            )
        # total thermoelectric voltage
        VTOTAL = VOUT + VREF
        # determine coefficients
        # https://srdata.nist.gov/its90/type_k/kcoefficients_inverse.html
        if -5.891 <= VTOTAL <= 0:
            DCOEF = (
                0.0000000e00,
                2.5173462e01,
                -1.1662878e00,
                -1.0833638e00,
                -8.9773540e-01,
                -3.7342377e-01,
                -8.6632643e-02,
                -1.0450598e-02,
                -5.1920577e-04,
            )
        elif 0 < VTOTAL <= 20.644:
            DCOEF = (
                0.000000e00,
                2.508355e01,
                7.860106e-02,
                -2.503131e-01,
                8.315270e-02,
                -1.228034e-02,
                9.804036e-04,
                -4.413030e-05,
                1.057734e-06,
                -1.052755e-08,
            )
        elif 20.644 < VTOTAL <= 54.886:
            DCOEF = (
                -1.318058e02,
                4.830222e01,
                -1.646031e00,
                5.464731e-02,
                -9.650715e-04,
                8.802193e-06,
                -3.110810e-08,
            )
        else:
            print("    ERRO!!! - VTOTAL out of range:", VTOTAL)
            raise ThermocoupleError(f"Total thermoelectric voltage out of range:{VTOTAL}")
        if (raw_temperature, junction_temp) == (0, 0):
            print("    ERRO!!! - Raw temperature and junction temperature are both zero")
            raise ThermocoupleError("Reading zeros for some reason")
        # compute temperature
        COMPENSATED_TEMPERATURE = 0
        for n, c in enumerate(DCOEF):
            COMPENSATED_TEMPERATURE += c * math.pow(VTOTAL, n)
        print(f"    compensated temperature: {COMPENSATED_TEMPERATURE}°C")
        return CompensatedTemperatures(
            COMPENSATED_TEMPERATURE,
            raw_temperature,
            junction_temp
        )

    @property
    def compensated_temperature(self) -> float:
        return self.temperature_NIST().compensated_temperature

    @property
    def raw_temperature(self) -> float:
        return self.read_temps().raw_temperature

    @property
    def junction_temperature(self) -> float:
        return self.read_temps().junction_temperature


class MAX31855:
    def __init__(self, cs_pin, clock_pin, data_pin, d_3v3_pin=None, d_gnd_pin=None, units = "c"):
        '''Initialize Soft (Bitbang) SPI bus

        Parameters:
        - cs_pin:    Chip Select (CS) / Slave Select (SS) pin (Any GPIO)  
        - clock_pin: Clock (SCLK / SCK) pin (Any GPIO)
        - data_pin:  Data input (SO / MOSI) pin (Any GPIO)
        - units:     (optional) unit of measurement to return. ("c" (default) | "k" | "f")

        '''
        self.thermocouple = Thermocouple(
            d_cs_pin=cs_pin,
            d_clk_pin=clock_pin,
            d_do_pin=data_pin,
            d_3v3_pin=d_3v3_pin,
            d_gnd_pin=d_gnd_pin,
        )
        self.units = units.lower()
        self.data: CompensatedTemperatures

    def get(self):
        '''Returns current value of thermocouple.'''
        try:
            temp = self.thermocouple.compensated_temperature
            return getattr(self, "to_" + self.units)(temp)
        except ThermocoupleError as e:
            raise MAX31855Error(e)

    def to_c(self, celsius):
        '''Celsius passthrough for generic to_* method.'''
        return celsius

    def to_k(self, celsius):
        '''Convert celsius to kelvin.'''
        return celsius + 273.15

    def to_f(self, celsius):
        '''Convert celsius to fahrenheit.'''
        return celsius * 9.0/5.0 + 32

class MAX31855Error(Exception):
     def __init__(self, value):
         self.value = value
     def __str__(self):
         return repr(self.value)