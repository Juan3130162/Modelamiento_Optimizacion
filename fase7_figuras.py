"""Graficas, a partir de lo que dejo la fase 6.

  figura1_recorridos_<medicion>.png   el distrito: orden de lista vs optimo
  figura2_escalabilidad.png           tiempo de solucion segun el tamano
  figura3_comparacion.png             distancia total por metodo
  figura4_geodesica_vs_vial.png       las dos mediciones lado a lado
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import comun as c
from fase1_depuracion import cargar_nodos

AZUL = "#2a78d6"      # solucion optima
NARANJA = "#eb6834"   # orden de lista
AQUA = "#1baf7a"      # 2-opt
TINTA = "#0b0b0b"
TINTA2 = "#52514e"
SUPERFICIE = "#fcfcfb"
REJILLA = "#e3e2de"

plt.rcParams.update({
    "figure.facecolor": SUPERFICIE, "axes.facecolor": SUPERFICIE,
    "savefig.facecolor": SUPERFICIE, "font.size": 9,
    "axes.edgecolor": REJILLA, "axes.labelcolor": TINTA,
    "text.color": TINTA, "xtick.color": TINTA2, "ytick.color": TINTA2,
    "axes.spines.top": False, "axes.spines.right": False,
})


def _fondo_vial(ax):
    """Pinta las calles de fondo, si el grafo esta a mano. Se cachea en el atributo."""
    if not os.path.exists(c.ARCHIVO_GRAFO):
        return
    try:
        import osmnx as ox
    except ImportError:
        return
    G = _fondo_vial.grafo if hasattr(_fondo_vial, "grafo") else ox.load_graphml(c.ARCHIVO_GRAFO)
    _fondo_vial.grafo = G
    for u, v, datos in G.edges(data=True):
        if "geometry" in datos:
            xs, ys = datos["geometry"].xy
        else:
            xs = [G.nodes[u]["x"], G.nodes[v]["x"]]
            ys = [G.nodes[u]["y"], G.nodes[v]["y"]]
        ax.plot(xs, ys, color="#d7d6d2", linewidth=0.7, zorder=1, solid_capstyle="round")


def _trazar_ruta(ax, nodos, ruta, color, titulo, distancia):
    _fondo_vial(ax)
    xs = [nodos[i]["lon"] for i in ruta]
    ys = [nodos[i]["lat"] for i in ruta]
    ax.plot(xs, ys, "-", color=color, linewidth=1.6, zorder=2, solid_capstyle="round")
    ax.scatter([n["lon"] for n in nodos[1:]], [n["lat"] for n in nodos[1:]],
               s=26, color=color, edgecolor=SUPERFICIE, linewidth=1.2, zorder=3)
    ax.scatter([nodos[0]["lon"]], [nodos[0]["lat"]], s=130, marker="*",
               color=TINTA, edgecolor=SUPERFICIE, linewidth=1.2, zorder=4)
    ax.annotate("Estacion\n(inicio y cierre)", (nodos[0]["lon"], nodos[0]["lat"]),
                textcoords="offset points", xytext=(8, -4), fontsize=7.5, color=TINTA2)
    ax.set_title("%s\n%.2f km" % (titulo, distancia / 1000.0), fontsize=10, loc="left")
    ax.set_xlabel("Longitud"); ax.set_ylabel("Latitud")
    ax.ticklabel_format(useOffset=False, style="plain")
    ax.xaxis.set_major_formatter(lambda v, _: "%.3f" % v)
    ax.yaxis.set_major_formatter(lambda v, _: "%.3f" % v)
    ax.tick_params(labelsize=7.5)
    ax.grid(True, color=REJILLA, linewidth=0.6)
    ax.set_aspect(1 / 0.845)          # para que no salga achatado por la latitud
    mx = (max(xs) - min(xs)) * 0.08 + 0.0008
    my = (max(ys) - min(ys)) * 0.08 + 0.0008
    ax.set_xlim(min(xs) - mx, max(xs) + mx)
    ax.set_ylim(min(ys) - my, max(ys) + my)


def figura_recorridos(instancia="I37", medicion="geodesica"):
    res = c.cargar_json(c.ruta_salida("resultados.json"))
    if instancia not in res or medicion not in res[instancia]:
        return None
    bloque = res[instancia][medicion]
    nodos, _ = cargar_nodos(instancia)
    cst = c.cargar_matriz_binaria(c.ruta_salida(
        ("matriz_%s_" % ("geodesica" if medicion == "geodesica" else "vial")) + instancia + ".bin"))

    lista = bloque["heuristicas"][0]
    mejor = bloque.get("exacto") or bloque["heuristicas"][2]

    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.6))
    _trazar_ruta(axes[0], nodos, lista["secuencia"], NARANJA,
                 "a) Orden de la lista (sin optimizar)", lista["distancia_m"])
    _trazar_ruta(axes[1], nodos, mejor["secuencia"], AZUL,
                 "b) Recorrido optimo (modelo MTZ)", mejor["distancia_m"])
    ahorro = 100 * (lista["distancia_m"] - mejor["distancia_m"]) / lista["distancia_m"]
    fig.suptitle("Recorrido de visita en %s - instancia %s (%d viviendas), "
                 "medicion %s. Ahorro: %.1f %%"
                 % (c.DISTRITO, instancia, len(nodos) - 1, medicion, ahorro),
                 fontsize=10.5, x=0.02, ha="left")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    ruta = c.ruta_salida("figura1_recorridos_%s.png" % medicion)
    fig.savefig(ruta, dpi=220); plt.close(fig)
    return ruta


def figura_escalabilidad():
    res = c.cargar_json(c.ruta_salida("resultados.json"))
    series = {}
    for medicion, color, etiqueta in (("geodesica", AZUL, "Medicion geodesica"),
                                      ("vial", NARANJA, "Medicion sobre la red vial")):
        puntos = []
        for inst, bloque in res.items():
            ex = bloque.get(medicion, {}).get("exacto")
            if ex and ex["segundos_solucion"] is not None:
                puntos.append((bloque["nodos"], ex["segundos_solucion"], inst, ex["estado"]))
        puntos.sort()
        if puntos:
            series[medicion] = (puntos, color, etiqueta)
    if not series:
        return None

    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    for medicion, (puntos, color, etiqueta) in series.items():
        ax.plot([p[0] for p in puntos], [p[1] for p in puntos], "-o",
                color=color, linewidth=2, markersize=8, label=etiqueta,
                markeredgecolor=SUPERFICIE, markeredgewidth=1.2)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    # las etiquetas de los puntos se ponen sobre una sola serie, si no se encima todo
    puntos = series["geodesica"][0] if "geodesica" in series else list(series.values())[0][0]
    ax.set_yscale("log")
    ax.set_xlabel("Nodos del modelo (viviendas + deposito)")
    ax.set_ylabel("Tiempo de solucion (s, escala logaritmica)")
    ax.set_title("Costo computacional de la formulacion compacta MTZ", loc="left", fontsize=10.5)
    ax.grid(True, which="both", color=REJILLA, linewidth=0.6)
    for x, y, inst, estado in puntos:
        etiqueta = "%s\n%.1f s" % (inst, y) if y >= 1 else "%s\n%.2f s" % (inst, y)
        if estado != "optimal":
            etiqueta += "\n(limite)"
        ax.annotate(etiqueta, (x, y), textcoords="offset points", xytext=(6, -14),
                    fontsize=7.5, color=TINTA2)
    fig.tight_layout()
    ruta = c.ruta_salida("figura2_escalabilidad.png")
    fig.savefig(ruta, dpi=220); plt.close(fig)
    return ruta


def figura_comparacion(medicion="geodesica"):
    res = c.cargar_json(c.ruta_salida("resultados.json"))
    inst = [i for i in ["I10", "I20", "I37", "I56"] if medicion in res.get(i, {})]
    lista, opt2, optimo = [], [], []
    for i in inst:
        b = res[i][medicion]
        lista.append(b["heuristicas"][0]["distancia_m"] / 1000)
        opt2.append(b["heuristicas"][2]["distancia_m"] / 1000)
        ex = b.get("exacto")
        optimo.append((ex["distancia_m"] / 1000) if ex and ex["distancia_m"] else 0)

    x = range(len(inst)); ancho = 0.26
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    b1 = ax.bar([v - ancho for v in x], lista, ancho * 0.92, color=NARANJA,
                label="Orden de la lista")
    b2 = ax.bar(list(x), opt2, ancho * 0.92, color=AQUA, label="Vecino mas cercano + 2-opt")
    b3 = ax.bar([v + ancho for v in x], optimo, ancho * 0.92, color=AZUL, label="Optimo (MTZ)")
    for barras in (b1, b2, b3):
        ax.bar_label(barras, fmt="%.1f", fontsize=7.5, color=TINTA2, padding=2)
    ax.set_xticks(list(x))
    ax.set_xticklabels(["%s\n(%d viviendas)" % (i, res[i]["viviendas"]) for i in inst])
    ax.set_ylabel("Distancia total del recorrido (km)")
    ax.set_title("Distancia recorrida segun el metodo - medicion %s" % medicion,
                 loc="left", fontsize=10.5)
    ax.grid(True, axis="y", color=REJILLA, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=8.5)
    fig.tight_layout()
    ruta = c.ruta_salida("figura3_comparacion.png")
    fig.savefig(ruta, dpi=220); plt.close(fig)
    return ruta


def figura_geodesica_vs_vial():
    res = c.cargar_json(c.ruta_salida("resultados.json"))
    inst = [i for i in ["I10", "I20", "I37", "I56", "I231"]
            if "vial" in res.get(i, {}) and "geodesica" in res.get(i, {})]
    if not inst:
        return None
    geo, vial = [], []
    for i in inst:
        for destino, medicion in ((geo, "geodesica"), (vial, "vial")):
            b = res[i][medicion]
            ex = b.get("exacto")
            # si no hay optimo se usa lo mejor que dio 2-opt
            destino.append(((ex["distancia_m"] if ex and ex["distancia_m"]
                             else b["heuristicas"][2]["distancia_m"]) / 1000))

    x = range(len(inst)); ancho = 0.34
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    b1 = ax.bar([v - ancho / 2 for v in x], geo, ancho * 0.92, color=AZUL,
                label="Medicion geodesica (linea recta)")
    b2 = ax.bar([v + ancho / 2 for v in x], vial, ancho * 0.92, color=NARANJA,
                label="Medicion sobre la red vial")
    ax.bar_label(b1, fmt="%.1f", fontsize=7.5, color=TINTA2, padding=2)
    ax.bar_label(b2, fmt="%.1f", fontsize=7.5, color=TINTA2, padding=2)
    for k, i in enumerate(inst):
        if geo[k] > 0:
            ax.annotate("x%.2f" % (vial[k] / geo[k]), (k, max(geo[k], vial[k])),
                        textcoords="offset points", xytext=(0, 16),
                        ha="center", fontsize=8, color=TINTA)
    ax.set_xticks(list(x))
    ax.set_xticklabels(["%s\n(%d viviendas)" % (i, res[i]["viviendas"]) for i in inst])
    ax.set_ylabel("Distancia total del recorrido (km)")
    ax.set_title("Cuanto subestima la linea recta al desplazamiento real",
                 loc="left", fontsize=10.5)
    ax.grid(True, axis="y", color=REJILLA, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=8.5)
    fig.tight_layout()
    ruta = c.ruta_salida("figura4_geodesica_vs_vial.png")
    fig.savefig(ruta, dpi=220); plt.close(fig)
    return ruta


def ejecutar():
    c.titulo("FASE 7. Figuras")
    for f in (figura_recorridos("I37", "geodesica"),
              figura_escalabilidad(),
              figura_comparacion("geodesica"),
              figura_recorridos("I37", "vial"),
              figura_geodesica_vs_vial()):
        if f:
            print("  " + os.path.basename(f))


if __name__ == "__main__":
    ejecutar()
