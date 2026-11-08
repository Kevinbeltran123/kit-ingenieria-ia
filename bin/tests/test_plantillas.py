"""Prueba de humo: los contratos de import-linter de la plantilla funcionan en un proyecto real.

Revisar solo la sintaxis del fragmento no basta: el 2026-11-08 el contrato `forbidden` fallaba
siempre porque faltaba `include_external_packages = true`.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[2]
FRAGMENTO = KIT / "plantillas" / "python" / "pyproject.toml.fragmento"
VERSION = re.search(r'"import-linter>=([\d.]+)"', FRAGMENTO.read_text()).group(1)
CAPAS = ("domain", "application", "adapters", "entrypoints")


def crear_proyecto(raiz: Path, capas=CAPAS) -> Path:
    if shutil.which("uvx") is None:
        pytest.skip("hace falta uv para correr import-linter")
    (raiz / "src" / "app").mkdir(parents=True)
    (raiz / "src" / "app" / "__init__.py").write_text("")
    for capa in capas:
        (raiz / "src" / "app" / capa).mkdir()
        (raiz / "src" / "app" / capa / "__init__.py").write_text("")
    (raiz / "pyproject.toml").write_text(FRAGMENTO.read_text())
    return raiz


def lint_imports(raiz: Path) -> subprocess.CompletedProcess:
    r = subprocess.run(
        ["uvx", "--no-config", "--from", f"import-linter=={VERSION}", "lint-imports"],
        cwd=raiz, capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(raiz / "src")},
    )
    if "Failed to fetch" in r.stderr or "error sending request" in r.stderr:
        pytest.skip("uv no pudo descargar import-linter (sin red ni caché)")
    return r


def test_proyecto_limpio_pasa(tmp_path):
    r = lint_imports(crear_proyecto(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr


def test_dominio_que_importa_boto3_falla(tmp_path):
    raiz = crear_proyecto(tmp_path)
    (raiz / "src" / "app" / "domain" / "reglas.py").write_text("import boto3\n")
    r = lint_imports(raiz)
    assert r.returncode == 1
    assert "app.domain.reglas -> boto3" in r.stdout


def test_repo_sin_adaptadores_ni_entrypoints_todavia_pasa(tmp_path):
    r = lint_imports(crear_proyecto(tmp_path, capas=("domain", "application")))
    assert r.returncode == 0, r.stdout + r.stderr
