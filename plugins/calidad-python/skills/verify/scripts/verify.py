"""Corre los sensores de calidad que el repo tenga configurados y resume el resultado.

Orden: ruff check, ruff format --check, tipos (ty/mypy/pyright), import-linter,
pytest, deptry. Sale con 1 si algo falla. Uso: python3 verify.py [raiz]
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

MAX_LINEAS = 25


def buscar_herramienta(raiz: Path, nombre: str) -> str | None:
    local = raiz / ".venv" / "bin" / nombre
    return str(local) if local.exists() else shutil.which(nombre)


def configurado(raiz: Path, seccion: str, *archivos: str) -> bool:
    pyproject = raiz / "pyproject.toml"
    if pyproject.exists() and f"[{seccion}" in pyproject.read_text():
        return True
    return any((raiz / a).exists() for a in archivos)


def pasos(raiz: Path) -> list[tuple[str, list[str], set[int]]]:
    """Lista (nombre, comando, códigos aceptados) según lo que use el repo."""
    lista = []
    ruff = buscar_herramienta(raiz, "ruff")
    if ruff:
        lista.append(("ruff check", [ruff, "check", "--output-format", "concise", "."], {0}))
        lista.append(("ruff format", [ruff, "format", "--check", "."], {0}))

    for nombre, seccion, archivos, cmd in [
        ("ty", "tool.ty", ["ty.toml"], ["check"]),
        ("mypy", "tool.mypy", ["mypy.ini", ".mypy.ini"], ["."]),
        ("pyright", "tool.pyright", ["pyrightconfig.json"], []),
    ]:
        herramienta = buscar_herramienta(raiz, nombre)
        if herramienta and configurado(raiz, seccion, *archivos):
            lista.append((nombre, [herramienta, *cmd], {0}))
            break

    lint = buscar_herramienta(raiz, "lint-imports")
    if lint and configurado(raiz, "tool.importlinter", ".importlinter"):
        lista.append(("import-linter", [lint], {0}))

    pytest = buscar_herramienta(raiz, "pytest")
    if pytest and (configurado(raiz, "tool.pytest", "pytest.ini") or (raiz / "tests").is_dir()):
        lista.append(("pytest", [pytest, "-q", "--no-header"], {0, 5}))

    deptry = buscar_herramienta(raiz, "deptry")
    if deptry and (raiz / "pyproject.toml").exists():
        lista.append(("deptry", [deptry, "."], {0}))
    return lista


def main() -> int:
    raiz = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    lista = pasos(raiz)
    if not lista:
        print("No encontré herramientas configuradas (ruff, tipos, pytest...). Nada que verificar.")
        return 0

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

    print(f"\n{len(lista) - fallos}/{len(lista)} pasos OK")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
