"""Las versiones que el kit repite en varios sitios tienen que coincidir.

Dependabot solo sube las acciones de .github/workflows del kit y el lockfile de Claude Code; uv, prek y
gitleaks se suben a mano, y una versión subida en un sitio y no en otro deja la regla de los 7 días a medias.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]


def texto(ruta: str) -> str:
    return (KIT / ruta).read_text()


def test_uv_tiene_una_sola_version():
    """setup-uv en los dos CI, el rev de uv-pre-commit, la imagen del Dockerfile y el «probado con» del README."""
    rev = re.search(r"uv-pre-commit\n\s+rev: (\S+)", texto("plantillas/python/.pre-commit-config.yaml")).group(1)
    for ci in (".github/workflows/ci.yml", "plantillas/github/workflows/ci.yml"):
        versiones = re.findall(r'^\s+version: "([\d.]+)"', texto(ci), re.M)
        assert versiones and set(versiones) == {rev}, (ci, versiones)
    assert re.search(r"astral-sh/uv:([\d.]+)-python", texto("plantillas/docker/Dockerfile")).group(1) == rev
    assert rev in texto("plantillas/README.md")


def test_gitleaks_misma_version_en_pre_commit_y_ci():
    rev = re.search(r"gitleaks/gitleaks\n\s+rev: v([\d.]+)", texto("plantillas/python/.pre-commit-config.yaml")).group(
        1
    )
    ci = texto("plantillas/github/workflows/ci.yml")
    assert f"download/v{rev}/gitleaks_{rev}_linux_x64.tar.gz" in ci
    assert f"gitleaks {rev}" in ci  # el nombre del paso


def test_prek_fijado_igual_en_todos_los_sitios():
    """`uvx prek` sin versión instala la última aunque tenga horas: cada mención lleva la misma versión."""
    version = re.search(r"uvx prek@([\d.]+) run", texto("plantillas/github/workflows/ci.yml")).group(1)
    for ruta in (
        "README.md",
        "bin/adoptar.py",
        "bin/humo_plantillas.py",
        "plantillas/README.md",
        "plantillas/claude/CLAUDE.md",
        "plantillas/python/.pre-commit-config.yaml",
        "plantillas/github/workflows/ci.yml",
    ):
        t = texto(ruta)
        assert set(re.findall(r"prek@([\d.]+)", t)) <= {version}, ruta
        assert not re.search(r"uvx prek(?![@\w])", t), f"{ruta}: uvx prek sin versión"


def test_acciones_del_kit_y_de_la_plantilla_con_el_mismo_sha():
    """Dependabot solo ve .github/workflows del kit: al aceptar su PR hay que copiar el SHA a la plantilla."""

    def acciones(ruta: str) -> dict[str, str]:
        return dict(re.findall(r"uses: ([\w./-]+)@([0-9a-f]{40})", texto(ruta)))

    kit = acciones(".github/workflows/ci.yml")
    for ruta in ("plantillas/github/workflows/ci.yml", "plantillas/github/workflows/claude-review.yml"):
        plantilla = acciones(ruta)
        comunes = set(kit) & set(plantilla)
        assert comunes, ruta
        for accion in comunes:
            assert plantilla[accion] == kit[accion], (ruta, accion)


def test_claude_code_del_ci_sale_del_lockfile():
    paquete = json.loads(texto(".github/claude-code/package.json"))["dependencies"]["@anthropic-ai/claude-code"]
    lock = json.loads(texto(".github/claude-code/package-lock.json"))["packages"]
    assert lock[""]["dependencies"]["@anthropic-ai/claude-code"] == paquete
    assert lock["node_modules/@anthropic-ai/claude-code"]["version"] == paquete


def test_terceros_fijados_por_sha_de_40():
    plugins = json.loads(texto(".claude-plugin/marketplace.json"))["plugins"]
    terceros = [p for p in plugins if isinstance(p["source"], dict)]
    assert terceros
    for p in terceros:
        assert re.fullmatch(r"[0-9a-f]{40}", p["source"]["sha"]), p["name"]


def test_ruff_del_kit_una_sola_version():
    """El CI del kit, el comentario de pyproject.toml y el README corren ruff con la misma versión fijada."""
    versiones = set()
    for ruta in (".github/workflows/ci.yml", "pyproject.toml", "README.md", "CONVENCIONES.md"):
        encontradas = re.findall(r"ruff@([\d.]+)", texto(ruta))
        assert encontradas, ruta
        versiones |= set(encontradas)
    assert len(versiones) == 1, versiones
