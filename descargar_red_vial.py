"""Baja la red vial del distrito desde OpenStreetMap y la guarda como graphml.

Se corre una sola vez, en un equipo con internet. Despues el resto del programa
trabaja con el archivo y ya no necesita conexion.

    pip install osmnx pandas
    python descargar_red_vial.py

Deja bertram_red_vial.graphml y reporte_red_vial.txt en la misma carpeta.
"""

import csv
import io
import json
import os
import sys

RUTA_CSV = "all_perth_310121.csv"
DISTRITO = "Bertram"
MARGEN_GRADOS = 0.006          # ~600 m de aire alrededor del distrito
SALIDA_GRAFO = "bertram_red_vial.graphml"
SALIDA_REPORTE = "reporte_red_vial.txt"


def leer_csv_robusto(ruta):
    """Lee el CSV original, que trae cada registro partido en dos lineas.

    Mismo arreglo que en comun.py: se repite aca para que este script se pueda
    llevar solo a otra maquina.
    """
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        crudo = f.read()

    texto = crudo.replace('"', "").replace("\r", "")
    registros = []
    for linea in texto.split("\n"):
        if linea.startswith(",") and registros:
            registros[-1] += linea          # continuacion del registro anterior
        elif linea.strip():
            registros.append(linea)

    lector = csv.DictReader(io.StringIO("\n".join(registros)))
    filas = [fila for fila in lector if len(fila) == 19 and None not in fila.values()]
    return filas


def coordenadas_del_distrito(filas, distrito):
    puntos = []
    for fila in filas:
        if fila["SUBURB"] == distrito:
            puntos.append((float(fila["LATITUDE"]), float(fila["LONGITUDE"])))
    return puntos


def descargar_grafo(bbox):
    """bbox = (oeste, sur, este, norte). Sirve con osmnx 1.x y 2.x."""
    import osmnx as ox

    oeste, sur, este, norte = bbox
    try:                                            # osmnx >= 2.0
        return ox.graph_from_bbox(bbox=(oeste, sur, este, norte), network_type="drive")
    except TypeError:                               # osmnx 1.x
        return ox.graph_from_bbox(norte, sur, este, oeste, network_type="drive")


def main():
    carpeta = os.path.dirname(os.path.abspath(__file__))
    ruta_csv = os.path.join(carpeta, RUTA_CSV)
    if not os.path.exists(ruta_csv):
        sys.exit("No se encontro '%s' junto al script. Copie el script a la "
                 "carpeta donde esta el CSV y vuelva a ejecutarlo." % RUTA_CSV)

    try:
        import osmnx as ox
        import networkx as nx
    except ImportError:
        sys.exit("Faltan librerias. Ejecute primero:  pip install osmnx pandas")

    print("1/5  Leyendo el archivo de origen ...")
    filas = leer_csv_robusto(ruta_csv)
    puntos = coordenadas_del_distrito(filas, DISTRITO)
    print("     registros totales: %d   viviendas en %s: %d" % (len(filas), DISTRITO, len(puntos)))
    if not puntos:
        sys.exit("No se encontraron viviendas del distrito '%s'." % DISTRITO)

    lats = [p[0] for p in puntos]
    lons = [p[1] for p in puntos]
    bbox = (min(lons) - MARGEN_GRADOS, min(lats) - MARGEN_GRADOS,
            max(lons) + MARGEN_GRADOS, max(lats) + MARGEN_GRADOS)
    print("2/5  Rectangulo de descarga (O,S,E,N): %.6f, %.6f, %.6f, %.6f" % bbox)

    print("3/5  Descargando la red vial desde OpenStreetMap (puede tardar 1-3 minutos) ...")
    G = descargar_grafo(bbox)
    print("     nodos: %d   arcos: %d" % (G.number_of_nodes(), G.number_of_edges()))

    print("4/5  Verificando cobertura y conectividad ...")
    nodos = ox.distance.nearest_nodes(G, X=lons, Y=lats)
    dists = []
    for (lat, lon), n in zip(puntos, nodos):
        dists.append(ox.distance.great_circle(lat, lon, G.nodes[n]["y"], G.nodes[n]["x"]))
    fuerte = nx.is_strongly_connected(G)
    debil = nx.is_weakly_connected(G)
    n_comp = nx.number_strongly_connected_components(G)

    print("5/5  Guardando ...")
    ox.save_graphml(G, os.path.join(carpeta, SALIDA_GRAFO))

    reporte = {
        "distrito": DISTRITO,
        "viviendas": len(puntos),
        "bbox_oeste_sur_este_norte": bbox,
        "nodos": G.number_of_nodes(),
        "arcos": G.number_of_edges(),
        "fuertemente_conexo": fuerte,
        "debilmente_conexo": debil,
        "componentes_fuertes": n_comp,
        "dist_vivienda_a_nodo_m": {
            "promedio": round(sum(dists) / len(dists), 2),
            "maxima": round(max(dists), 2),
        },
        "nodos_distintos_asignados": len(set(nodos)),
        "osmnx": ox.__version__,
    }
    with open(os.path.join(carpeta, SALIDA_REPORTE), "w", encoding="utf-8") as f:
        f.write(json.dumps(reporte, indent=2, ensure_ascii=False))

    print()
    print(json.dumps(reporte, indent=2, ensure_ascii=False))
    print()
    print("Listo. Se generaron '%s' y '%s' en:" % (SALIDA_GRAFO, SALIDA_REPORTE))
    print("   ", carpeta)


if __name__ == "__main__":
    main()
