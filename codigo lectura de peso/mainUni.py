#!/usr/bin/python
# -*- coding:utf-8 -*-

import spidev
import RPi.GPIO as GPIO
import time

# ==============================
# CONFIGURACIÓN DE PINES / SPI
# ==============================
RST_PIN  = 18
CS_PIN   = 22
DRDY_PIN = 17

SPI = spidev.SpiDev(0, 0)

def digital_write(pin, value):
    GPIO.output(pin, value)

def digital_read(pin):
    return GPIO.input(DRDY_PIN)

def delay_ms(delaytime):
    time.sleep(delaytime / 1000.0)

def spi_writebyte(data):
    SPI.writebytes(data)
    
def spi_readbytes(reg):
    return SPI.readbytes(reg)

def module_init():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(RST_PIN, GPIO.OUT)
    GPIO.setup(CS_PIN, GPIO.OUT)
    GPIO.setup(DRDY_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    SPI.max_speed_hz = 20000
    SPI.mode = 0b01
    return 0

# ==============================
# ADS1256 DRIVER
# ==============================
ADS1256_GAIN_E = {
    'ADS1256_GAIN_1'  : 0,
    'ADS1256_GAIN_2'  : 1,
    'ADS1256_GAIN_4'  : 2,
    'ADS1256_GAIN_8'  : 3,
    'ADS1256_GAIN_16' : 4,
    'ADS1256_GAIN_32' : 5,
    'ADS1256_GAIN_64' : 6,
}

ADS1256_DRATE_E = {
    'ADS1256_100SPS' : 0x82,  # Elegido: 100 SPS
}

REG_E = {
    'REG_STATUS' : 0,
    'REG_MUX'    : 1,
    'REG_ADCON'  : 2,
    'REG_DRATE'  : 3,
}

CMD = {
    'CMD_WREG'  : 0x50,
    'CMD_RREG'  : 0x10,
    'CMD_SYNC'  : 0xFC,
    'CMD_WAKEUP': 0x00,
    'CMD_RDATA' : 0x01,
}

class ADS1256:
    def __init__(self):
        self.rst_pin  = RST_PIN
        self.cs_pin   = CS_PIN
        self.drdy_pin = DRDY_PIN

    def ADS1256_reset(self):
        digital_write(self.rst_pin, GPIO.HIGH)
        delay_ms(200)
        digital_write(self.rst_pin, GPIO.LOW)
        delay_ms(200)
        digital_write(self.rst_pin, GPIO.HIGH)

    def ADS1256_WriteCmd(self, reg):
        digital_write(self.cs_pin, GPIO.LOW)
        spi_writebyte([reg])
        digital_write(self.cs_pin, GPIO.HIGH)

    def ADS1256_WriteReg(self, reg, data):
        digital_write(self.cs_pin, GPIO.LOW)
        spi_writebyte([CMD['CMD_WREG'] | reg, 0x00, data])
        digital_write(self.cs_pin, GPIO.HIGH)

    def ADS1256_WaitDRDY(self):
        while(digital_read(self.drdy_pin) == 1):
            pass

    def ADS1256_ConfigADC(self, gain, drate):
        self.ADS1256_WaitDRDY()
        buf = [0, 0, 0, 0]
        buf[0] = 0x01  # STATUS
        buf[1] = 0x08  # MUX default
        buf[2] = gain  # ADCON: PGA gain
        buf[3] = drate # DRATE: sample rate
        digital_write(self.cs_pin, GPIO.LOW)
        spi_writebyte([CMD['CMD_WREG'] | 0, 0x03])
        spi_writebyte(buf)
        digital_write(self.cs_pin, GPIO.HIGH)
        delay_ms(1)

    def ADS1256_SetDiffChannal(self, Channal):
        # Solo implementamos AIN0-AIN1 (diferencial)
        if Channal == 0:
            self.ADS1256_WriteReg(REG_E['REG_MUX'], (0 << 4) | 1)

    def ADS1256_init(self):
        if (module_init() != 0):
            return -1
        self.ADS1256_reset()
        self.ADS1256_ConfigADC(ADS1256_GAIN_E['ADS1256_GAIN_64'],
                               ADS1256_DRATE_E['ADS1256_100SPS'])
        return 0

    def ADS1256_Read_ADC_Data(self):
        self.ADS1256_WaitDRDY()
        digital_write(self.cs_pin, GPIO.LOW)
        spi_writebyte([CMD['CMD_RDATA']])
        buf = spi_readbytes(3)
        digital_write(self.cs_pin, GPIO.HIGH)
        read = (buf[0] << 16) | (buf[1] << 8) | buf[2]
        if (read & 0x800000):  # signed 24-bit
            read -= 0x1000000
        return read

# ==============================
# MAIN LOOP
# ==============================
# Parámetros de la celda de carga
VREF = 5.0        # Referencia del ADC
FS_N = 2943       # 300 kg ≈ 2943 N
FS_mV = 9.0       # 1 mV/V * 9 V excitación

try:
    ADC = ADS1256()
    ADC.ADS1256_init()

    while True:
        ADC.ADS1256_SetDiffChannal(0)  # Canal diferencial AIN0-AIN1
        raw = ADC.ADS1256_Read_ADC_Data()

        # Convertir a mV
        voltage = (raw * VREF / 0x7fffff) * 1000
        # Convertir a Newtons
        fuerza = (voltage / FS_mV) * FS_N

        print("Celda = %.3f mV   (%.2f N)" % (voltage, fuerza))
        time.sleep(0.01)  # ~100 SPS

except KeyboardInterrupt:
    GPIO.cleanup()
    print("\r\nPrograma terminado")
    exit()
