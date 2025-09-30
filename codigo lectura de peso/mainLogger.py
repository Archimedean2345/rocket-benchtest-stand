#!/usr/bin/python3
# -*- coding:utf-8 -*-

import csv, time
import matplotlib.pyplot as plt

# Importamos directamente del mainUni
import mainUni

def adquirir_datos(duracion=10, filename="mediciones.csv"):
    adc = mainUni.ADS1256()
    adc.init(mainUni.GAIN)
    adc.set_diff_ch()

    # Tare inicial
    N = 20
    raw_zero = sum(adc.read_data() for _ in range(N)) // N
    print(f"Tare inicial raw={raw_zero}")

    tiempos, raws, voltajes, fuerzas = [], [], [], []

    t0 = time.time()
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Tiempo (s)", "Raw", "mV", "Fuerza (N)"])
        while time.time() - t0 < duracion:
            raw = adc.read_data()
            delta = raw - raw_zero
            mv = mainUni.code_to_mV(delta, mainUni.GAIN)
            fuerza = (mv / mainUni.FS_mV) * mainUni.FS_N
            t = time.time() - t0

            writer.writerow([t, raw, mv, fuerza])
            tiempos.append(t); raws.append(raw); voltajes.append(mv); fuerzas.append(fuerza)

            print(f"t={t:.2f}s Raw={raw} mV={mv:.3f} Fuerza={fuerza:.2f}N")
            time.sleep(0.01)

    return tiempos, voltajes, fuerzas

def graficar(tiempos, voltajes, fuerzas):
    plt.figure(figsize=(10,5))
    plt.subplot(2,1,1)
    plt.plot(tiempos, voltajes, label="Voltaje (mV)")
    plt.ylabel("mV"); plt.legend()

    plt.subplot(2,1,2)
    plt.plot(tiempos, fuerzas, color="orange", label="Fuerza (N)")
    plt.xlabel("Tiempo (s)"); plt.ylabel("N"); plt.legend()
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    duracion = int(input("⏱️  Tiempo de adquisición (segundos): "))
    filename = input("💾 Nombre de archivo CSV [mediciones.csv]: ") or "mediciones.csv"

    tiempos, voltajes, fuerzas = adquirir_datos(duracion, filename)
    print(f"\n✅ Datos guardados en {filename}")
    graficar(tiempos, voltajes, fuerzas)
