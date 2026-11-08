"""Corre los detectores de deuda técnica disponibles y escribe un informe markdown.

Detectores: vulture (código muerto), deptry (dependencias), complexipy
(complejidad cognitiva) y jscpd (duplicados, si está instalado). Siempre sale
con 0: es un informe, no un bloqueo.

Uso: python3 deuda.py [raiz] [--salida informe.md]
"""

import argparse
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

MAX_LINEAS = 60


def buscar_herramienta(raiz: Path, nombre: str) -> str | None:
    local = raiz / ".venv" / "bin" / nombre
    return str(local) if local.exists() else shutil.which(nombre)


def carpeta_codigo(raiz: Path) -> str:
    return "src" if (raiz / "src").is_dir() else "."


def detectores(raiz: Path) -> list[tuple[str, str, list[str] | None]]:
    """(titulo, herramienta, comando o None si no está instalada)."""
    codigo = carpeta_codigo(raiz)
    especificacion = [
        ("Código muerto", "vulture", [codigo, "--min-confidence", "80"]),
        ("Dependencias", "deptry", ["."]),
        ("Complejidad cognitiva", "complexipy", [codigo, "--max-complexity-allowed", "15", "--failed"]),
        ("Código duplicado", "jscpd", ["--min-lines", "8", "--reporters", "console", codigo]),
    ]
    lista = []
    for titulo, nombre, args in especificacion:
        herramienta = buscar_herramienta(raiz, nombre)
        lista.append((titulo, nombre, [herramienta, *args] if herramienta else None))
    return lista


def informe(raiz: Path) -> str:
    partes = [f"# Informe de deuda técnica — {date.today().isoformat()}", "", f"Repo: `{raiz}`", ""]
    faltantes = []
    for titulo, nombre, cmd in detectores(raiz):
        if cmd is None:
            faltantes.append(nombre)
            continue
        r = subprocess.run(cmd, cwd=raiz, capture_output=True, text=True)
        salida = (r.stdout + r.stderr).strip().splitlines()
        estado = "sin hallazgos" if r.returncode == 0 and not salida else f"{len(salida)} líneas de salida"
        partes += [f"## {titulo} ({nombre}) — {estado}", ""]
        if salida:
            recorte = salida[:MAX_LINEAS]
            partes += ["```", *recorte, "```"]
            if len(salida) > MAX_LINEAS:
                partes.append(f"_({len(salida) - MAX_LINEAS} líneas más; corre `{nombre}` directamente)_")
        partes.append("")
    if faltantes:
        partes += ["## No instalados", "", ", ".join(f"`{n}`" for n in faltantes), ""]
    return "\n".join(partes)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("raiz", nargs="?", default=".")
    parser.add_argument("--salida")
    args = parser.parse_args()
    texto = informe(Path(args.raiz).resolve())
    if args.salida:
        Path(args.salida).write_text(texto)
        print(f"Informe escrito en {args.salida}")
    else:
        print(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
