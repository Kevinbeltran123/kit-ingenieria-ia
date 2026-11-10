"""Corre los sensores de calidad que el repo tenga configurados y resume el resultado.

Orden: uv lock --check, ruff check, ruff format --check, tipos (ty/mypy/pyright),
import-linter, pytest, deptry. Sale con 1 si algo falla, si una herramienta configurada
no está instalada (no revisada no cuenta como OK) o si no hay nada que verificar.
Uso: python3 verify.py [raiz]
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

MAX_LINEAS = 25


def buscar_herramienta(raiz: Path, nombre: str) -> str | None:
    local = raiz / ".venv" / "bin" / nombre
    return str(local) if local.exists() else shutil.which(nombre)


def configurado(raiz: Path, seccion: str, *archivos: str) -> bool:
    """`seccion` es `tool.ty`: cuenta `[tool.ty]` y `[tool.ty.environment]`, no `[tool.typos]`."""
    pyproject = raiz / "pyproject.toml"
    if pyproject.exists() and re.search(rf"(?m)^\s*\[\[?{re.escape(seccion)}[\].]", pyproject.read_text()):
        return True
    return any((raiz / a).exists() for a in archivos)


def pasos(raiz: Path) -> tuple[list[tuple[str, list[str], set[int]]], list[str]]:
    """Devuelve (pasos: nombre, comando y códigos aceptados; herramientas configuradas sin instalar)."""
    lista, faltan = [], []
    if (raiz / "uv.lock").exists():  # CI corre `uv sync --locked`, que falla con un lock viejo
        uv = buscar_herramienta(raiz, "uv")
        if uv:
            lista.append(("uv lock --check", [uv, "lock", "--check"], {0}))
        else:
            faltan.append("uv")

    ruff = buscar_herramienta(raiz, "ruff")
    if ruff:
        lista.append(("ruff check", [ruff, "check", "--output-format", "concise", "."], {0}))
        lista.append(("ruff format", [ruff, "format", "--check", "."], {0}))
    elif configurado(raiz, "tool.ruff", "ruff.toml", ".ruff.toml"):
        faltan.append("ruff")

    tipos = [
        (nombre, cmd)
        for nombre, seccion, archivos, cmd in [
            ("ty", "tool.ty", ["ty.toml"], ["check"]),
            ("mypy", "tool.mypy", ["mypy.ini", ".mypy.ini"], ["."]),
            ("pyright", "tool.pyright", ["pyrightconfig.json"], []),
        ]
        if configurado(raiz, seccion, *archivos)
    ]
    instalados = [(nombre, h, cmd) for nombre, cmd in tipos if (h := buscar_herramienta(raiz, nombre))]
    if instalados:
        nombre, herramienta, cmd = instalados[0]
        lista.append((nombre, [herramienta, *cmd], {0}))
    elif tipos:
        faltan.append(tipos[0][0])

    lint = buscar_herramienta(raiz, "lint-imports")
    if configurado(raiz, "tool.importlinter", ".importlinter"):
        if lint:
            lista.append(("import-linter", [lint], {0}))
        else:
            faltan.append("lint-imports")

    pytest = buscar_herramienta(raiz, "pytest")
    if configurado(raiz, "tool.pytest", "pytest.ini") or (raiz / "tests").is_dir():
        if pytest:
            lista.append(("pytest", [pytest, "-q", "--no-header"], {0, 5}))
        else:
            faltan.append("pytest")

    deptry = buscar_herramienta(raiz, "deptry")
    if deptry and (raiz / "pyproject.toml").exists():
        lista.append(("deptry", [deptry, "."], {0}))
    elif not deptry and configurado(raiz, "tool.deptry"):
        faltan.append("deptry")
    return lista, faltan


def main() -> int:
    raiz = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    lista, faltan = pasos(raiz)
    if not lista and not faltan:
        print("No encontré herramientas configuradas (ruff, tipos, pytest...). Nada que verificar.")
        return 1

    fallos = 0
    for nombre, cmd, aceptados in lista:
        r = subprocess.run(cmd, cwd=raiz, capture_output=True, text=True)
        if r.returncode in aceptados:
            print(f"OK    {nombre}")
            continue
        fallos += 1
        print(f"FALLA {nombre}")
        for linea in (r.stdout + r.stderr).strip().splitlines()[-MAX_LINEAS:]:
            print(f"      {linea}")

    if faltan:
        print(f"\nNo instalados (no se revisó): {', '.join(faltan)}. Corre `uv sync` o instálalos.")
    print(f"\n{len(lista) - fallos}/{len(lista)} pasos OK, {len(faltan)} sin revisar")
    return 1 if fallos or faltan else 0


if __name__ == "__main__":
    sys.exit(main())
