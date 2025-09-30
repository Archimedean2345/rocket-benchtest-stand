#!/usr/bin/python3
# -*- coding:utf-8 -*-

import csv, time
from mainUni import ADS1256, code_to_mV, VREF, CODE_FS, FS_mV, FS_N, ADS1256_DRATE_E, GAIN

# ==============================
# Logger de datos
# ==============================
def main():
    # Preguntar al usuario
    duracion = int(input("⏱️ ¿Cuánto tiempo quieres loggear (segundos)? "))
    nombre_archivo = input("📂 Nombre del archivo CSV (sin extensión): ").strip() + ".csv"

    print(f"\n>>> Loggeando durante {duracion} segundos...")
    print(f">>> Los datos se guardarán en {nombre_archivo}\n")

    # Inicializar ADC
    adc = ADS1256(); adc.init(GAIN); adc.set_diff_ch()

    # Tare inicial
    N = 20
    raw_zero = sum(adc.read_data() for _ in range(N)) // N
    print(f"Tare inicial raw={raw_zero}\n")

    # Abrir CSV
    with open(nombre_archivo, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "raw", "delta", "voltaje_mV", "fuerza_N"])

        start = time.time()
        while (time.time() - start) < duracion:
            raw = adc.read_data()
            delta = raw - raw_zero
            mv = code_to_mV(delta, GAIN)
            fuerza = mv * FS_mV  # N

            # Guardar en CSV
            writer.writerow([time.time() - start, raw, delta, mv, fuerza])

            # Mostrar en consola preview
            print(f"Raw={raw:7d} Δ={delta:7d} Voltaje={mv:8.3f} mV Fuerza={fuerza:9.2f} N")

            time.sleep(0.01)  # 100 Hz aprox

    print(f"\n✅ Logging terminado. Archivo guardado en {nombre_archivo}")

if __name__ == "__main__":
    main()
