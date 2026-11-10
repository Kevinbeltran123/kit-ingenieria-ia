"""Pruebas de adoptar.py sobre repos temporales, y validación de sintaxis de las plantillas."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BIN = Path(__file__).resolve().parent.parent
KIT = BIN.parent
PLANTILLAS = KIT / "plantillas"
sys.path.insert(0, str(BIN))

import adoptar  # noqa: E402


def correr(*args):
    return subprocess.run(
        [sys.executable, "-I", str(BIN / "adoptar.py"), *map(str, args)], capture_output=True, text=True
    )


def test_crea_todo_en_repo_vacio(tmp_path):
    r = correr(tmp_path)
    assert r.returncode == 0, r.stderr
    for destino in [
        ".python-version",
        ".pre-commit-config.yaml",
        "CLAUDE.md",
        ".github/workflows/ci.yml",
        ".github/workflows/claude-review.yml",
        ".github/dependabot.yml",
        "Dockerfile",
        ".dockerignore",
        ".claude/settings.json",
    ]:
        assert (tmp_path / destino).exists(), destino
    settings = json.loads((tmp_path / ".claude/settings.json").read_text())
    fuente = settings["extraKnownMarketplaces"]["kit-ingenieria-ia"]["source"]
    assert fuente == {"source": "directory", "path": str(KIT)}
    assert set(settings["enabledPlugins"]) == {f"{p}@kit-ingenieria-ia" for p in adoptar.PLUGINS["base"]}
    assert "Pasos manuales" in r.stdout
    assert (tmp_path / ".python-version").read_text().strip() == "3.12"  # la misma del Dockerfile y de ty


def test_nunca_sobrescribe(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("mío")
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / ".github/workflows/ci.yml").write_text("mío")
    r = correr(tmp_path)
    assert r.returncode == 0
    assert (tmp_path / "CLAUDE.md").read_text() == "mío"
    assert (tmp_path / ".github/workflows/ci.yml").read_text() == "mío"
    assert "ya existe, no se tocó: CLAUDE.md" in r.stdout


def test_perfil_ml_crea_codeowners_del_evaluador(tmp_path):
    r = correr(tmp_path, "--perfil", "ml", "--sin-docker")
    assert r.returncode == 0, r.stderr
    reglas = [
        l.split()[0]
        for l in (tmp_path / ".github/CODEOWNERS").read_text().splitlines()
        if l.strip() and not l.startswith("#")
    ]
    for ruta in ["/eval/", "/splits/", "/data/splits/", "/.claude/ml-vision.json"]:
        assert ruta in reglas, ruta
    assert "Require review from Code Owners" in r.stdout


def test_otros_perfiles_no_crean_codeowners(tmp_path):
    assert correr(tmp_path, "--perfil", "datos", "--sin-docker").returncode == 0
    assert not (tmp_path / ".github/CODEOWNERS").exists()


@pytest.mark.parametrize("existente", ["CODEOWNERS", "docs/CODEOWNERS"])
def test_codeowners_en_otra_ubicacion_no_se_tapa(tmp_path, existente):
    """GitHub usa el primero que encuentra en .github/, raíz y docs/: crear .github/CODEOWNERS
    reemplazaría en silencio los dueños que el repo ya tiene."""
    (tmp_path / existente).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / existente).write_text("* @equipo\n")
    r = correr(tmp_path, "--perfil", "ml", "--sin-docker")
    assert r.returncode == 0, r.stderr
    assert not (tmp_path / ".github/CODEOWNERS").exists()
    assert f"ya existe, no se tocó: {existente}" in r.stdout


def fuente_del_kit(repo):
    settings = json.loads((repo / ".claude/settings.json").read_text())
    return settings["extraKnownMarketplaces"]["kit-ingenieria-ia"]["source"]


def test_pasar_a_github_reemplaza_la_fuente_local(tmp_path):
    assert correr(tmp_path, "--sin-docker").returncode == 0
    r = correr(tmp_path, "--sin-docker", "--marketplace-github", "acme/kit-ingenieria-ia", "--ref", "v0.2.0")
    assert r.returncode == 0, r.stderr
    assert fuente_del_kit(tmp_path) == {"source": "github", "repo": "acme/kit-ingenieria-ia", "ref": "v0.2.0"}
    assert "cambiado:" in r.stdout


def test_sin_marketplace_github_no_toca_una_fuente_existente(tmp_path):
    assert correr(tmp_path, "--sin-docker", "--marketplace-github", "acme/kit-ingenieria-ia").returncode == 0
    assert correr(tmp_path, "--sin-docker").returncode == 0
    assert fuente_del_kit(tmp_path) == {"source": "github", "repo": "acme/kit-ingenieria-ia"}


def test_dry_run_no_escribe(tmp_path):
    r = correr(tmp_path, "--dry-run")
    assert r.returncode == 0
    assert list(tmp_path.iterdir()) == []
    assert "[dry-run] creado: CLAUDE.md" in r.stdout


def test_fusiona_settings_sin_borrar_ni_cambiar(tmp_path):
    (tmp_path / ".claude").mkdir()
    previo = {
        "permissions": {"deny": ["Read(./.env)", "Bash(rm -rf *)"], "allow": ["Bash(make test)"]},
        "attribution": {"commit": "mi firma"},
        "enabledPlugins": {"otro@x": True, "barreras@kit-ingenieria-ia": False},
        "model": "opus",
    }
    (tmp_path / ".claude/settings.json").write_text(json.dumps(previo))
    r = correr(tmp_path, "--perfil", "ml")
    assert r.returncode == 0, r.stderr
    final = json.loads((tmp_path / ".claude/settings.json").read_text())
    assert final["model"] == "opus"
    assert final["permissions"]["allow"] == ["Bash(make test)"]
    assert final["permissions"]["deny"][:2] == ["Read(./.env)", "Bash(rm -rf *)"]
    assert final["permissions"]["deny"].count("Read(./.env)") == 1
    assert "Read(~/.aws/**)" in final["permissions"]["deny"]
    assert final["attribution"]["commit"] == "mi firma"  # no cambia valores existentes
    assert final["attribution"]["pr"] == ""
    assert final["enabledPlugins"]["barreras@kit-ingenieria-ia"] is False  # respeta la decisión previa
    assert final["enabledPlugins"]["otro@x"] is True
    assert final["enabledPlugins"]["ml-vision@kit-ingenieria-ia"] is True
    assert "fusionado: .claude/settings.json" in r.stdout


def test_fusion_idempotente(tmp_path):
    correr(tmp_path)
    antes = (tmp_path / ".claude/settings.json").read_text()
    r = correr(tmp_path)
    assert (tmp_path / ".claude/settings.json").read_text() == antes
    assert "ya tenía todo" in r.stdout


def test_marketplace_desde_github(tmp_path):
    correr(tmp_path, "--marketplace-github", "kevin/kit-ingenieria-ia", "--ref", "v0.1.0", "--sin-docker")
    settings = json.loads((tmp_path / ".claude/settings.json").read_text())
    assert settings["extraKnownMarketplaces"]["kit-ingenieria-ia"]["source"] == {
        "source": "github",
        "repo": "kevin/kit-ingenieria-ia",
        "ref": "v0.1.0",
    }
    assert not (tmp_path / "Dockerfile").exists()


def test_errores_de_uso(tmp_path):
    assert correr(tmp_path / "no-existe").returncode == 1
    assert correr(tmp_path, "--ref", "v1").returncode == 1


# --- Sintaxis de las plantillas ---


def test_plantillas_json_y_toml_validas():
    json.loads((PLANTILLAS / "claude/settings.json").read_text())
    tomllib = pytest.importorskip("tomllib")  # Python 3.11+
    tomllib.loads((PLANTILLAS / "python/pyproject.toml.fragmento").read_text())


YAMLS = [
    "python/.pre-commit-config.yaml",
    "github/workflows/ci.yml",
    "github/workflows/claude-review.yml",
    "github/dependabot.yml",
]


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv no disponible")
def test_plantillas_yaml_validas():
    rutas = [str(PLANTILLAS / y) for y in YAMLS]
    codigo = "import sys, yaml\nfor p in sys.argv[1:]: yaml.safe_load(open(p))"
    r = subprocess.run(
        ["uv", "run", "--no-project", "--with", "pyyaml", "python", "-c", codigo, *rutas],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
