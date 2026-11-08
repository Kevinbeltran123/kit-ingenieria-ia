"""Los hooks y scripts del kit deben correr con Python 3.9 (el python3 de macOS y de Amazon Linux 2023).

Con 3.9, una anotación como `str | None` falla al cargar el archivo. Un hook que se cae así sale
con 1, y Claude Code lo trata como error no bloqueante: la acción sigue. En barreras eso deja la
barrera abierta.
"""

from __future__ import annotations

import ast
import shutil
import subprocess
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[2]
SCRIPTS = sorted([
    *KIT.glob("plugins/*/hooks/*.py"),
    *KIT.glob("plugins/*/skills/*/scripts/*.py"),
    *KIT.glob("bin/*.py"),
])


def nombre(ruta: Path) -> str:
    return str(ruta.relative_to(KIT))


def python_39() -> str | None:
    for candidato in ("/usr/bin/python3", shutil.which("python3.9")):
        if not candidato or not Path(candidato).exists():
            continue
        r = subprocess.run([candidato, "-c", "import sys; print(sys.version_info[:2] == (3, 9))"],
                           capture_output=True, text=True)
        if r.stdout.strip() == "True":
            return candidato
    return None


@pytest.mark.parametrize("ruta", SCRIPTS, ids=nombre)
def test_difiere_las_anotaciones(ruta):
    arbol = ast.parse(ruta.read_text())
    assert any(isinstance(n, ast.ImportFrom) and n.module == "__future__"
               and any(a.name == "annotations" for a in n.names) for n in arbol.body), \
        "falta `from __future__ import annotations` después del docstring"


@pytest.mark.parametrize("ruta", [s for s in SCRIPTS if "# /// script" not in s.read_text()], ids=nombre)
def test_carga_con_python_39(ruta):
    interprete = python_39()
    if interprete is None:
        pytest.skip("no hay un Python 3.9 en esta máquina")
    r = subprocess.run([interprete, "-I", "-c", "import runpy, sys; runpy.run_path(sys.argv[1], run_name='carga')",
                        str(ruta)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-600:]
