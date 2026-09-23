"""Modelo exacto del agente viajero (formulacion MTZ) en Pyomo.

    min  Z = SUM_i SUM_{j!=i} c_ij x_ij
    s.a. SUM_{j!=i} x_ij = 1            para todo i      (un sucesor por nodo)
         SUM_{i!=j} x_ij = 1            para todo j      (un predecesor por nodo)
         u_i - u_j + n x_ij <= n - 1    para 1 <= i != j <= n-1
         1 <= u_i <= n - 1,  x_ij en {0,1}

El nodo 0 es el deposito. Las dos primeras familias son las del problema de
asignacion; la tercera es la que evita que la solucion se parta en varios
circuitos sueltos, y de paso la que vuelve el problema NP-dificil.
"""

import itertools
import time

import pyomo.environ as pyo

LIMITE_TIEMPO = 300          # segundos por instancia
BRECHA_ACEPTABLE = 0.0       # se exige optimalidad demostrada


def construir_modelo(cst):
    n = len(cst)
    N = list(range(n))
    A = [(i, j) for i in N for j in N if i != j]

    m = pyo.ConcreteModel(name="TSP-MTZ")
    m.N = pyo.Set(initialize=N)
    m.A = pyo.Set(initialize=A, dimen=2)
    m.c = pyo.Param(m.A, initialize={(i, j): cst[i][j] for i, j in A})
    m.x = pyo.Var(m.A, domain=pyo.Binary)
    m.u = pyo.Var(N[1:], bounds=(1, n - 1))          # posicion en la secuencia

    m.objetivo = pyo.Objective(
        expr=sum(m.c[i, j] * m.x[i, j] for i, j in A), sense=pyo.minimize)

    m.sucesor = pyo.Constraint(
        m.N, rule=lambda m, i: sum(m.x[i, j] for j in m.N if j != i) == 1)
    m.predecesor = pyo.Constraint(
        m.N, rule=lambda m, j: sum(m.x[i, j] for i in m.N if i != j) == 1)
    m.mtz = pyo.Constraint(
        [(i, j) for i, j in A if i != 0 and j != 0],
        rule=lambda m, i, j: m.u[i] - m.u[j] + n * m.x[i, j] <= n - 1)
    return m


def _secuencia(m, n):
    """Arma la ruta siguiendo los arcos que quedaron en 1."""
    sig = {}
    for i in range(n):
        for j in range(n):
            if i != j and pyo.value(m.x[i, j]) > 0.5:
                sig[i] = j
    ruta, actual = [0], 0
    for _ in range(n):
        actual = sig[actual]
        ruta.append(actual)
        if actual == 0:
            break
    return ruta


def resolver(cst, limite_tiempo=LIMITE_TIEMPO, brecha=BRECHA_ACEPTABLE, mostrar=False):
    """Resuelve y devuelve la secuencia, la distancia y la brecha que quedo."""
    n = len(cst)
    t0 = time.perf_counter()
    m = construir_modelo(cst)
    t_constr = time.perf_counter() - t0

    from pyomo.contrib.appsi.solvers.highs import Highs
    solucionador = Highs()
    solucionador.config.time_limit = limite_tiempo
    solucionador.config.mip_gap = brecha
    solucionador.config.stream_solver = mostrar
    solucionador.config.load_solution = False

    t0 = time.perf_counter()
    res = solucionador.solve(m)
    t_sol = time.perf_counter() - t0

    estado = str(res.termination_condition).split(".")[-1]
    salida = {
        "nodos": n,
        "variables_binarias": n * (n - 1),
        "restricciones_mtz": (n - 1) * (n - 2),
        "segundos_construccion": round(t_constr, 3),
        "segundos_solucion": round(t_sol, 3),
        "estado": estado,
        "secuencia": None,
        "distancia_m": None,
        "cota_inferior_m": None,
        "brecha_relativa": None,
    }
    if res.best_feasible_objective is not None:
        res.solution_loader.load_vars()
        salida["secuencia"] = _secuencia(m, n)
        salida["distancia_m"] = float(res.best_feasible_objective)
        if res.best_objective_bound is not None:
            cota = float(res.best_objective_bound)
            salida["cota_inferior_m"] = cota
            if salida["distancia_m"] > 0:
                salida["brecha_relativa"] = max(
                    0.0, (salida["distancia_m"] - cota) / salida["distancia_m"])
    return salida


def enumerar(cst):
    """Fuerza bruta: prueba las (n-1)! secuencias posibles.

    Es la forma de comprobar que el modelo esta bien escrito. Solo sirve hasta
    nueve o diez nodos; con quince serian mas de 87 mil millones de rutas.
    """
    n = len(cst)
    mejor, mejor_ruta = float("inf"), None
    t0 = time.perf_counter()
    for perm in itertools.permutations(range(1, n)):
        ruta = (0,) + perm + (0,)
        d = sum(cst[ruta[k]][ruta[k + 1]] for k in range(n))
        if d < mejor:
            mejor, mejor_ruta = d, list(ruta)
    return {"distancia_m": mejor, "secuencia": mejor_ruta,
            "segundos": round(time.perf_counter() - t0, 3),
            "secuencias_evaluadas": _factorial(n - 1)}


def _factorial(k):
    r = 1
    for i in range(2, k + 1):
        r *= i
    return r


def longitud(cst, ruta):
    return sum(cst[ruta[k]][ruta[k + 1]] for k in range(len(ruta) - 1))
