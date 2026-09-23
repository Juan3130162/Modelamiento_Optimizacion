"""Corre todo el flujo de punta a punta.

    python main.py                 todo
    python main.py --sin-modelo    solo depuracion, matrices y figuras

Requisitos:
    pip install -r requirements.txt

La fase 3 necesita bertram_red_vial.graphml; se baja una sola vez con
descargar_red_vial.py.
"""

import sys

import comun as c
import fase1_depuracion
import fase2_matriz_geodesica
import fase3_matriz_vial
import fase6_comparacion
import fase7_figuras
import preparar_app


def main():
    completo = "--sin-modelo" not in sys.argv

    fase1_depuracion.construir_instancias()
    fase2_matriz_geodesica.ejecutar()
    fase3_matriz_vial.ejecutar()

    if completo:
        fase6_comparacion.ejecutar()
    else:
        print("\n(Se omite la solucion de los modelos por peticion del usuario.)")

    fase7_figuras.ejecutar()
    c.titulo("Preparacion de los datos de la aplicacion web")
    preparar_app.ejecutar()

    c.titulo("Proceso terminado")
    print("Todas las salidas quedaron en la carpeta 'salidas'.")


if __name__ == "__main__":
    main()
