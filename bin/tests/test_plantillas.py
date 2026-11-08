"""Prueba de humo: los contratos de import-linter de la plantilla funcionan en un proyecto real.

Revisar solo la sintaxis del fragmento no basta: el 2026-11-08 el contrato `forbidden` fallaba
siempre porque faltaba `include_external_packages = true`.
"""

from __future__ import annotations

import json
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


def test_las_reglas_de_secretos_cubren_cualquier_carpeta():
    """Read(./.env) solo cubre la raíz; Read(**/.env) cubre services/api/.env y cualquier otra carpeta."""
    reglas = json.loads((KIT / "plantillas" / "claude" / "settings.json").read_text())["permissions"]["deny"]
    for patron in ("Read(**/.env)", "Read(**/.env.*)", "Read(**/.envrc)", "Read(**/secrets/**)"):
        assert patron in reglas, patron
    assert not [r for r in reglas if r.startswith("Read(./")]


def test_repo_sin_adaptadores_ni_entrypoints_todavia_pasa(tmp_path):
    r = lint_imports(crear_proyecto(tmp_path, capas=("domain", "application")))
    assert r.returncode == 0, r.stdout + r.stderr


def marketplace_de_revision(flujo: str) -> dict:
    """El marketplace.json que arma claude-review.yml en el heredoc <<'JSON'."""
    return json.loads(flujo.split("<<'JSON'\n", 1)[1].split("\n          JSON\n", 1)[0])


def test_la_revision_usa_pr_review_toolkit_en_el_commit_auditado():
    """claude-review.yml instala pr-review-toolkit desde el commit que el kit fijó y auditó, no desde main."""
    flujo = (KIT / "plantillas" / "github" / "workflows" / "claude-review.yml").read_text()
    entradas = json.loads((KIT / ".claude-plugin" / "marketplace.json").read_text())["plugins"]
    auditada = next(p["source"] for p in entradas if p["name"] == "pr-review-toolkit")
    marketplace = marketplace_de_revision(flujo)
    assert [p["source"] for p in marketplace["plugins"]] == [auditada]  # mismo url, path, ref y sha
    assert re.search(r"plugin_marketplaces: \$\{\{ runner\.temp \}\}/marketplace-revision\n", flujo)
    assert f'plugins: "pr-review-toolkit@{marketplace["name"]}"' in flujo
