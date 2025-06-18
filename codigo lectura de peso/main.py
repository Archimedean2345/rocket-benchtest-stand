#!/usr/bin/python
# -*- coding:utf-8 -*-

import time
import ADS1256
import RPi.GPIO as GPIO

try:
    # Inicializa el ADC
    ADC = ADS1256.ADS1256()
    ADC.ADS1256_init()

    # Configura la ganancia del amplificador interno (64x)
    ADC.ADS1256_SetGain(ADC.GAIN_64)

    print("Inicio de lectura de celda de carga (AIN0 - AIN1)...\n")

    while True:
        # Selecciona lectura diferencial entre AIN0 y AIN1 (canal 0)
        ADC.ADS1256_SetDiffChannal(0)
        raw_value = ADC.ADS1256_GetChannalValue(0)

        # Convierte a voltaje
        voltage = raw_value * 5.0 / 0x7FFFFF  # 24 bits
        print(f"Voltaje diferencial: {voltage:.6f} V")

        time.sleep(0.2)

except KeyboardInterrupt:
    GPIO.cleanup()
    print("\nLectura interrumpida por el usuario.")

except Exception as e:
    GPIO.cleanup()
    print(f"\nError: {e}")
    exit()
