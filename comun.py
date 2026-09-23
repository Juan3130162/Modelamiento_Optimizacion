"""Cosas que usan todos los modulos: leer el CSV, medir distancias y guardar archivos."""

import csv
import io
import json
import math
import os
import struct

RAIZ = os.path.dirname(os.path.abspath(__file__))
SALIDAS = os.path.join(RAIZ, "salidas")
ARCHIVO_ORIGEN = os.path.join(RAIZ, "all_perth_310121.csv")
ARCHIVO_GRAFO = os.path.join(RAIZ, "bertram_red_vial.graphml")

DISTRITO = "Bertram"
COLUMNAS = ["ADDRESS", "SUBURB", "PRICE", "BEDROOMS", "BATHROOMS", "GARAGE",
            "LAND_AREA", "FLOOR_AREA", "BUILD_YEAR", "CBD_DIST", "NEAREST_STN",
            "NEAREST_STN_DIST", "DATE_SOLD", "POSTCODE", "LATITUDE", "LONGITUDE",
            "NEAREST_SCH", "NEAREST_SCH_DIST", "NEAREST_SCH_RANK"]

os.makedirs(SALIDAS, exist_ok=True)


def ruta_salida(nombre):
    return os.path.join(SALIDAS, nombre)


def leer_csv_robusto(ruta=ARCHIVO_ORIGEN):
    """Lee el CSV original, que viene roto.

    El archivo mete un salto de linea justo despues de DATE_SOLD y envuelve todo
    entre comillas, asi que cada registro queda partido en dos lineas fisicas.
    Si se lee de frente con csv.reader o con pandas las columnas quedan corridas
    y el filtro por suburbio no devuelve nada.

    Truco: quitar comillas y CR (ningun campo tiene comas dentro de comillas de
    verdad) y pegar a la linea anterior toda linea que empiece con coma.
    """
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        crudo = f.read()

    texto = crudo.replace('"', "").replace("\r", "")
    registros = []
    for linea in texto.split("\n"):
        if linea.startswith(",") and registros:
            registros[-1] += linea
        elif linea.strip():
            registros.append(linea)

    lector = csv.DictReader(io.StringIO("\n".join(registros)))
    filas, descartadas = [], 0
    for fila in lector:
        if len(fila) != len(COLUMNAS) or None in fila.values():
            descartadas += 1
            continue
        filas.append(fila)
    return filas, descartadas


def _num(valor, tipo=float, defecto=None):
    try:
        return tipo(valor)
    except (TypeError, ValueError):
        return defecto


def viviendas_del_distrito(filas, distrito=DISTRITO):
    """Se queda con las filas del distrito y pasa a numeros lo que hace falta."""
    viviendas = []
    for fila in filas:
        if fila["SUBURB"] != distrito:
            continue
        viviendas.append({
            "direccion": fila["ADDRESS"].strip(),
            "precio": _num(fila["PRICE"], float),
            "habitaciones": _num(fila["BEDROOMS"], int),
            "banos": _num(fila["BATHROOMS"], int),
            "anio_venta": _num(str(fila["DATE_SOLD"])[-4:], int),
            "mes_venta": str(fila["DATE_SOLD"])[:2],
            "lat": _num(fila["LATITUDE"], float),
            "lon": _num(fila["LONGITUDE"], float),
            "estacion": fila["NEAREST_STN"].strip(),
            "dist_estacion": _num(fila["NEAREST_STN_DIST"], float),
        })
    viviendas.sort(key=lambda v: v["direccion"])
    return viviendas


# Proyeccion plana local. Sirve porque el distrito mide un par de kilometros;
# a esta escala tratar la zona como un plano no introduce error apreciable.
def _proyectar(lat, lon, lat0, lon0):
    x = math.radians(lon - lon0) * 6378137.0 * math.cos(math.radians(lat0))
    y = math.radians(lat - lat0) * 6356752.0
    return x, y


def _desproyectar(x, y, lat0, lon0):
    lat = lat0 + math.degrees(y / 6356752.0)
    lon = lon0 + math.degrees(x / (6378137.0 * math.cos(math.radians(lat0))))
    return lat, lon


def estimar_estacion(viviendas, iteraciones=60, tolerancia=1e-6):
    """Ubica la estacion por trilateracion.

    El dataset no trae las coordenadas de las estaciones, solo el nombre de la
    mas cercana y la distancia a ella. Con 231 viviendas de posicion conocida y
    231 distancias, la posicion queda de sobra determinada.

    Se resuelve por minimos cuadrados con Gauss-Newton: se arranca en el
    centroide, se linealiza el residuo ||p - q_i|| - d_i y se resuelve el
    sistema 2x2 en cada iteracion hasta que el paso sea menor a la tolerancia.
    Devuelve tambien el error cuadratico medio para saber que tan buena quedo.
    """
    lat0 = sum(v["lat"] for v in viviendas) / len(viviendas)
    lon0 = sum(v["lon"] for v in viviendas) / len(viviendas)
    puntos = [_proyectar(v["lat"], v["lon"], lat0, lon0) for v in viviendas]
    dist = [v["dist_estacion"] for v in viviendas]

    px, py = 0.0, 0.0
    for _ in range(iteraciones):
        a11 = a12 = a22 = b1 = b2 = 0.0
        for (qx, qy), d in zip(puntos, dist):
            dx, dy = px - qx, py - qy
            rho = math.hypot(dx, dy)
            if rho < 1e-9:
                continue
            jx, jy = dx / rho, dy / rho          # gradiente del residuo
            r = rho - d
            a11 += jx * jx; a12 += jx * jy; a22 += jy * jy
            b1 += jx * r;   b2 += jy * r
        det = a11 * a22 - a12 * a12
        if abs(det) < 1e-12:
            break
        sx = -(a22 * b1 - a12 * b2) / det
        sy = -(a11 * b2 - a12 * b1) / det
        px += sx; py += sy
        if math.hypot(sx, sy) < tolerancia:
            break

    residuos = [math.hypot(px - qx, py - qy) - d for (qx, qy), d in zip(puntos, dist)]
    ecm = math.sqrt(sum(r * r for r in residuos) / len(residuos))
    lat, lon = _desproyectar(px, py, lat0, lon0)
    return {"lat": lat, "lon": lon, "ecm_m": ecm,
            "max_residuo_m": max(abs(r) for r in residuos),
            "observaciones": len(viviendas)}


def geodesica(lat1, lon1, lat2, lon2):
    """Distancia en metros sobre el elipsoide WGS84.

    Usa geopy (que por debajo es geographiclib). Si no esta instalado cae a
    haversine, que a escala de un barrio se equivoca en menos del 0,5 %.
    """
    try:
        from geopy.distance import geodesic as _g
        return _g((lat1, lon1), (lat2, lon2)).meters
    except ImportError:
        r = 6371008.8
        p1, p2 = math.radians(lat1), math.radians(lat2)
        dp = p2 - p1
        dl = math.radians(lon2 - lon1)
        a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return 2 * r * math.asin(math.sqrt(a))


MAGIC = b"MATDIST1"


def guardar_matriz_binaria(matriz, ruta):
    """Guarda la matriz en binario: firma, orden n y n*n doubles little endian.

    En binario los valores se recuperan tal cual. En texto hay que decidir
    cuantos decimales se escriben y ahi ya se pierde precision.
    """
    n = len(matriz)
    with open(ruta, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<I", n))
        for fila in matriz:
            f.write(struct.pack("<%dd" % n, *fila))
    return os.path.getsize(ruta)


def cargar_matriz_binaria(ruta):
    with open(ruta, "rb") as f:
        if f.read(8) != MAGIC:
            raise ValueError("El archivo %s no tiene la firma esperada." % ruta)
        n = struct.unpack("<I", f.read(4))[0]
        matriz = []
        for _ in range(n):
            matriz.append(list(struct.unpack("<%dd" % n, f.read(8 * n))))
    return matriz


def guardar_matriz_texto(matriz, ruta, decimales=2):
    """La misma matriz en texto. Se conserva solo para comparar tamano y precision."""
    with open(ruta, "w", encoding="utf-8") as f:
        for fila in matriz:
            f.write(",".join(("%." + str(decimales) + "f") % v for v in fila) + "\n")
    return os.path.getsize(ruta)


def guardar_json(objeto, ruta):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(objeto, f, indent=2, ensure_ascii=False)


def cargar_json(ruta):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def escribir_csv(filas, campos, ruta):
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=campos)
        escritor.writeheader()
        for fila in filas:
            escritor.writerow({c: fila.get(c, "") for c in campos})
    return ruta


def leer_csv(ruta):
    with open(ruta, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def titulo(texto):
    print()
    print("=" * 74)
    print(texto)
    print("=" * 74)
