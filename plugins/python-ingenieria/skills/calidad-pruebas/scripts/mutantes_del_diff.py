"""Convierte los .py cambiados respecto a una rama en patrones de módulo para mutmut 3.

Ejemplo: src/app/domain/lote.py -> "app.domain.lote.*"  (mutmut 3 nombra los mutantes
módulo.x_función__mutmut_N; el punto evita tomar también lote_historico)
Uso:     pats=$(python3 mutantes_del_diff.py --base origin/main) || exit 1
         uv run mutmut run $pats

Incluye cambios commiteados (base...HEAD), sin commitear y archivos nuevos.
Excluye pruebas y conftest. Sale con 1 si no hay código cambiado y con 2 si la base no
existe: en los dos casos no imprime nada, para que mutmut no termine mutando todo el repo.
"""

from __future__ import annotations

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
        # Solo las funciones y métodos del propio __init__ (x_ y xǁ), no los submódulos del paquete.
        return ".".join(partes[:-1]) + ".x*" if len(partes) > 1 else None
    if not partes:
        return None
    return ".".join(partes) + ".*"


def base_existe(base: str) -> bool:
    r = subprocess.run(["git", "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}"], capture_output=True)
    return r.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="origin/main")
    args = parser.parse_args()
    if not base_existe(args.base):
        print(
            f"No existe la base {args.base}. Pásala con --base; en CI usa fetch-depth: 0 para tener la historia.",
            file=sys.stderr,
        )
        return 2
    patrones = sorted({pat for f in archivos_cambiados(args.base) if (pat := a_patron(f))})
    if not patrones:
        print("No hay archivos de código cambiados para mutar.", file=sys.stderr)
        return 1
    print(" ".join(f'"{p}"' if " " in p else p for p in patrones))
    return 0


if __name__ == "__main__":
    sys.exit(main())
