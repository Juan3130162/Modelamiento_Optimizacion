"""Metodos aproximados: los tres recorridos contra los que se compara el optimo.

  orden_de_lista      -> visita en el orden en que vienen las viviendas.
                         Es el comprador que sigue la lista tal como la recibio.
  vecino_mas_cercano  -> en cada paso salta a la vivienda no visitada mas cerca.
  dos_opt             -> agarra un recorrido y le deshace los cruces mientras
                         encuentre alguno que valga la pena.

Los tres son deterministas: misma entrada, misma salida.
"""

import time


def longitud(cst, ruta):
    return sum(cst[ruta[k]][ruta[k + 1]] for k in range(len(ruta) - 1))


def orden_de_lista(cst):
    n = len(cst)
    ruta = list(range(n)) + [0]
    return {"metodo": "orden de lista", "secuencia": ruta,
            "distancia_m": longitud(cst, ruta), "segundos": 0.0}


def vecino_mas_cercano(cst, inicio=0):
    n = len(cst)
    t0 = time.perf_counter()
    pendientes = set(range(n)) - {inicio}
    ruta, actual = [inicio], inicio
    while pendientes:
        siguiente = min(pendientes, key=lambda j: cst[actual][j])
        pendientes.remove(siguiente)
        ruta.append(siguiente)
        actual = siguiente
    ruta.append(inicio)
    return {"metodo": "vecino mas cercano", "secuencia": ruta,
            "distancia_m": longitud(cst, ruta),
            "segundos": round(time.perf_counter() - t0, 4)}


def dos_opt(cst, ruta_inicial, max_pasadas=200):
    """Intercambia pares de aristas y, si mejora, invierte el segmento del medio."""
    t0 = time.perf_counter()
    ruta = list(ruta_inicial)
    n = len(ruta) - 1                      # el ultimo nodo repite el deposito
    mejora, pasadas = True, 0
    while mejora and pasadas < max_pasadas:
        mejora, pasadas = False, pasadas + 1
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                a, b = ruta[i - 1], ruta[i]
                cc, d = ruta[j], ruta[j + 1]
                if a == cc or b == d:
                    continue
                delta = (cst[a][cc] + cst[b][d]) - (cst[a][b] + cst[cc][d])
                if delta < -1e-9:
                    ruta[i:j + 1] = reversed(ruta[i:j + 1])
                    mejora = True
        if not mejora:
            break
    return {"metodo": "vecino mas cercano + 2-opt", "secuencia": ruta,
            "distancia_m": longitud(cst, ruta),
            "segundos": round(time.perf_counter() - t0, 4),
            "pasadas": pasadas}


def ejecutar_todas(cst):
    base = orden_de_lista(cst)
    vmc = vecino_mas_cercano(cst)
    mejorado = dos_opt(cst, vmc["secuencia"])
    return [base, vmc, mejorado]
