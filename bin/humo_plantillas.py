"""Prueba de humo de las plantillas: arma un repo nuevo con ellas y corre lo que corre su CI.

Crea en una carpeta temporal un paquete `app` con capas de dominio y aplicación, le aplica
bin/adoptar.py y el fragmento de pyproject, y corre los pasos del job `calidad` de
plantillas/github/workflows/ci.yml más todos los hooks de pre-commit. Si una plantilla se
rompe (como el import-linter que fallaba siempre, B1), falla aquí y no en un repo de verdad.

Uso: python3 bin/humo_plantillas.py [--conservar]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent

PYPROJECT = '''[project]
name = "app"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[build-system]
requires = ["uv_build>=0.13,<0.14"]
build-backend = "uv_build"

'''

ARCHIVOS = {
    "src/app/__init__.py": '"""Paquete de prueba del kit."""\n',
    "src/app/domain/__init__.py": '"""Dominio."""\n',
    "src/app/domain/lote.py": '''"""Reglas del lote."""


def rendimiento_kg_ha(kg: float, hectareas: float) -> float:
    """Kilos por hectárea; las hectáreas tienen que ser positivas."""
    if hectareas <= 0:
        msg = "las hectáreas deben ser positivas"
        raise ValueError(msg)
    return kg / hectareas
''',
    "src/app/application/__init__.py": '"""Casos de uso."""\n',
    "src/app/application/reporte.py": '''"""Reporte de rendimiento."""

from app.domain.lote import rendimiento_kg_ha


def reportar(kg: float, hectareas: float) -> str:
    """Rendimiento del lote como texto."""
    return f"{rendimiento_kg_ha(kg, hectareas):.1f} kg/ha"
''',
    "tests/test_lote.py": '''import pytest

from app.application.reporte import reportar
from app.domain.lote import rendimiento_kg_ha


def test_rendimiento():
    assert rendimiento_kg_ha(1000, 4) == 250


def test_hectareas_cero_es_error():
    with pytest.raises(ValueError, match="positivas"):
        rendimiento_kg_ha(1, 0)


def test_reporte():
    assert reportar(1000, 4) == "250.0 kg/ha"
''',
}

# Los pasos del job `calidad` de la plantilla de CI, en su orden, salvo pip-audit (depende de la
# base de CVE del día) y vulture (no bloquea). prek corre aquí todos los hooks, no solo los que
# el CI de la plantilla no cubre.
PASOS = [
    ["uv", "sync", "--locked"],
    ["uvx", "prek@0.5.9", "run", "--all-files", "--show-diff-on-failure"],
    ["uv", "run", "ruff", "check", "."],
    ["uv", "run", "ruff", "format", "--check", "."],
    ["uv", "run", "ty", "check"],
    ["uv", "run", "lint-imports"],
    ["uv", "run", "pytest", "-q"],
    ["uv", "run", "deptry", "."],
]


def armar(repo: Path) -> None:
    subprocess.run([sys.executable, str(KIT / "bin" / "adoptar.py"), str(repo), "--sin-docker"],
                   check=True, capture_output=True)
    fragmento = (KIT / "plantillas" / "python" / "pyproject.toml.fragmento").read_text()
    (repo / "pyproject.toml").write_text(PYPROJECT + fragmento)
    for ruta, texto in ARCHIVOS.items():
        archivo = repo / ruta
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(texto)
    for cmd in (["git", "init", "-q", "-b", "main"], ["uv", "lock", "-q"], ["git", "add", "-A"]):
        subprocess.run(cmd, cwd=repo, check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--conservar", action="store_true", help="no borrar el repo de prueba")
    args = parser.parse_args(argv)
    faltan = [h for h in ("uv", "uvx", "git") if not shutil.which(h)]
    if faltan:
        print(f"Faltan en el PATH: {', '.join(faltan)}", file=sys.stderr)
        return 2

    base = Path(tempfile.mkdtemp(prefix="humo-kit-"))
    repo = base / "repo"
    repo.mkdir()
    try:
        armar(repo)
        fallos = []
        for cmd in PASOS:
            print(f"\n$ {' '.join(cmd)}", flush=True)
            if subprocess.run(cmd, cwd=repo).returncode != 0:
                fallos.append(" ".join(cmd))
    finally:
        if args.conservar:
            print(f"\nRepo de prueba: {repo}")
        else:
            shutil.rmtree(base, ignore_errors=True)

    if fallos:
        print(f"\nFALLA en {len(fallos)} de {len(PASOS)} pasos:", *fallos, sep="\n  ")
        return 1
    print(f"\n{len(PASOS)}/{len(PASOS)} pasos OK: las plantillas funcionan en un repo nuevo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
