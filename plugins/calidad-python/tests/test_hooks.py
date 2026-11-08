"""Pruebas de los hooks con herramientas falsas en .venv/bin del proyecto de prueba."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parent.parent / "hooks"


@pytest.fixture
def proyecto(tmp_path):
    raiz = tmp_path / "repo"
    (raiz / ".venv" / "bin").mkdir(parents=True)
    (raiz / "app.py").write_text("x = 1\n")
    temporal = tmp_path / "tmp"
    temporal.mkdir()
    return raiz, temporal


def herramienta_falsa(raiz: Path, nombre: str, codigo: int, salida: str = "") -> Path:
    """Crea .venv/bin/<nombre> que guarda sus argumentos, imprime `salida` y sale con `codigo`."""
    registro = raiz / f"{nombre}.args"
    script = raiz / ".venv" / "bin" / nombre
    script.write_text(f'#!/bin/sh\necho "$@" >> "{registro}"\necho "{salida}"\nexit {codigo}\n')
    script.chmod(0o755)
    return registro


def correr(hook: str, datos: dict, raiz: Path, temporal: Path, path_extra: str = ""):
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(raiz), "TMPDIR": str(temporal)}
    if path_extra:
        env["PATH"] = path_extra + os.pathsep + env["PATH"]
    return subprocess.run(
        [sys.executable, "-I", str(HOOKS / hook)],
        input=json.dumps(datos), capture_output=True, text=True, env=env,
    )


def marca(temporal: Path, sesion: str) -> Path:
    return temporal / "claude-calidad-python" / sesion


def editar(raiz, temporal, sesion="s1"):
    datos = {"session_id": sesion, "tool_input": {"file_path": str(raiz / "app.py")}}
    return correr("ruff_al_editar.py", datos, raiz, temporal)


# --- ruff_al_editar.py ---

def test_ignora_archivos_que_no_son_python(proyecto):
    raiz, temporal = proyecto
    (raiz / "notas.md").write_text("hola")
    r = correr("ruff_al_editar.py", {"session_id": "s1", "tool_input": {"file_path": str(raiz / "notas.md")}}, raiz, temporal)
    assert r.returncode == 0
    assert not marca(temporal, "s1").exists()


def test_errores_de_ruff_se_devuelven_a_claude(proyecto):
    raiz, temporal = proyecto
    herramienta_falsa(raiz, "ruff", 1, "app.py:1:1: F401 unused import")
    r = editar(raiz, temporal)
    assert r.returncode == 2
    assert "F401" in r.stderr
    assert str(raiz / "app.py") in marca(temporal, "s1").read_text()


def test_ruff_limpio_pasa(proyecto):
    raiz, temporal = proyecto
    registro = herramienta_falsa(raiz, "ruff", 0)
    r = editar(raiz, temporal)
    assert r.returncode == 0
    llamadas = registro.read_text()
    assert "check --fix" in llamadas and "format" in llamadas


# --- revisar_al_terminar.py ---

def test_sin_ediciones_de_python_no_revisa(proyecto):
    raiz, temporal = proyecto
    registro = herramienta_falsa(raiz, "pytest", 1)
    (raiz / "tests").mkdir()
    r = correr("revisar_al_terminar.py", {"session_id": "s1"}, raiz, temporal)
    assert r.returncode == 0
    assert not registro.exists()


def test_pruebas_que_fallan_bloquean_el_final(proyecto):
    raiz, temporal = proyecto
    herramienta_falsa(raiz, "ruff", 0)
    herramienta_falsa(raiz, "pytest", 1, "FAILED tests/test_app.py::test_suma")
    (raiz / "tests").mkdir()
    editar(raiz, temporal)
    r = correr("revisar_al_terminar.py", {"session_id": "s1"}, raiz, temporal)
    assert r.returncode == 2
    assert "pytest falló" in r.stderr and "test_suma" in r.stderr
    assert marca(temporal, "s1").exists()


def test_un_solo_reintento(proyecto):
    raiz, temporal = proyecto
    herramienta_falsa(raiz, "ruff", 0)
    herramienta_falsa(raiz, "pytest", 1)
    (raiz / "tests").mkdir()
    editar(raiz, temporal)
    r = correr("revisar_al_terminar.py", {"session_id": "s1", "stop_hook_active": True}, raiz, temporal)
    assert r.returncode == 0
    assert not marca(temporal, "s1").exists()


def test_sin_pruebas_recolectadas_no_es_fallo(proyecto):
    raiz, temporal = proyecto
    herramienta_falsa(raiz, "ruff", 0)
    herramienta_falsa(raiz, "pytest", 5)
    (raiz / "tests").mkdir()
    editar(raiz, temporal)
    r = correr("revisar_al_terminar.py", {"session_id": "s1"}, raiz, temporal)
    assert r.returncode == 0
    assert not marca(temporal, "s1").exists()


def test_usa_el_verificador_de_tipos_configurado_sobre_los_archivos_editados(proyecto):
    raiz, temporal = proyecto
    (raiz / "pyproject.toml").write_text("[tool.mypy]\nstrict = true\n")
    herramienta_falsa(raiz, "ruff", 0)
    ty = herramienta_falsa(raiz, "ty", 0)
    mypy = herramienta_falsa(raiz, "mypy", 1, "app.py:1: error: tipo incorrecto")
    editar(raiz, temporal)
    r = correr("revisar_al_terminar.py", {"session_id": "s1"}, raiz, temporal)
    assert r.returncode == 2
    assert "mypy falló" in r.stderr
    assert str(raiz / "app.py") in mypy.read_text()
    assert not ty.exists()


def test_import_linter_solo_si_esta_configurado(proyecto):
    raiz, temporal = proyecto
    herramienta_falsa(raiz, "ruff", 0)
    lint = herramienta_falsa(raiz, "lint-imports", 1, "Contrato roto")
    editar(raiz, temporal)
    assert correr("revisar_al_terminar.py", {"session_id": "s1"}, raiz, temporal).returncode == 0
    assert not lint.exists()

    (raiz / "pyproject.toml").write_text("[tool.importlinter]\nroot_package = 'app'\n")
    editar(raiz, temporal, sesion="s2")
    r = correr("revisar_al_terminar.py", {"session_id": "s2"}, raiz, temporal)
    assert r.returncode == 2 and "import-linter falló" in r.stderr


# --- notificar.py ---

def test_notificacion_pasa_el_texto_como_argumento(proyecto, tmp_path):
    raiz, temporal = proyecto
    bin_falso = tmp_path / "bin"
    bin_falso.mkdir()
    registro = tmp_path / "osascript.args"
    script = bin_falso / "osascript"
    script.write_text(f'#!/bin/sh\nfor a in "$@"; do echo "$a" >> "{registro}"; done\n')
    script.chmod(0o755)
    datos = {"message": 'Hola" & do shell script "rm', "title": "Permiso"}
    r = correr("notificar.py", datos, raiz, temporal, path_extra=str(bin_falso))
    assert r.returncode == 0
    if sys.platform == "darwin":
        lineas = registro.read_text().splitlines()
        assert lineas[-2:] == ['Hola" & do shell script "rm', "Permiso"]
