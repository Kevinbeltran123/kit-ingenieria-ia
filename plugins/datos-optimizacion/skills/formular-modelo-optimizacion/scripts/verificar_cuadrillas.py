"""Verificador independiente para la asignación de cuadrillas.

No importa el modelo ni el solver: revisa la solución contra las reglas de
negocio y recalcula el objetivo desde cero. Solo biblioteca estándar.

    python3 verificar_cuadrillas.py instancia.json solucion.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def verificar(instancia: dict, solucion: dict) -> list[str]:
    """Devuelve las violaciones encontradas; lista vacía = factible y objetivo correcto."""
    errores = []
    cuadrillas = instancia["cuadrillas"]
    lotes = instancia["lotes"]
    asignacion = solucion.get("asignacion", {})

    errores.extend(f"El lote {lote} quedó sin cuadrilla." for lote in lotes if lote not in asignacion)
    for lote, cuadrilla in asignacion.items():
        if lote not in lotes:
            errores.append(f"Se asignó un lote que no existe: {lote}.")
        if cuadrilla not in cuadrillas:
            errores.append(f"El lote {lote} tiene una cuadrilla que no existe: {cuadrilla}.")

    for cuadrilla, datos in cuadrillas.items():
        carga = sum(lotes[lote]["kg"] for lote, c in asignacion.items() if c == cuadrilla and lote in lotes)
        if carga > datos["cap_kg"]:
            errores.append(f"La cuadrilla {cuadrilla} recibe {carga} kg y su capacidad es {datos['cap_kg']} kg.")

    if not errores:
        objetivo = sum(instancia["dist_m"][c][lote] for lote, c in asignacion.items())
        if solucion.get("objetivo_m") != objetivo:
            errores.append(
                f"El objetivo reportado ({solucion.get('objetivo_m')} m) no coincide con el recalculado ({objetivo} m)."
            )
    return errores


if __name__ == "__main__":
    instancia = json.loads(Path(sys.argv[1]).read_text())
    solucion = json.loads(Path(sys.argv[2]).read_text())
    errores = verificar(instancia, solucion)
    print("\n".join(errores) if errores else "Solución factible y objetivo correcto.")
    sys.exit(1 if errores else 0)
