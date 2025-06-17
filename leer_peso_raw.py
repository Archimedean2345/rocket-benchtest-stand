import time
from ADS1256 import ADS1256
import RPi.GPIO as GPIO

adc = ADS1256()
adc.ADS1256_init()
adc.ADS1256_SetMode(0)
adc.ADS1256_SetGain(ADS1256.GAIN_64)
adc.ADS1256_SetRate(ADS1256.RATE_1000SPS)

print("Leyendo diferencial AD0-AD1... Ctrl+C para salir.")

try:
    while True:
        valor = adc.ADS1256_GetDiffChannalValue(0)
        print(f"Valor ADC bruto: {valor}")
        time.sleep(0.1)
except KeyboardInterrupt:
    GPIO.cleanup()
    print("Lectura detenida.")
