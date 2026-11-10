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
from pathlib import Path

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
    kg = {lote: int(instancia["lotes"][lote]["kg"]) for lote in lotes}
    cap = {c: int(instancia["cuadrillas"][c]["cap_kg"]) for c in cuadrillas}
    dist = {(c, lote): int(instancia["dist_m"][c][lote]) for c in cuadrillas for lote in lotes}

    modelo = cp_model.CpModel()
    x = {(c, lote): modelo.new_bool_var(f"x_{c}_{lote}") for c in cuadrillas for lote in lotes}
    for lote in lotes:
        modelo.add_exactly_one(x[c, lote] for c in cuadrillas)
    for c in cuadrillas:
        modelo.add(sum(kg[lote] * x[c, lote] for lote in lotes) <= cap[c])
    modelo.minimize(sum(dist[c, lote] * x[c, lote] for c in cuadrillas for lote in lotes))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = limite_s
    estado = solver.solve(modelo)

    if estado not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"estado": solver.status_name(estado), "asignacion": {}, "objetivo_m": None}
    asignacion = {lote: c for c in cuadrillas for lote in lotes if solver.value(x[c, lote])}
    return {
        "estado": solver.status_name(estado),
        "asignacion": asignacion,
        "objetivo_m": int(solver.objective_value),
    }


if __name__ == "__main__":
    instancia = json.loads(Path(sys.argv[1]).read_text()) if len(sys.argv) > 1 else INSTANCIA_MINIMA
    print(json.dumps(resolver(instancia), indent=2, ensure_ascii=False))
