"""Corre la parte vial y consolida el resumen.

Sirve cuando la fase 6 ya dejo hechas las instancias geodesicas y no vale la
pena repetir los modelos que ya cerraron. Va guardando despues de cada
instancia, asi que si se interrumpe no se pierde lo resuelto.
"""

import os
import sys

import comun as c
import fase4_modelo_mtz as modelo
import fase5_heuristicas as heur
import fase6_comparacion as f6
from fase1_depuracion import cargar_nodos

INSTANCIAS_EXACTAS = ["I08", "I10", "I20", "I37", "I56"]
INSTANCIAS = ["I08", "I10", "I20", "I37", "I56", "I231"]
LIMITE = 300


def resolver_vial():
    res = c.cargar_json(c.ruta_salida("resultados.json"))
    for nombre in INSTANCIAS:
        if "vial" in res.get(nombre, {}):
            print("  %-4s ya estaba resuelta" % nombre)
            continue
        ruta_bin = c.ruta_salida("matriz_vial_%s.bin" % nombre)
        if not os.path.exists(ruta_bin):
            continue
        nodos, _ = cargar_nodos(nombre)
        cst = c.cargar_matriz_binaria(ruta_bin)
        bloque = {}

        aproximados = heur.ejecutar_todas(cst)
        for a in aproximados:
            ok, nota = f6.verificar_circuito(a["secuencia"], len(cst))
            a["circuito_valido"], a["verificacion"] = ok, nota
        bloque["heuristicas"] = aproximados

        exacto = None
        if nombre in INSTANCIAS_EXACTAS:
            exacto = modelo.resolver(cst, limite_tiempo=LIMITE)
            ok, nota = f6.verificar_circuito(exacto["secuencia"], len(cst))
            exacto["circuito_valido"], exacto["verificacion"] = ok, nota
            bloque["exacto"] = exacto

        if nombre == "I08":
            fuerza = modelo.enumerar(cst)
            fuerza["coincide_con_el_modelo"] = abs(
                fuerza["distancia_m"] - exacto["distancia_m"]) < 1e-6
            bloque["enumeracion"] = fuerza

        mejor = exacto if exacto and exacto["secuencia"] else aproximados[-1]
        f6.escribir_itinerario(
            nodos, mejor["secuencia"], cst,
            "Itinerario optimizado - instancia %s - medicion vial" % nombre,
            c.ruta_salida("itinerario_%s_vial.txt" % nombre),
            extra={"Distrito": c.DISTRITO, "Viviendas": len(nodos) - 1,
                   "Punto de inicio y cierre": nodos[0]["direccion"],
                   "Metodo": ("modelo exacto MTZ" if exacto and exacto["secuencia"]
                              else mejor["metodo"]),
                   "Estado": (exacto["estado"] if exacto else "heuristico")})

        res[nombre]["vial"] = bloque
        c.guardar_json(res, c.ruta_salida("resultados.json"))   # por si se cae
        print("  %-4s vial  lista %7.2f | 2-opt %7.2f | optimo %s"
              % (nombre, aproximados[0]["distancia_m"] / 1000,
                 aproximados[2]["distancia_m"] / 1000,
                 ("%7.2f km (%s, %.1f s)" % (exacto["distancia_m"] / 1000,
                                             exacto["estado"], exacto["segundos_solucion"]))
                 if exacto and exacto["distancia_m"] else "n/d"))
        sys.stdout.flush()
    return res


def consolidar(res):
    """Rearma resumen_resultados.csv con todo lo que haya en resultados.json."""
    filas = []
    for nombre in INSTANCIAS:
        bloque = res.get(nombre, {})
        for medicion in ("geodesica", "vial"):
            if medicion not in bloque:
                continue
            b = bloque[medicion]
            base = b["heuristicas"][0]["distancia_m"]
            vmc = b["heuristicas"][1]["distancia_m"]
            opt2 = b["heuristicas"][2]["distancia_m"]
            ex = b.get("exacto")
            ref = ex["distancia_m"] if ex and ex["distancia_m"] else None
            filas.append({
                "instancia": nombre, "medicion": medicion,
                "viviendas": bloque["viviendas"], "nodos": bloque["nodos"],
                "orden_lista_km": round(base / 1000, 3),
                "vecino_cercano_km": round(vmc / 1000, 3),
                "vmc_2opt_km": round(opt2 / 1000, 3),
                "optimo_km": round(ref / 1000, 3) if ref else "",
                "estado_modelo": ex["estado"] if ex else "no resuelto",
                "brecha_%": (round(100 * ex["brecha_relativa"], 3)
                             if ex and ex["brecha_relativa"] is not None else ""),
                "segundos_modelo": ex["segundos_solucion"] if ex else "",
                "ahorro_vs_lista_%": (round(100 * (base - ref) / base, 1) if ref
                                      else round(100 * (base - opt2) / base, 1)),
                "exceso_2opt_vs_optimo_%": (round(100 * (opt2 - ref) / ref, 2) if ref else ""),
            })
    c.escribir_csv(filas, list(filas[0].keys()), c.ruta_salida("resumen_resultados.csv"))
    return filas


if __name__ == "__main__":
    c.titulo("Medicion sobre la red vial")
    res = resolver_vial()
    c.titulo("Evaluacion cruzada entre mediciones")
    cruzada = f6.evaluacion_cruzada(res)
    if cruzada:
        c.escribir_csv(cruzada, list(cruzada[0].keys()),
                       c.ruta_salida("evaluacion_cruzada.csv"))
    consolidar(res)
    print("\nResumen consolidado en salidas/resumen_resultados.csv")
