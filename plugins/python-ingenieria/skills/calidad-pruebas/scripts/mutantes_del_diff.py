"""Convierte los .py cambiados respecto a una rama en patrones de módulo para mutmut 3.

Ejemplo: src/app/domain/lote.py -> "app.domain.lote*"
Uso:     mutmut run $(python3 mutantes_del_diff.py --base origin/main)

Incluye cambios commiteados (base...HEAD), sin commitear y archivos nuevos.
Excluye pruebas, conftest y __init__.py vacíos de lógica.
"""

import argparse
import subprocess
import sys
from pathlib import PurePosixPath


def archivos_cambiados(base: str) -> set[str]:
    comandos = [
        ["git", "diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD"],
        ["git", "diff", "--name-only", "--diff-filter=ACMR", "HEAD"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ]
    archivos: set[str] = set()
    for cmd in comandos:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            archivos.update(l for l in r.stdout.splitlines() if l)
    return archivos


def a_patron(ruta: str) -> str | None:
    p = PurePosixPath(ruta)
    if p.suffix != ".py" or p.name == "conftest.py" or p.name.startswith("test_") or p.name.endswith("_test.py"):
        return None
    partes = list(p.with_suffix("").parts)
    if partes and partes[0] in {"tests", "test"}:
        return None
    if partes and partes[0] == "src":
        partes = partes[1:]
    if partes and partes[-1] == "__init__":
        partes = partes[:-1]
    if not partes:
        return None
    return ".".join(partes) + "*"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="origin/main")
    args = parser.parse_args()
    patrones = sorted({pat for f in archivos_cambiados(args.base) if (pat := a_patron(f))})
    if not patrones:
        print("No hay archivos de código cambiados para mutar.", file=sys.stderr)
        return 1
    print(" ".join(f'"{p}"' if " " in p else p for p in patrones))
    return 0


if __name__ == "__main__":
    sys.exit(main())
