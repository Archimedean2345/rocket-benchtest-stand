#!/usr/bin/python
# -*- coding:utf-8 -*-

import spidev
import RPi.GPIO as GPIO
import time
import sys
import termios
import tty
import select

# ==============================
# CONFIG PINES / SPI
# ==============================
RST_PIN  = 18
CS_PIN   = 22
DRDY_PIN = 17

SPI = spidev.SpiDev(0, 0)

def digital_write(pin, value):
    GPIO.output(pin, value)

def digital_read(pin):
    return GPIO.input(DRDY_PIN)

def delay_ms(ms):
    time.sleep(ms / 1000.0)

def spi_writebyte(data):
    SPI.writebytes(data)

def spi_readbytes(n):
    return SPI.readbytes(n)

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
# ADS1256
# ==============================
ADS1256_GAIN_E = {'ADS1256_GAIN_64': 6}
ADS1256_DRATE_E = {'ADS1256_100SPS': 0x82}
REG_E = {'REG_STATUS':0, 'REG_MUX':1, 'REG_ADCON':2, 'REG_DRATE':3}
CMD = {'CMD_WREG':0x50,'CMD_RREG':0x10,'CMD_SYNC':0xFC,'CMD_WAKEUP':0x00,'CMD_RDATA':0x01}

class ADS1256:
    def __init__(self):
        self.rst_pin  = RST_PIN
        self.cs_pin   = CS_PIN
        self.drdy_pin = DRDY_PIN

    def reset(self):
        digital_write(self.rst_pin, GPIO.HIGH); delay_ms(50)
        digital_write(self.rst_pin, GPIO.LOW);  delay_ms(50)
        digital_write(self.rst_pin, GPIO.HIGH); delay_ms(50)

    def write_reg(self, reg, data):
        digital_write(self.cs_pin, GPIO.LOW)
        spi_writebyte([CMD['CMD_WREG'] | reg, 0x00, data])
        digital_write(self.cs_pin, GPIO.HIGH)

    def wait_drdy(self):
        while digital_read(self.drdy_pin) == 1:
            pass

    def config(self, gain, drate):
        self.wait_drdy()
        # STATUS(0x01), MUX(0x08 por defecto), ADCON(gain), DRATE
        digital_write(self.cs_pin, GPIO.LOW)
        spi_writebyte([CMD['CMD_WREG'] | 0, 0x03])
        spi_writebyte([0x01, 0x08, gain, drate])
        digital_write(self.cs_pin, GPIO.HIGH)
        delay_ms(1)

    def set_diff_ch(self, ch=0):
        # ch=0 => AIN0 (P) - AIN1 (N)
        if ch == 0:
            self.write_reg(REG_E['REG_MUX'], (0 << 4) | 1)

    def init(self):
        if module_init() != 0:
            return -1
        self.reset()
        self.config(ADS1256_GAIN_E['ADS1256_GAIN_64'], ADS1256_DRATE_E['ADS1256_100SPS'])
        return 0

    def read_data(self):
        self.wait_drdy()
        digital_write(self.cs_pin, GPIO.LOW)
        spi_writebyte([CMD['CMD_RDATA']])
        b = spi_readbytes(3)
        digital_write(self.cs_pin, GPIO.HIGH)
        raw = (b[0] << 16) | (b[1] << 8) | b[2]
        if raw & 0x800000:  # signed 24-bit
            raw -= 0x1000000
        return raw

# ==============================
# Teclado sin ENTER
# ==============================
def set_cbreak():
    fd = sys.stdin.fileno()
    st = termios.tcgetattr(fd)
    tty.setcbreak(fd)
    return fd, st

def restore_term(fd, st):
    termios.tcsetattr(fd, termios.TCSADRAIN, st)

def kbhit():
    dr, _, _ = select.select([sys.stdin], [], [], 0)
    return dr != []

def getch():
    return sys.stdin.read(1)

# ==============================
# MAIN
# ==============================
VREF = 5.0       # Referencia que usa la placa (jumper en 5V)
FS_mV = 9.0      # 1 mV/V * 9V = 9 mV a carga máxima
FS_N  = 2943     # 300 kg ≈ 2943 N
CODE_FS = 0x7fffff  # + full scale code

def code_to_mV(delta_code):
    # Convierte delta de código a mV
    return (delta_code * VREF / CODE_FS) * 1000.0

try:
    adc = ADS1256()
    adc.init()
    adc.set_diff_ch(0)  # AIN0 - AIN1 (S+ en AD0, S- en AD1)

    # --- TARE en crudo: promedio para un cero estable ---
    N_TARE = 20
    acc = 0
    for _ in range(N_TARE):
        acc += adc.read_data()
        time.sleep(0.005)
    raw_zero = acc // N_TARE

    # Polaridad: si al comprimir ves N negativos, pon -1 o pulsa 'p'
    sign_dir = +1  # +1 = AIN0-AIN1 positivo es compresión; -1 invierte

    # Teclado sin ENTER
    fd, old = set_cbreak()

    print("Tare inicial (raw) = %d" % raw_zero)
    print("Teclas:  t = tare | p = invertir polaridad | q = salir\n")

    while True:
        adc.set_diff_ch(0)
        raw = adc.read_data()
        raw_delta = raw - raw_zero          # Tare en crudo
        mv = sign_dir * code_to_mV(raw_delta)
        forceN = (mv / FS_mV) * FS_N

        print("Raw=%7d  Δraw=%7d  Voltaje=%8.3f mV  Fuerza=%9.2f N  (pol=%+d)"
              % (raw, raw_delta, mv, forceN, sign_dir))
        time.sleep(0.01)  # ~100 SPS

        if kbhit():
            ch = getch().lower()
            if ch == 't':
                # nuevo tare (promedio rápido)
                acc = 0
                for _ in range(N_TARE):
                    acc += adc.read_data()
                    time.sleep(0.005)
                raw_zero = acc // N_TARE
                print("\n>>> Nuevo tare aplicado. raw_zero = %d\n" % raw_zero)
            elif ch == 'p':
                sign_dir *= -1
                print("\n>>> Polaridad invertida. (pol=%+d)\n" % sign_dir)
            elif ch == 'q':
                break

except KeyboardInterrupt:
    pass
finally:
    try:
        restore_term(fd, old)
    except Exception:
        pass
    GPIO.cleanup()
    print("\nPrograma terminado.")
