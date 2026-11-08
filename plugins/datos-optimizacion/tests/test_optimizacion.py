"""Pruebas del ejemplo de asignación de cuadrillas y de su verificador independiente."""

from __future__ import annotations

import itertools
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "formular-modelo-optimizacion" / "scripts"))

from verificar_cuadrillas import verificar  # noqa: E402

MINIMA = {
    "cuadrillas": {"A": {"cap_kg": 5000}, "B": {"cap_kg": 4000}},
    "lotes": {"L1": {"kg": 3000}, "L2": {"kg": 2000}, "L3": {"kg": 2500}},
    "dist_m": {
        "A": {"L1": 100, "L2": 500, "L3": 400},
        "B": {"L1": 600, "L2": 300, "L3": 200},
    },
}

INFACTIBLE = {
    "cuadrillas": {"A": {"cap_kg": 1000}},
    "lotes": {"L1": {"kg": 3000}},
    "dist_m": {"A": {"L1": 100}},
}


def fuerza_bruta(instancia: dict) -> int | None:
    """Mejor objetivo enumerando todas las asignaciones; None si ninguna es factible."""
    lotes = list(instancia["lotes"])
    mejor = None
    for combo in itertools.product(instancia["cuadrillas"], repeat=len(lotes)):
        asignacion = dict(zip(lotes, combo))
        objetivo = sum(instancia["dist_m"][c][l] for l, c in asignacion.items())
        if not verificar(instancia, {"asignacion": asignacion, "objetivo_m": objetivo}):
            mejor = objetivo if mejor is None else min(mejor, objetivo)
    return mejor


def instancia_aleatoria(semilla: int) -> dict:
    rng = random.Random(semilla)
    cuadrillas = {f"C{i}": {"cap_kg": rng.randint(3000, 8000)} for i in range(3)}
    lotes = {f"L{j}": {"kg": rng.randint(500, 4000)} for j in range(5)}
    dist = {c: {l: rng.randint(50, 2000) for l in lotes} for c in cuadrillas}
    return {"cuadrillas": cuadrillas, "lotes": lotes, "dist_m": dist}


# --- Verificador (siempre corre, sin solver) ---

def test_verificador_acepta_el_optimo_calculado_a_mano():
    sol = {"asignacion": {"L1": "A", "L2": "A", "L3": "B"}, "objetivo_m": 800}
    assert verificar(MINIMA, sol) == []


def test_verificador_detecta_capacidad_excedida():
    sol = {"asignacion": {"L1": "B", "L2": "B", "L3": "A"}, "objetivo_m": 1300}
    errores = verificar(MINIMA, sol)
    assert any("capacidad" in e for e in errores)


def test_verificador_detecta_lote_sin_cuadrilla():
    sol = {"asignacion": {"L1": "A", "L2": "A"}, "objetivo_m": 600}
    assert any("sin cuadrilla" in e for e in verificar(MINIMA, sol))


def test_verificador_detecta_objetivo_mal_reportado():
    sol = {"asignacion": {"L1": "A", "L2": "A", "L3": "B"}, "objetivo_m": 700}
    assert any("no coincide" in e for e in verificar(MINIMA, sol))


def test_fuerza_bruta_confirma_el_optimo_a_mano():
    assert fuerza_bruta(MINIMA) == 800
    assert fuerza_bruta(INFACTIBLE) is None


# --- Modelo (solo si OR-Tools está instalado) ---

@pytest.fixture
def resolver():
    pytest.importorskip("ortools")
    from ejemplo_cuadrillas import resolver

    return resolver


def test_modelo_reproduce_el_optimo_conocido(resolver):
    sol = resolver(MINIMA)
    assert sol["estado"] == "OPTIMAL"
    assert sol["objetivo_m"] == 800
    assert verificar(MINIMA, sol) == []


def test_modelo_reporta_infactible(resolver):
    sol = resolver(INFACTIBLE)
    assert sol["estado"] == "INFEASIBLE"
    assert sol["asignacion"] == {}


def test_modelo_sin_lotes_es_trivial(resolver):
    vacia = {"cuadrillas": {"A": {"cap_kg": 1000}}, "lotes": {}, "dist_m": {"A": {}}}
    sol = resolver(vacia)
    assert sol["estado"] == "OPTIMAL" and sol["objetivo_m"] == 0


def test_capacidad_exacta_es_factible(resolver):
    justa = {"cuadrillas": {"A": {"cap_kg": 3000}}, "lotes": {"L1": {"kg": 3000}}, "dist_m": {"A": {"L1": 10}}}
    assert resolver(justa)["objetivo_m"] == 10


@pytest.mark.parametrize("semilla", range(10))
def test_modelo_igual_a_fuerza_bruta(resolver, semilla):
    instancia = instancia_aleatoria(semilla)
    sol = resolver(instancia)
    esperado = fuerza_bruta(instancia)
    if esperado is None:
        assert sol["estado"] == "INFEASIBLE"
    else:
        assert sol["objetivo_m"] == esperado
        assert verificar(instancia, sol) == []
