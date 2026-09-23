"""Copia a app/datos/ lo que necesita la interfaz web.

Son cuatro archivos: el listado de viviendas, las dos matrices en binario y un
json con el deposito y el resultado del modelo exacto. La idea es que la
interfaz lea exactamente lo que produjo el programa, sin duplicar datos.
"""

import os
import shutil

import comun as c

DESTINO = os.path.join(c.RAIZ, "app", "datos")


def ejecutar():
    os.makedirs(DESTINO, exist_ok=True)
    for archivo in ["candidatas_I231.csv", "matriz_geodesica_I231.bin",
                    "matriz_vial_I231.bin"]:
        origen = c.ruta_salida(archivo)
        if os.path.exists(origen):
            shutil.copy2(origen, os.path.join(DESTINO, archivo))
            print("  copiado %s (%d bytes)" % (archivo, os.path.getsize(origen)))

    meta = c.cargar_json(c.ruta_salida("instancias.json"))
    referencia = {"deposito": meta["deposito"],
                  "distrito": meta["distrito"],
                  "viviendas_distrito": meta["viviendas_distrito"]}

    # se prefiere el resultado vial; si no esta, sirve el geodesico
    if os.path.exists(c.ruta_salida("resultados.json")):
        res = c.cargar_json(c.ruta_salida("resultados.json"))
        bloque = res.get("I37", {})
        for medicion in ("vial", "geodesica"):
            if medicion in bloque and bloque[medicion].get("exacto"):
                ex = bloque[medicion]["exacto"]
                heur = bloque[medicion]["heuristicas"][2]
                referencia["instancia_principal"] = {
                    "viviendas": bloque["viviendas"],
                    "precio_max": meta["filtros"]["precio_maximo_aud"],
                    "habitaciones_min": meta["filtros"]["habitaciones_minimas"],
                    "anio_desde": meta["filtros"]["anios_vigencia"][0],
                    "medicion": medicion,
                    "optimo_vial_m": ex["distancia_m"],
                    "estado": ex["estado"],
                    "segundos": ex["segundos_solucion"],
                    "exceso_2opt_vial_%": round(
                        100 * (heur["distancia_m"] - ex["distancia_m"]) / ex["distancia_m"], 2),
                }
                break

    c.guardar_json(referencia, os.path.join(DESTINO, "referencia.json"))
    print("  referencia.json escrito")


if __name__ == "__main__":
    ejecutar()
