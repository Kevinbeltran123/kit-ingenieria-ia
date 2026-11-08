"""Pruebas de los scripts de python-ingenieria con herramientas falsas."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SKILLS = Path(__file__).resolve().parent.parent / "skills"
DEUDA = SKILLS / "deuda-tecnica" / "scripts" / "deuda.py"
MUTANTES = SKILLS / "calidad-pruebas" / "scripts" / "mutantes_del_diff.py"
SUMINISTRO = SKILLS / "cadena-suministro-python" / "scripts" / "suministro.py"
PATH_MINIMO = {"PATH": "/usr/bin:/bin"}


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


def correr(script: Path, *args, cwd=None):
    return subprocess.run(
        [sys.executable, "-I", str(script), *map(str, args)],
        capture_output=True, text=True, env=PATH_MINIMO, cwd=cwd,
    )


# --- deuda.py ---

def test_deuda_informa_hallazgos_y_faltantes(raiz):
    (raiz / "src").mkdir()
    vulture = falsa(raiz, "vulture", 3, "src/app.py:3: unused function 'vieja' (60% confidence)")
    falsa(raiz, "deptry", 0)
    r = correr(DEUDA, raiz)
    assert r.returncode == 0
    assert "Código muerto (vulture)" in r.stdout and "unused function 'vieja'" in r.stdout
    assert "Dependencias (deptry) — sin hallazgos" in r.stdout
    assert "`complexipy`" in r.stdout and "`jscpd`" in r.stdout  # no instalados
    assert vulture.read_text().startswith("src ")  # usa src/ si existe


def test_vulture_sin_config_muestra_funciones_y_clases(raiz):
    """vulture da 60 % de confianza a funciones, clases y variables: con 80 nunca salían."""
    vulture = falsa(raiz, "vulture", 0)
    correr(DEUDA, raiz)
    assert "--min-confidence 60" in vulture.read_text()


def test_vulture_respeta_la_config_del_repo(raiz):
    """Pasar rutas o umbral por línea de comandos reemplaza [tool.vulture], incluida la lista blanca."""
    (raiz / "pyproject.toml").write_text('[tool.vulture]\npaths = ["src", "vulture_whitelist.py"]\nmin_confidence = 60\n')
    vulture = falsa(raiz, "vulture", 0)
    correr(DEUDA, raiz)
    assert vulture.read_text().strip() == ""


def test_herramienta_que_pasa_aunque_imprima_algo_queda_sin_hallazgos(raiz):
    falsa(raiz, "deptry", 0, "Success! No dependency issues found.")
    r = correr(DEUDA, raiz)
    assert "Dependencias (deptry) — sin hallazgos" in r.stdout


def test_deuda_escribe_archivo(raiz):
    falsa(raiz, "deptry", 0)
    salida = raiz / "informe.md"
    r = correr(DEUDA, raiz, "--salida", salida)
    assert r.returncode == 0
    assert salida.read_text().startswith("# Informe de deuda técnica")


# --- mutantes_del_diff.py ---

def cargar(script: Path):
    spec = importlib.util.spec_from_file_location("modulo", script)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.mark.parametrize(("ruta", "esperado"), [
    ("src/app/domain/lote.py", "app.domain.lote.*"),
    ("app/servicio.py", "app.servicio.*"),
    ("src/app/__init__.py", "app.x*"),  # solo las funciones del __init__, no todo el paquete
    ("tests/test_lote.py", None),
    ("src/app/test_algo.py", None),
    ("conftest.py", None),
    ("README.md", None),
])
def test_a_patron(ruta, esperado):
    assert cargar(MUTANTES).a_patron(ruta) == esperado


def test_mutantes_desde_git(tmp_path):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    (tmp_path / "src" / "app").mkdir(parents=True)
    (tmp_path / "src" / "app" / "viejo.py").write_text("x = 1\n")
    git("add", ".")
    git("commit", "-qm", "base")
    git("checkout", "-qb", "rama")
    (tmp_path / "src" / "app" / "nuevo.py").write_text("y = 2\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_nuevo.py").write_text("")
    r = correr(MUTANTES, "--base", "main", cwd=tmp_path)
    assert r.returncode == 0
    assert r.stdout.split() == ["app.nuevo.*"]


def test_base_inexistente_es_error_y_no_lista_vacia(tmp_path):
    """Sin la rama base, la lista vacía haría que mutmut mutara todo el repo."""
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q", "-b", "trunk")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    (tmp_path / "x.py").write_text("x = 1\n")
    git("add", ".")
    git("commit", "-qm", "base")
    r = correr(MUTANTES, "--base", "origin/main", cwd=tmp_path)
    assert r.returncode == 2
    assert r.stdout == ""
    assert "origin/main" in r.stderr


def test_mutantes_sin_cambios_sale_con_1(tmp_path):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    (tmp_path / "x.py").write_text("x = 1\n")
    git("add", ".")
    git("commit", "-qm", "base")
    r = correr(MUTANTES, "--base", "main", cwd=tmp_path)
    assert r.returncode == 1
    assert r.stdout == ""


# --- suministro.py ---

def test_suministro_avisa_si_falta_lock_y_enfriamiento(raiz):
    (raiz / "pyproject.toml").write_text("[project]\nname='x'\n")
    r = correr(SUMINISTRO, raiz)
    assert r.returncode == 1
    assert "No hay uv.lock" in r.stdout and "exclude-newer" in r.stdout
    assert "No instalados" in r.stdout and "pip-audit" in r.stdout


def test_suministro_todo_ok(raiz):
    (raiz / "pyproject.toml").write_text('[tool.uv]\nexclude-newer = "7 days"\n')
    (raiz / "uv.lock").write_text("")
    (raiz / ".github" / "workflows").mkdir(parents=True)
    for nombre in ["uv", "pip-audit", "osv-scanner", "gitleaks", "zizmor"]:
        falsa(raiz, nombre, 0)
    r = correr(SUMINISTRO, raiz)
    assert r.returncode == 0, r.stdout
    assert "5/5 pasos OK, 0 avisos" in r.stdout


def test_suministro_falla_si_hay_cve(raiz):
    (raiz / "pyproject.toml").write_text('[tool.uv]\nexclude-newer = "7 days"\n')
    (raiz / "uv.lock").write_text("")
    falsa(raiz, "uv", 0)
    falsa(raiz, "pip-audit", 1, "requests 2.0 GHSA-xxxx")
    r = correr(SUMINISTRO, raiz)
    assert r.returncode == 1
    assert "FALLA pip-audit" in r.stdout and "GHSA-xxxx" in r.stdout
