"""Resuelve todas las instancias, valida y escribe las salidas.

Por cada instancia y cada forma de medir el costo corre el modelo exacto y los
tres metodos aproximados, y deja:

  salidas/itinerario_<instancia>_<medicion>.txt  el itinerario, legible
  salidas/resumen_resultados.csv                 la tabla comparativa
  salidas/resultados.json                        todo el detalle

La validacion va por dos lados: en I08 se contrasta el optimo del modelo contra
la enumeracion de las 40.320 secuencias, y en todas se revisa que la solucion
sea de verdad un circuito cerrado que pase una sola vez por cada nodo.
"""

import os

import comun as c
import fase4_modelo_mtz as modelo
import fase5_heuristicas as heur
from fase1_depuracion import cargar_nodos

INSTANCIAS_EXACTAS = ["I08", "I10", "I20", "I37", "I56"]
INSTANCIAS_TODAS = ["I08", "I10", "I20", "I37", "I56", "I231"]
LIMITE_TIEMPO = 300


def verificar_circuito(ruta, n):
    """Revisa que la ruta sea un solo ciclo cerrado, sin repetidos ni faltantes."""
    if ruta is None:
        return False, "sin solucion"
    if ruta[0] != 0 or ruta[-1] != 0:
        return False, "no inicia y termina en el deposito"
    interior = ruta[1:-1]
    if len(interior) != n - 1:
        return False, "el numero de visitas no coincide con el de nodos"
    if len(set(interior)) != n - 1:
        return False, "hay nodos repetidos"
    if set(interior) != set(range(1, n)):
        return False, "hay nodos sin visitar"
    return True, "circuito unico, cerrado y sin repeticiones"


def escribir_itinerario(nodos, ruta, cst, titulo_, ruta_archivo, extra=None):
    with open(ruta_archivo, "w", encoding="utf-8") as f:
        f.write(titulo_ + "\n")
        f.write("=" * len(titulo_) + "\n\n")
        if extra:
            for k, v in extra.items():
                f.write("%-28s %s\n" % (k + ":", v))
            f.write("\n")
        f.write("%-5s %-34s %12s %12s\n" % ("Orden", "Punto", "Tramo (m)", "Acumulado"))
        f.write("-" * 66 + "\n")
        acum = 0.0
        for k, idx in enumerate(ruta):
            tramo = 0.0 if k == 0 else cst[ruta[k - 1]][idx]
            acum += tramo
            etiqueta = nodos[idx]["direccion"]
            if nodos[idx]["tipo"] == "deposito":
                etiqueta += " (inicio y cierre)"
            f.write("%-5d %-34s %12.1f %12.1f\n" % (k, etiqueta[:34], tramo, acum))
        f.write("-" * 66 + "\n")
        f.write("%-40s %25.1f\n" % ("DISTANCIA TOTAL (m)", acum))
        f.write("%-40s %25.2f\n" % ("DISTANCIA TOTAL (km)", acum / 1000.0))
    return acum


def evaluacion_cruzada(resultados):
    """Cuanto cuesta optimizar con la medicion equivocada.

    Se toma la ruta optima calculada en linea recta, se mide sobre la red vial y
    se compara con la ruta que si es optima ahi. La diferencia son los metros de
    mas que uno termina haciendo por haber ignorado que se circula por calles.
    """
    filas = []
    for nombre, bloque in resultados.items():
        if "geodesica" not in bloque or "vial" not in bloque:
            continue
        geo, vial = bloque["geodesica"], bloque["vial"]
        sec_geo = (geo.get("exacto") or geo["heuristicas"][2])["secuencia"]
        sec_vial = (vial.get("exacto") or vial["heuristicas"][2])["secuencia"]
        if not sec_geo or not sec_vial:
            continue
        cst_geo = c.cargar_matriz_binaria(c.ruta_salida("matriz_geodesica_%s.bin" % nombre))
        cst_vial = c.cargar_matriz_binaria(c.ruta_salida("matriz_vial_%s.bin" % nombre))
        d_geo_en_geo = modelo.longitud(cst_geo, sec_geo)
        d_geo_en_vial = modelo.longitud(cst_vial, sec_geo)
        d_vial_en_vial = modelo.longitud(cst_vial, sec_vial)
        filas.append({
            "instancia": nombre,
            "viviendas": bloque["viviendas"],
            "optimo_geodesico_km": round(d_geo_en_geo / 1000, 3),
            "optimo_vial_km": round(d_vial_en_vial / 1000, 3),
            "factor_rodeo": round(d_vial_en_vial / d_geo_en_geo, 3),
            "orden_geodesico_medido_en_red_km": round(d_geo_en_vial / 1000, 3),
            "sobrecosto_por_medir_en_recta_km": round((d_geo_en_vial - d_vial_en_vial) / 1000, 3),
            "sobrecosto_%": round(100 * (d_geo_en_vial - d_vial_en_vial) / d_vial_en_vial, 2),
            "misma_secuencia": sec_geo == sec_vial or sec_geo == sec_vial[::-1],
        })
        print("  %-4s factor de rodeo x%.2f | optimizar en linea recta cuesta "
              "%+.2f %% sobre la red real"
              % (nombre, filas[-1]["factor_rodeo"], filas[-1]["sobrecosto_%"]))
    return filas


def ejecutar(limite_tiempo=LIMITE_TIEMPO):
    c.titulo("FASE 6. Solucion, comparacion y validacion")
    resultados = {}
    filas_resumen = []

    mediciones = [("geodesica", "matriz_geodesica_%s.bin")]
    if os.path.exists(c.ruta_salida("matriz_vial_I08.bin")):
        mediciones.append(("vial", "matriz_vial_%s.bin"))
    else:
        print("  (La matriz vial no esta disponible; se reporta solo la "
              "medicion geodesica.)\n")

    for nombre in INSTANCIAS_TODAS:
        nodos, _ = cargar_nodos(nombre)
        resultados[nombre] = {"viviendas": len(nodos) - 1, "nodos": len(nodos)}

        for medicion, patron in mediciones:
            ruta_bin = c.ruta_salida(patron % nombre)
            if not os.path.exists(ruta_bin):
                continue
            cst = c.cargar_matriz_binaria(ruta_bin)
            bloque = {}

            # primero los metodos rapidos
            aproximados = heur.ejecutar_todas(cst)
            for a in aproximados:
                ok, nota = verificar_circuito(a["secuencia"], len(cst))
                a["circuito_valido"] = ok
                a["verificacion"] = nota
            bloque["heuristicas"] = aproximados

            # y ahora el modelo, si la instancia es manejable
            exacto = None
            if nombre in INSTANCIAS_EXACTAS:
                exacto = modelo.resolver(cst, limite_tiempo=limite_tiempo)
                ok, nota = verificar_circuito(exacto["secuencia"], len(cst))
                exacto["circuito_valido"] = ok
                exacto["verificacion"] = nota
                bloque["exacto"] = exacto

            # en la instancia chica se comprueba contra fuerza bruta
            if nombre == "I08":
                fuerza = modelo.enumerar(cst)
                coincide = abs(fuerza["distancia_m"] - exacto["distancia_m"]) < 1e-6
                fuerza["coincide_con_el_modelo"] = coincide
                bloque["enumeracion"] = fuerza

            mejor = exacto if exacto and exacto["secuencia"] else aproximados[-1]
            escribir_itinerario(
                nodos, mejor["secuencia"], cst,
                "Itinerario optimizado - instancia %s - medicion %s" % (nombre, medicion),
                c.ruta_salida("itinerario_%s_%s.txt" % (nombre, medicion)),
                extra={
                    "Distrito": c.DISTRITO,
                    "Viviendas": len(nodos) - 1,
                    "Punto de inicio y cierre": nodos[0]["direccion"],
                    "Metodo": ("modelo exacto MTZ" if exacto and exacto["secuencia"]
                               else mejor["metodo"]),
                    "Estado": (exacto["estado"] if exacto else "heuristico"),
                })

            base = aproximados[0]["distancia_m"]          # orden de lista
            vmc = aproximados[1]["distancia_m"]
            opt2 = aproximados[2]["distancia_m"]
            ref = exacto["distancia_m"] if exacto and exacto["distancia_m"] else None
            filas_resumen.append({
                "instancia": nombre,
                "medicion": medicion,
                "viviendas": len(nodos) - 1,
                "nodos": len(nodos),
                "orden_lista_km": round(base / 1000, 3),
                "vecino_cercano_km": round(vmc / 1000, 3),
                "vmc_2opt_km": round(opt2 / 1000, 3),
                "optimo_km": round(ref / 1000, 3) if ref else "",
                "estado_modelo": exacto["estado"] if exacto else "no resuelto",
                "brecha_%": (round(100 * exacto["brecha_relativa"], 3)
                             if exacto and exacto["brecha_relativa"] is not None else ""),
                "segundos_modelo": exacto["segundos_solucion"] if exacto else "",
                "ahorro_vs_lista_%": (round(100 * (base - ref) / base, 1) if ref else
                                      round(100 * (base - opt2) / base, 1)),
                "exceso_2opt_vs_optimo_%": (round(100 * (opt2 - ref) / ref, 2) if ref else ""),
            })
            resultados[nombre][medicion] = bloque
            print("  %-4s %-9s  lista %7.2f km | v.cercano %7.2f km | 2-opt %7.2f km | "
                  "optimo %s"
                  % (nombre, medicion, base / 1000, vmc / 1000, opt2 / 1000,
                     ("%7.2f km (%s, %.1f s)" % (ref / 1000, exacto["estado"],
                                                 exacto["segundos_solucion"]))
                     if ref else "   n/d"))

    cruzada = evaluacion_cruzada(resultados)
    if cruzada:
        c.escribir_csv(cruzada, list(cruzada[0].keys()),
                       c.ruta_salida("evaluacion_cruzada.csv"))

    c.guardar_json(resultados, c.ruta_salida("resultados.json"))
    campos = list(filas_resumen[0].keys())
    c.escribir_csv(filas_resumen, campos, c.ruta_salida("resumen_resultados.csv"))
    print()
    print("Salidas escritas en la carpeta 'salidas'.")
    return resultados, filas_resumen


if __name__ == "__main__":
    ejecutar()
