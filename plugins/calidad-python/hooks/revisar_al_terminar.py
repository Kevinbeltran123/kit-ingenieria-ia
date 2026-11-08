"""Stop: antes de que Claude termine, revisa tipos, arquitectura y pruebas.

Solo actúa si en esta sesión se editaron archivos .py (lo anota
ruff_al_editar.py) y solo corre lo que el repo tenga configurado.
Si algo falla, sale con 2 y Claude debe arreglarlo. Revisa cada vez que
Claude intenta terminar, también después de corregir. Bloquea como máximo
MAX_BLOQUEOS veces por mensaje de la persona; si sigue fallando, deja
terminar y le avisa a la persona.
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
MAX_BLOQUEOS = 2


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


def bloqueos_previos(contador: Path) -> int:
    try:
        return int(contador.read_text())
    except (OSError, ValueError):
        return 0


def main() -> int:
    datos = json.load(sys.stdin)
    sesion = re.sub(r"[^A-Za-z0-9_-]", "", datos.get("session_id", "")) or "sin-sesion"
    carpeta = Path(tempfile.gettempdir()) / "claude-calidad-python"
    marca = carpeta / sesion
    contador = carpeta / f"{sesion}.bloqueos"
    if not marca.exists():
        return 0

    raiz = Path(os.environ.get("CLAUDE_PROJECT_DIR") or datos.get("cwd") or ".")
    editados = sorted({p for p in marca.read_text().splitlines() if p and Path(p).exists()})

    fallos = {}
    for nombre, cmd, aceptados in comandos(raiz, editados):
        r = subprocess.run(cmd, cwd=raiz, capture_output=True, text=True)
        if r.returncode not in aceptados:
            salida = (r.stdout + r.stderr).strip().splitlines()[-MAX_LINEAS:]
            fallos[nombre] = f"## {nombre} falló\n" + "\n".join(salida)

    if not fallos:
        marca.unlink()
        contador.unlink(missing_ok=True)
        return 0

    # stop_hook_active también es True si bloqueó otro plugin; por eso se cuentan
    # solo los bloqueos propios. Sin stop_hook_active, la persona escribió de nuevo.
    bloqueos = bloqueos_previos(contador) if datos.get("stop_hook_active") else 0
    if bloqueos < MAX_BLOQUEOS:
        contador.write_text(str(bloqueos + 1))
        print("Antes de terminar, corrige esto:\n\n" + "\n\n".join(fallos.values()), file=sys.stderr)
        return 2

    marca.unlink()
    contador.unlink(missing_ok=True)
    aviso = (f"calidad-python: después de {MAX_BLOQUEOS} intentos sigue fallando "
             f"{', '.join(fallos)}. Revísalo antes de dar la tarea por terminada.")
    print(json.dumps({"systemMessage": aviso}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
