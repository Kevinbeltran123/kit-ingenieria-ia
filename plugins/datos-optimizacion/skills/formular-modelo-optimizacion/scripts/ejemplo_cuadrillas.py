# /// script
# requires-python = ">=3.11"
# dependencies = ["ortools>=9.10"]
# ///
"""Ejemplo: asignar cuadrillas a lotes con OR-Tools CP-SAT.

Cada lote lo cosecha una sola cuadrilla, sin pasar su capacidad (kg RFF/día),
minimizando los metros recorridos. Uso:

    uv run ejemplo_cuadrillas.py [instancia.json]

Sin argumento usa la instancia mínima de abajo. La solución se revisa con
verificar_cuadrillas.py, que no comparte código con este modelo.
"""

from __future__ import annotations

import json
import sys

from ortools.sat.python import cp_model

# Instancia mínima: el óptimo es 800 m (A: L1+L2, B: L3); se calcula a mano.
INSTANCIA_MINIMA = {
    "cuadrillas": {"A": {"cap_kg": 5000}, "B": {"cap_kg": 4000}},
    "lotes": {"L1": {"kg": 3000}, "L2": {"kg": 2000}, "L3": {"kg": 2500}},
    "dist_m": {
        "A": {"L1": 100, "L2": 500, "L3": 400},
        "B": {"L1": 600, "L2": 300, "L3": 200},
    },
}


def resolver(instancia: dict, limite_s: float = 10.0) -> dict:
    """Devuelve {"estado": ..., "asignacion": {lote: cuadrilla}, "objetivo_m": int}."""
    cuadrillas = list(instancia["cuadrillas"])
    lotes = list(instancia["lotes"])
    kg = {l: int(instancia["lotes"][l]["kg"]) for l in lotes}
    cap = {c: int(instancia["cuadrillas"][c]["cap_kg"]) for c in cuadrillas}
    dist = {(c, l): int(instancia["dist_m"][c][l]) for c in cuadrillas for l in lotes}

    modelo = cp_model.CpModel()
    x = {(c, l): modelo.new_bool_var(f"x_{c}_{l}") for c in cuadrillas for l in lotes}
    for l in lotes:
        modelo.add_exactly_one(x[c, l] for c in cuadrillas)
    for c in cuadrillas:
        modelo.add(sum(kg[l] * x[c, l] for l in lotes) <= cap[c])
    modelo.minimize(sum(dist[c, l] * x[c, l] for c in cuadrillas for l in lotes))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = limite_s
    estado = solver.solve(modelo)

    if estado not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"estado": solver.status_name(estado), "asignacion": {}, "objetivo_m": None}
    asignacion = {l: c for c in cuadrillas for l in lotes if solver.value(x[c, l])}
    return {
        "estado": solver.status_name(estado),
        "asignacion": asignacion,
        "objetivo_m": int(solver.objective_value),
    }


if __name__ == "__main__":
    instancia = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else INSTANCIA_MINIMA
    print(json.dumps(resolver(instancia), indent=2, ensure_ascii=False))
