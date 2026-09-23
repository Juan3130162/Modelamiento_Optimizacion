"""Depuracion del archivo original y armado de las instancias de prueba.

Salidas: salidas/candidatas_<instancia>.csv y salidas/instancias.json

Las instancias son anidadas (I08 c I10 c I20 c I37 c I56) para poder ver como
se comporta el modelo a medida que crece el numero de viviendas sin cambiar de
territorio ni de perfil de comprador.
"""

import random

import comun as c

SEMILLA = 2026          # fija, para que el experimento se pueda repetir
ANIOS_VIGENCIA = (2019, 2020)
PRECIO_MAXIMO = 400000
HABITACIONES_MINIMAS = 4


def construir_instancias():
    c.titulo("FASE 1. Lectura y depuracion del archivo de origen")

    filas, descartadas = c.leer_csv_robusto()
    print("Registros leidos correctamente : %d" % len(filas))
    print("Registros descartados          : %d" % descartadas)

    viviendas = c.viviendas_del_distrito(filas)
    print("Viviendas en el distrito %-6s: %d" % (c.DISTRITO, len(viviendas)))

    coords = {(v["lat"], v["lon"]) for v in viviendas}
    print("Coordenadas distintas          : %d" % len(coords))
    faltantes = [v for v in viviendas if v["lat"] is None or v["lon"] is None]
    print("Viviendas sin coordenadas      : %d" % len(faltantes))

    # La estacion es el punto de inicio y cierre; hay que deducir donde queda
    estacion = c.estimar_estacion(viviendas)
    print()
    print("Deposito (%s) estimado por trilateracion:" % viviendas[0]["estacion"])
    print("  latitud %.6f   longitud %.6f" % (estacion["lat"], estacion["lon"]))
    print("  error cuadratico medio %.1f m sobre %d observaciones (maximo %.1f m)"
          % (estacion["ecm_m"], estacion["observaciones"], estacion["max_residuo_m"]))
    estacion["nombre"] = viviendas[0]["estacion"]

    # Filtros del comprador, uno encima del otro
    vigentes = [v for v in viviendas if v["anio_venta"] in ANIOS_VIGENCIA]
    i56 = [v for v in vigentes if v["precio"] is not None and v["precio"] <= PRECIO_MAXIMO]
    i37 = [v for v in i56 if v["habitaciones"] is not None
           and v["habitaciones"] >= HABITACIONES_MINIMAS]

    print()
    print("Aplicacion de los filtros del perfil de comprador:")
    print("  ventas de %d-%d                       : %3d viviendas" % (ANIOS_VIGENCIA[0], ANIOS_VIGENCIA[1], len(vigentes)))
    print("  ... y precio <= %d AUD             : %3d viviendas" % (PRECIO_MAXIMO, len(i56)))
    print("  ... y %d habitaciones o mas             : %3d viviendas" % (HABITACIONES_MINIMAS, len(i37)))

    # Subconjuntos mas pequenos, para el estudio de escalabilidad
    orden = list(i37)
    random.Random(SEMILLA).shuffle(orden)
    subconjuntos = {
        "I08": orden[:8],
        "I10": orden[:10],
        "I20": orden[:20],
        "I37": i37,
        "I56": i56,
        "I231": viviendas,          # el distrito completo, sin filtros
    }

    instancias = {}
    for nombre, lista in subconjuntos.items():
        lista = sorted(lista, key=lambda v: v["direccion"])
        ruta = c.ruta_salida("candidatas_%s.csv" % nombre)
        c.escribir_csv(lista, ["direccion", "lat", "lon", "precio", "habitaciones",
                               "banos", "mes_venta", "anio_venta", "dist_estacion"], ruta)
        instancias[nombre] = {
            "viviendas": len(lista),
            "nodos": len(lista) + 1,            # + el deposito
            "archivo": "candidatas_%s.csv" % nombre,
        }
        print("  instancia %-4s -> %2d viviendas (%2d nodos con deposito) -> %s"
              % (nombre, len(lista), len(lista) + 1, "candidatas_%s.csv" % nombre))

    meta = {
        "distrito": c.DISTRITO,
        "registros_origen": len(filas),
        "viviendas_distrito": len(viviendas),
        "coordenadas_distintas": len(coords),
        "filtros": {
            "anios_vigencia": list(ANIOS_VIGENCIA),
            "precio_maximo_aud": PRECIO_MAXIMO,
            "habitaciones_minimas": HABITACIONES_MINIMAS,
        },
        "deposito": estacion,
        "semilla": SEMILLA,
        "instancias": instancias,
    }
    c.guardar_json(meta, c.ruta_salida("instancias.json"))
    print()
    print("Metadatos escritos en salidas/instancias.json")
    return meta


def cargar_nodos(nombre_instancia):
    """Nodos de una instancia. El 0 siempre es el deposito, ahi empieza y termina."""
    meta = c.cargar_json(c.ruta_salida("instancias.json"))
    dep = meta["deposito"]
    nodos = [{"id": 0, "tipo": "deposito", "direccion": dep["nombre"],
              "lat": dep["lat"], "lon": dep["lon"]}]
    filas = c.leer_csv(c.ruta_salida(meta["instancias"][nombre_instancia]["archivo"]))
    for i, fila in enumerate(filas, start=1):
        nodos.append({"id": i, "tipo": "vivienda", "direccion": fila["direccion"],
                      "lat": float(fila["lat"]), "lon": float(fila["lon"]),
                      "precio": float(fila["precio"]) if fila["precio"] else None,
                      "habitaciones": fila["habitaciones"]})
    return nodos, meta


if __name__ == "__main__":
    construir_instancias()
