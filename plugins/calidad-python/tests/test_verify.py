"""Pruebas de skills/verify/scripts/verify.py con herramientas falsas."""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "skills" / "verify" / "scripts" / "verify.py"


@pytest.fixture
def raiz(tmp_path):
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    return tmp_path


def falsa(raiz: Path, nombre: str, codigo: int, salida: str = "") -> Path:
    registro = raiz / f"{nombre}.args"
    script = raiz / ".venv" / "bin" / nombre
    script.write_text(f'#!/bin/sh\necho "$@" >> "{registro}"\necho "{salida}"\nexit {codigo}\n')
    script.chmod(0o755)
    return registro


def correr(raiz: Path):
    # PATH mínimo para que no encuentre herramientas reales del sistema.
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(raiz)],
        capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"},
    )


def test_sin_herramientas_no_lo_reporta_como_exito(raiz):
    r = correr(raiz)
    assert r.returncode == 0
    assert "Nada que verificar" in r.stdout


def test_todo_ok(raiz):
    falsa(raiz, "ruff", 0)
    falsa(raiz, "pytest", 0)
    (raiz / "tests").mkdir()
    r = correr(raiz)
    assert r.returncode == 0
    assert "3/3 pasos OK" in r.stdout


def test_un_fallo_hace_salir_con_1_y_muestra_la_salida(raiz):
    falsa(raiz, "ruff", 0)
    falsa(raiz, "pytest", 1, "FAILED test_x")
    (raiz / "tests").mkdir()
    r = correr(raiz)
    assert r.returncode == 1
    assert "FALLA pytest" in r.stdout and "FAILED test_x" in r.stdout


def test_pytest_sin_pruebas_no_es_fallo(raiz):
    falsa(raiz, "pytest", 5)
    (raiz / "tests").mkdir()
    assert correr(raiz).returncode == 0


def test_tipos_solo_el_configurado(raiz):
    (raiz / "pyproject.toml").write_text("[tool.mypy]\n")
    ty = falsa(raiz, "ty", 0)
    mypy = falsa(raiz, "mypy", 1, "error: tipo")
    deptry = falsa(raiz, "deptry", 0)
    r = correr(raiz)
    assert r.returncode == 1 and "FALLA mypy" in r.stdout
    assert not ty.exists()
    assert deptry.exists()


def test_orden_de_los_pasos(raiz):
    (raiz / "pyproject.toml").write_text("[tool.ty]\n[tool.importlinter]\n")
    for nombre in ["ruff", "ty", "lint-imports", "pytest", "deptry"]:
        falsa(raiz, nombre, 0)
    (raiz / "tests").mkdir()
    lineas = [l.split()[1] for l in correr(raiz).stdout.splitlines() if l.startswith("OK")]
    assert lineas == ["ruff", "ruff", "ty", "import-linter", "pytest", "deptry"]
