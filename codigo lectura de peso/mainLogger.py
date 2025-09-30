#!/usr/bin/python3
# -*- coding:utf-8 -*-

import spidev, RPi.GPIO as GPIO, time, sys, termios, tty, select, csv
from collections import deque

# ==============================
# CONFIGURACIÓN DE PINES / SPI
# ==============================
RST_PIN, CS_PIN, DRDY_PIN = 18, 22, 17
SPI = spidev.SpiDev(0, 0)

def digital_write(pin, val): GPIO.output(pin, val)
def digital_read(pin): return GPIO.input(DRDY_PIN)
def delay_ms(ms): time.sleep(ms/1000.0)
def spi_writebyte(data): SPI.writebytes(data)
def spi_readbytes(n): return SPI.readbytes(n)

def module_init():
    GPIO.setmode(GPIO.BCM); GPIO.setwarnings(False)
    GPIO.setup(RST_PIN, GPIO.OUT); GPIO.setup(CS_PIN, GPIO.OUT)
    GPIO.setup(DRDY_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    SPI.max_speed_hz, SPI.mode = 20000, 0b01
    return 0

# ==============================
# ADS1256
# ==============================
ADS1256_GAIN_E = {1:0, 2:1, 4:2, 8:3, 16:4, 32:5, 64:6}
ADS1256_DRATE_E = {'30SPS':0xF0, '60SPS':0x86, '100SPS':0x82, '500SPS':0x72}
REG_E = {'REG_MUX':1,'REG_ADCON':2,'REG_DRATE':3}
CMD = {'CMD_WREG':0x50,'CMD_RDATA':0x01}

class ADS1256:
    def __init__(self): self.rst_pin, self.cs_pin, self.drdy_pin = RST_PIN, CS_PIN, DRDY_PIN
    def reset(self):
        digital_write(self.rst_pin,1); delay_ms(50)
        digital_write(self.rst_pin,0); delay_ms(50)
        digital_write(self.rst_pin,1); delay_ms(50)
    def write_reg(self, reg, data):
        digital_write(self.cs_pin,0); spi_writebyte([CMD['CMD_WREG']|reg,0,data]); digital_write(self.cs_pin,1)
    def wait_drdy(self): 
        while digital_read(self.drdy_pin)==1: pass
    def config(self, gain, drate):
        self.wait_drdy()
        digital_write(self.cs_pin,0)
        spi_writebyte([CMD['CMD_WREG']|0,0x03])
        spi_writebyte([0x01,0x08,ADS1256_GAIN_E[gain],drate])
        digital_write(self.cs_pin,1); delay_ms(1)
    def set_diff_ch(self): self.write_reg(REG_E['REG_MUX'], (0<<4)|1) # AIN0-AIN1
    def init(self, gain, drate):
        if module_init()!=0: return -1
        self.reset(); self.config(gain, drate); return 0
    def read_data(self):
        self.wait_drdy(); digital_write(self.cs_pin,0)
        spi_writebyte([CMD['CMD_RDATA']]); b=spi_readbytes(3); digital_write(self.cs_pin,1)
        raw=(b[0]<<16)|(b[1]<<8)|b[2]
        if raw & 0x800000: raw -= 0x1000000
        return raw

# ==============================
# TECLADO
# ==============================
def set_cbreak():
    fd=sys.stdin.fileno(); st=termios.tcgetattr(fd); tty.setcbreak(fd); return fd,st
def restore_term(fd,st): termios.tcsetattr(fd,termios.TCSADRAIN,st)
def kbhit(): dr,_,_=select.select([sys.stdin],[],[],0); return dr!=[]
def getch(): return sys.stdin.read(1)

# ==============================
# MAIN CONFIG
# ==============================
VREF = 5.0
GAIN = 16
SPS = '100SPS'
CODE_FS = 0x7fffff
FS_mV = 3.9711563   # calibración

def code_to_mV(delta, gain): return (delta * (VREF/gain) / CODE_FS) * 1000.0

# ==============================
# FILTROS
# ==============================
FILTERS = ["OFF", "MEDIAN", "EMA", "MEDIAN+EMA", "MA"]
filter_mode_idx = 2  # por defecto EMA
alpha = 0.2          # EMA factor
ma_window = 10       # ventana MA

median_buf = deque(maxlen=5)
ma_buf = deque(maxlen=ma_window)
ema_state = None

def median5(x):
    median_buf.append(x)
    return sorted(median_buf)[len(median_buf)//2]

def ema(x):
    global ema_state
    if ema_state is None:
        ema_state = x
    else:
        ema_state = alpha * x + (1.0 - alpha) * ema_state
    return ema_state

def ma(x):
    ma_buf.append(x)
    return sum(ma_buf) / len(ma_buf)

def apply_filter(x):
    mode = FILTERS[filter_mode_idx]
    if mode == "OFF": return x
    elif mode == "MEDIAN": return median5(x)
    elif mode == "EMA": return ema(x)
    elif mode == "MEDIAN+EMA": return ema(median5(x))
    elif mode == "MA": return ma(x)
    return x

# ==============================
# MAIN
# ==============================
try:
    duracion = int(input("⏱️ ¿Cuánto tiempo quieres muestrear (segundos)? "))

    adc=ADS1256(); adc.init(GAIN, ADS1256_DRATE_E[SPS]); adc.set_diff_ch()
    # Tare inicial
    N=20; raw_zero=sum(adc.read_data() for _ in range(N))//N
    fd,old=set_cbreak()
    print("Tare inicial raw=%d\nPresiona: t=tare | g=ganancia | s=SPS | f=filtro | q=salir\n"%raw_zero)

    with open("thrust-curve.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["tiempo_s","raw","delta","voltaje_mV","fuerza_N","GAIN","SPS",
                         "voltaje_filt_mV","fuerza_filt_N"])

        start=time.time()
        while (time.time()-start)<duracion:
            adc.set_diff_ch(); raw=adc.read_data()
            delta=raw-raw_zero
            mv=code_to_mV(delta, GAIN)
            masa=(mv*FS_mV)
            t=time.time()-start

            mv_filt = apply_filter(mv)
            masa_filt = (mv_filt * FS_mV)

            writer.writerow([f"{t:.3f}", raw, delta, f"{mv:.6f}", f"{masa:.6f}",
                             GAIN, SPS, f"{mv_filt:.6f}", f"{masa_filt:.6f}"])

            print("t=%6.2fs GAIN=%2d SPS=%3s Raw=%7d Δ=%7d V=%8.3f mV F=%8.3f kgf | Vf=%8.3f Ff=%8.3f [%s]" % (
                t, GAIN, SPS, raw, delta, mv, masa, mv_filt, masa_filt, FILTERS[filter_mode_idx]))

            time.sleep(0.01)

            if kbhit():
                ch=getch().lower()
                if ch=='t':
                    raw_zero=sum(adc.read_data() for _ in range(N))//N
                    print("\n>>> Nuevo tare raw=%d\n"%raw_zero)
                elif ch=='g':
                    next_gains=[4,8,16,64]
                    GAIN=next_gains[(next_gains.index(GAIN)+1)%len(next_gains)]
                    adc.config(GAIN, ADS1256_DRATE_E[SPS])
                    print("\n>>> GAIN cambiado a %d\n"%GAIN)
                elif ch=='s':
                    next_sps=['30SPS','60SPS','100SPS','500SPS']
                    SPS=next_sps[(next_sps.index(SPS)+1)%len(next_sps)]
                    adc.config(GAIN, ADS1256_DRATE_E[SPS])
                    print("\n>>> SPS cambiado a %s\n"%SPS)
                elif ch=='f':
                    filter_mode_idx=(filter_mode_idx+1)%len(FILTERS)
                    ema_state=None
                    print("\n>>> Filtro: %s (alpha=%.2f, MAwin=%d)\n"%(FILTERS[filter_mode_idx],alpha,ma_window))
                elif ch=='+':
                    alpha=min(0.95,alpha+0.05)
                    print("\n>>> EMA alpha=%.2f\n"%alpha)
                elif ch=='-':
                    alpha=max(0.05,alpha-0.05)
                    print("\n>>> EMA alpha=%.2f\n"%alpha)
                elif ch=='h':
                    ma_window=min(500,ma_window+5); ma_buf=deque(ma_buf,maxlen=ma_window)
                    print("\n>>> MA window=%d\n"%ma_window)
                elif ch=='j':
                    ma_window=max(3,ma_window-5); ma_buf=deque(ma_buf,maxlen=ma_window)
                    print("\n>>> MA window=%d\n"%ma_window)
                elif ch=='q':
                    print("\n>>> Muestreo terminado por usuario\n"); break

    print("\n✅ Muestreo terminado. Datos guardados en thrust-curve.csv")

except KeyboardInterrupt:
    print("\n>>> Interrumpido con Ctrl+C")
finally:
    try: restore_term(fd,old)
    except: pass
    GPIO.cleanup(); print("GPIO liberado")
