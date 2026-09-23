"""Matriz de distancias sobre la red vial, con Dijkstra.

Necesita bertram_red_vial.graphml, que se baja una sola vez con
descargar_red_vial.py.

La idea: la malla se representa como un digrafo (nodos = intersecciones,
arcos = tramos con su longitud y su sentido), cada vivienda se engancha al nodo
mas cercano y se corre Dijkstra una vez por origen. Cada corrida llena una fila
entera de la matriz.

Esta matriz no tiene por que ser simetrica: con sentidos unicos, ir puede
costar distinto a volver.
"""

import os
import time

import comun as c
from fase1_depuracion import cargar_nodos

INSTANCIAS = ["I08", "I10", "I20", "I37", "I56", "I231"]


def hay_red():
    return os.path.exists(c.ARCHIVO_GRAFO)


def cargar_red():
    import osmnx as ox
    G = ox.load_graphml(c.ARCHIVO_GRAFO)
    return G


def asociar_nodos(G, nodos):
    import osmnx as ox
    lats = [n["lat"] for n in nodos]
    lons = [n["lon"] for n in nodos]
    return list(ox.distance.nearest_nodes(G, X=lons, Y=lats))


def matriz_vial(G, nodos_red):
    import networkx as nx
    n = len(nodos_red)
    m = [[0.0] * n for _ in range(n)]
    inalcanzables = 0
    for i, origen in enumerate(nodos_red):
        dist = nx.single_source_dijkstra_path_length(G, origen, weight="length")
        for j, destino in enumerate(nodos_red):
            if i == j:
                continue
            if destino in dist:
                m[i][j] = float(dist[destino])
            else:
                m[i][j] = float("inf")
                inalcanzables += 1
    return m, inalcanzables


def ejecutar():
    c.titulo("FASE 3. Matriz de distancias sobre la red vial (Dijkstra)")
    if not hay_red():
        print("  No se encontro '%s'." % os.path.basename(c.ARCHIVO_GRAFO))
        print("  Ejecute primero 'descargar_red_vial.py' en un equipo con "
              "conexion a internet.")
        print("  El resto del programa continua solo con la medicion geodesica.")
        return None

    import networkx as nx
    G = cargar_red()
    print("  Red vial: %d nodos, %d arcos" % (G.number_of_nodes(), G.number_of_edges()))
    print("  Fuertemente conexa: %s" % nx.is_strongly_connected(G))

    reporte = {"nodos_red": G.number_of_nodes(), "arcos_red": G.number_of_edges(),
               "fuertemente_conexa": bool(nx.is_strongly_connected(G)),
               "instancias": {}}

    for nombre in INSTANCIAS:
        nodos, _ = cargar_nodos(nombre)
        t0 = time.perf_counter()
        nodos_red = asociar_nodos(G, nodos)
        desplaz = [c.geodesica(n["lat"], n["lon"],
                               G.nodes[r]["y"], G.nodes[r]["x"])
                   for n, r in zip(nodos, nodos_red)]
        m, inalcanzables = matriz_vial(G, nodos_red)
        t = time.perf_counter() - t0

        # cuantos pares tienen ida y vuelta distintas
        n = len(m)
        asim = sum(1 for i in range(n) for j in range(i + 1, n)
                   if abs(m[i][j] - m[j][i]) > 1.0)
        pares = n * (n - 1) // 2

        ruta = c.ruta_salida("matriz_vial_%s.bin" % nombre)
        c.guardar_matriz_binaria(m, ruta)
        reporte["instancias"][nombre] = {
            "nodos": n,
            "nodos_red_distintos": len(set(nodos_red)),
            "desplazamiento_medio_m": round(sum(desplaz) / len(desplaz), 1),
            "desplazamiento_maximo_m": round(max(desplaz), 1),
            "pares_inalcanzables": inalcanzables,
            "pares_asimetricos": asim,
            "porcentaje_asimetrico": round(100.0 * asim / pares, 1),
            "segundos": round(t, 2),
        }
        print("  %-4s n=%3d  nodos de red distintos %3d  ajuste medio %5.1f m  "
              "pares asimetricos %4.1f %%  (%.1f s)"
              % (nombre, n, len(set(nodos_red)),
                 reporte["instancias"][nombre]["desplazamiento_medio_m"],
                 reporte["instancias"][nombre]["porcentaje_asimetrico"], t))

    c.guardar_json(reporte, c.ruta_salida("red_vial.json"))
    return reporte


if __name__ == "__main__":
    ejecutar()
