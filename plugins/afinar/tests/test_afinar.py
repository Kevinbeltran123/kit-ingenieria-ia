"""afinar: el revisor encuentra lo que falta en un pedido y el hook solo avisa cuando hace falta."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "skills" / "afinar" / "scripts"))

from revisar import es_tarea, revisar

AVISO = PLUGIN / "hooks" / "aviso.py"


def claves(texto):
    return {h["clave"] for h in revisar(texto)["hallazgos"]}


@pytest.mark.parametrize(
    ("texto", "tarea"),
    [
        ("agrega la matriz de confusión al informe", True),
        ("Fix the flaky test in tests/test_io.py", True),
        ("¿cómo funciona el índice de corridas?", False),
        ("/afinar agrega algo", False),
        ("gracias, se ve bien", False),
    ],
)
def test_es_tarea(texto, tarea):
    assert es_tarea(texto) is tarea


def test_pedido_suelto_tiene_todos_los_huecos():
    assert claves("mejora el informe de las corridas para que se vea mejor y sea más útil para el equipo") >= {
        "comprobacion", "limites", "referencias", "vago",
    }  # fmt: skip


def test_pedido_afinado_queda_completo():
    texto = (
        "Meta: el informe de cada corrida muestra la matriz de confusión.\n"
        "Comprobación: `just informe runs/e004` genera la figura → uv run pytest -q pasa.\n"
        "Límites: Sí: src/palma/informe.py. No toques eval/ ni los datos.\n"
        "Agrega la figura con matplotlib."
    )
    r = revisar(texto)
    assert r["completo"], r["hallazgos"]


def test_detecta_riesgos():
    assert "riesgo" in claves("haz push a main y borra la rama vieja cuando termines la migración")


def correr_aviso(prompt, **env):
    return subprocess.run(
        [sys.executable, "-I", str(AVISO)], input=json.dumps({"prompt": prompt}), capture_output=True, text=True,
        env={**os.environ, **env}, timeout=10, check=False,
    )  # fmt: skip


def test_aviso_cuando_falta_la_comprobacion():
    r = correr_aviso("agrega la matriz de confusión al informe de cada corrida del clasificador")
    assert r.returncode == 0
    salida = json.loads(r.stdout)["hookSpecificOutput"]
    assert salida["hookEventName"] == "UserPromptSubmit"
    assert "cómo se comprueba" in salida["additionalContext"]


def test_aviso_de_riesgo_aunque_tenga_comprobacion():
    r = correr_aviso("borra las ramas viejas de flota y haz push; comprobación: git branch -r ya no las muestra")
    contexto = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "Confirma" in contexto
    assert "cómo se comprueba" not in contexto


@pytest.mark.parametrize(
    "prompt",
    [
        "¿qué hace palma.vivo y por qué usa caffeinate en las corridas largas?",
        "arregla esto",
        "/afinar agrega la matriz de confusión al informe de cada corrida",
        "agrega la matriz al informe; comprobación: just informe runs/e004 → aparece la figura y pytest pasa",
    ],
)
def test_sin_aviso_cuando_no_hace_falta(prompt):
    r = correr_aviso(prompt)
    assert r.returncode == 0
    assert r.stdout == ""


def test_se_apaga_y_falla_abierto():
    assert correr_aviso("agrega la matriz de confusión al informe de cada corrida", AFINAR_AVISO="0").stdout == ""
    r = subprocess.run(
        [sys.executable, "-I", str(AVISO)], input="no es json", capture_output=True, text=True, check=False
    )
    assert r.returncode == 0
    assert r.stdout == ""
