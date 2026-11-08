"""Stop: antes de que Claude termine, revisa tipos, arquitectura y pruebas.

Solo actúa si en esta sesión se editaron archivos .py (lo anota
ruff_al_editar.py) y solo corre lo que el repo tenga configurado.
Si algo falla, sale con 2 y Claude debe arreglarlo. Un solo reintento:
si ya está continuando por este hook, lo deja terminar.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MAX_LINEAS = 40


def buscar_herramienta(raiz: Path, nombre: str) -> str | None:
    local = raiz / ".venv" / "bin" / nombre
    return str(local) if local.exists() else shutil.which(nombre)


def configurado(raiz: Path, seccion: str, *archivos: str) -> bool:
    pyproject = raiz / "pyproject.toml"
    if pyproject.exists() and f"[{seccion}" in pyproject.read_text():
        return True
    return any((raiz / a).exists() for a in archivos)


def comandos(raiz: Path, editados: list[str]) -> list[tuple[str, list[str], set[int]]]:
    """Lista (nombre, comando, códigos de salida aceptados) según lo que use el repo."""
    lista = []
    for nombre, seccion, archivos in [
        ("ty", "tool.ty", ["ty.toml"]),
        ("mypy", "tool.mypy", ["mypy.ini", ".mypy.ini"]),
        ("pyright", "tool.pyright", ["pyrightconfig.json"]),
    ]:
        herramienta = buscar_herramienta(raiz, nombre)
        if herramienta and configurado(raiz, seccion, *archivos):
            sub = ["check"] if nombre == "ty" else []
            lista.append((nombre, [herramienta, *sub, *editados], {0}))
            break

    lint = buscar_herramienta(raiz, "lint-imports")
    if lint and configurado(raiz, "tool.importlinter", ".importlinter"):
        lista.append(("import-linter", [lint], {0}))

    pytest = buscar_herramienta(raiz, "pytest")
    if pytest and (configurado(raiz, "tool.pytest", "pytest.ini") or (raiz / "tests").is_dir()):
        # 5 = no encontró pruebas; no es un fallo.
        lista.append(("pytest", [pytest, "-x", "-q", "--no-header"], {0, 5}))
    return lista


def main() -> int:
    datos = json.load(sys.stdin)
    sesion = re.sub(r"[^A-Za-z0-9_-]", "", datos.get("session_id", "")) or "sin-sesion"
    marca = Path(tempfile.gettempdir()) / "claude-calidad-python" / sesion
    if not marca.exists():
        return 0
    if datos.get("stop_hook_active"):
        marca.unlink()
        return 0

    raiz = Path(os.environ.get("CLAUDE_PROJECT_DIR") or datos.get("cwd") or ".")
    editados = sorted({p for p in marca.read_text().splitlines() if p and Path(p).exists()})

    fallos = []
    for nombre, cmd, aceptados in comandos(raiz, editados):
        r = subprocess.run(cmd, cwd=raiz, capture_output=True, text=True)
        if r.returncode not in aceptados:
            salida = (r.stdout + r.stderr).strip().splitlines()[-MAX_LINEAS:]
            fallos.append(f"## {nombre} falló\n" + "\n".join(salida))

    if fallos:
        print("Antes de terminar, corrige esto:\n\n" + "\n\n".join(fallos), file=sys.stderr)
        return 2
    marca.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main())
