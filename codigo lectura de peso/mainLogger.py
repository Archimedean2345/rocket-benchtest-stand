#!/usr/bin/python3
# -*- coding:utf-8 -*-

import csv, time
import RPi.GPIO as GPIO
from mainUni import ADS1256, code_to_mV, FS_mV, FS_N, GAIN

def main():
    # Preguntar al usuario
    duracion = int(input("⏱️ ¿Cuánto tiempo quieres loggear (segundos)? "))
    nombre_archivo = input("📂 Nombre del archivo CSV (sin extensión): ").strip() + ".csv"

    print(f"\n>>> Loggeando durante {duracion} segundos...")
    print(f">>> Guardando en: {nombre_archivo}\n")

    # Inicializar ADC
    adc = ADS1256()
    adc.init(GAIN)
    adc.set_diff_ch()

    # Tare inicial
    N = 20
    raw_zero = sum(adc.read_data() for _ in range(N)) // N
    print(f"Tare inicial raw={raw_zero}\n")

    # Abrir archivo CSV
    with open(nombre_archivo, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["tiempo_s", "raw", "delta", "voltaje_mV", "fuerza_N"])

        start = time.time()
        while (time.time() - start) < duracion:
            raw = adc.read_data()
            delta = raw - raw_zero
            mv = code_to_mV(delta, GAIN)
            fuerza = (mv / FS_mV) * FS_N
            t = time.time() - start

            writer.writerow([f"{t:.3f}", raw, delta, f"{mv:.6f}", f"{fuerza:.6f}"])
            print(f"t={t:6.2f}s Raw={raw:7d} Δ={delta:7d} "
                  f"Voltaje={mv:8.3f} mV Fuerza={fuerza:9.2f} N")

            time.sleep(0.01)  # ~100 Hz

    print(f"\n✅ Logging terminado. Archivo guardado en {nombre_archivo}")

if __name__ == "__main__":
    try:
        main()
    finally:
        GPIO.cleanup()
