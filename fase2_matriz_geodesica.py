"""Matriz de distancias en linea recta.

Escribe cada matriz en binario y en texto para poder comparar los dos formatos:
tamano en disco, tiempo de lectura y precision al recuperarla.
"""

import os
import time

import comun as c
from fase1_depuracion import cargar_nodos

INSTANCIAS = ["I08", "I10", "I20", "I37", "I56", "I231"]


def matriz_geodesica(nodos):
    n = len(nodos)
    m = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = c.geodesica(nodos[i]["lat"], nodos[i]["lon"],
                            nodos[j]["lat"], nodos[j]["lon"])
            m[i][j] = d
            m[j][i] = d                       # en linea recta ir y volver cuesta igual
    return m


def comparar_formatos(matriz, nombre):
    """Escribe la matriz en los dos formatos y mide que pasa con cada uno."""
    ruta_bin = c.ruta_salida("matriz_geodesica_%s.bin" % nombre)
    ruta_txt = c.ruta_salida("matriz_geodesica_%s.txt" % nombre)

    t0 = time.perf_counter(); bytes_bin = c.guardar_matriz_binaria(matriz, ruta_bin)
    t_esc_bin = time.perf_counter() - t0
    t0 = time.perf_counter(); bytes_txt = c.guardar_matriz_texto(matriz, ruta_txt)
    t_esc_txt = time.perf_counter() - t0

    t0 = time.perf_counter(); leida_bin = c.cargar_matriz_binaria(ruta_bin)
    t_lec_bin = time.perf_counter() - t0
    t0 = time.perf_counter()
    with open(ruta_txt, encoding="utf-8") as f:
        leida_txt = [[float(v) for v in linea.split(",")] for linea in f if linea.strip()]
    t_lec_txt = time.perf_counter() - t0

    # cuanto se desvia el valor recuperado del original
    err_bin = max(abs(leida_bin[i][j] - matriz[i][j])
                  for i in range(len(matriz)) for j in range(len(matriz)))
    err_txt = max(abs(leida_txt[i][j] - matriz[i][j])
                  for i in range(len(matriz)) for j in range(len(matriz)))

    return {
        "instancia": nombre,
        "orden": len(matriz),
        "bytes_binario": bytes_bin,
        "bytes_texto": bytes_txt,
        "razon_tamano_txt_bin": round(bytes_txt / bytes_bin, 2),
        "ms_escritura_binario": round(t_esc_bin * 1000, 2),
        "ms_escritura_texto": round(t_esc_txt * 1000, 2),
        "ms_lectura_binario": round(t_lec_bin * 1000, 2),
        "ms_lectura_texto": round(t_lec_txt * 1000, 2),
        "error_maximo_binario_m": err_bin,
        "error_maximo_texto_m": err_txt,
    }


def ejecutar():
    c.titulo("FASE 2. Matriz de distancias geodesicas (Karney, 2013)")
    reporte = []
    for nombre in INSTANCIAS:
        nodos, _ = cargar_nodos(nombre)
        t0 = time.perf_counter()
        m = matriz_geodesica(nodos)
        t = time.perf_counter() - t0
        info = comparar_formatos(m, nombre)
        info["ms_calculo"] = round(t * 1000, 1)
        info["distancias_distintas"] = len(m) * (len(m) - 1) // 2
        reporte.append(info)
        print("  %-4s n=%2d  %5d distancias  calculo %7.1f ms  "
              "binario %6d B  texto %6d B (x%.2f)  error texto %.4f m"
              % (nombre, info["orden"], info["distancias_distintas"], info["ms_calculo"],
                 info["bytes_binario"], info["bytes_texto"],
                 info["razon_tamano_txt_bin"], info["error_maximo_texto_m"]))

    c.guardar_json(reporte, c.ruta_salida("e_s_matrices.json"))
    print()
    print("El formato binario recupera los valores sin ninguna perdida "
          "(error maximo 0 m);\nel texto plano con dos decimales introduce un "
          "error de hasta 5 mm por celda.")
    return reporte


if __name__ == "__main__":
    ejecutar()
