#!/usr/bin/python3
# -*- coding:utf-8 -*-

import time
import ADS1256
import RPi.GPIO as GPIO

try:
    ADC = ADS1256.ADS1256()
    ADC.ADS1256_init()

    print("Lectura diferencial de 4 pares (AIN0-AIN1, AIN2-AIN3, AIN4-AIN5, AIN6-AIN7)")

    while True:
        ADC_Value = ADC.ADS1256_GetAll()
        for i in range(len(ADC_Value)):
            Voltage = ADC_Value[i] * 5.0 / 0x7FFFFF
            print(f"{i} ADC = {Voltage:.6f} V")
        print("\33[4A")  # Retrocede 4 líneas para imprimir sobre las mismas

except KeyboardInterrupt:
    GPIO.cleanup()
    print("\nPrograma terminado por usuario")