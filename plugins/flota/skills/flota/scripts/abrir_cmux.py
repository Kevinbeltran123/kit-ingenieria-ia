"""Abre el espacio «Flota» de cmux desde una terminal de cmux, sin pasar por la paleta de comandos.

Uso (dentro de una terminal de cmux): python3 -I abrir_cmux.py [--nombre Flota]
Lee el comando con ese nombre del cmux.json de usuario (~/.config/cmux/cmux.json, o FLOTA_CMUX_JSON) y crea el
espacio con `cmux new-workspace --layout`, así el diseño vive en un solo sitio.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def leer_comando(ruta: Path, nombre: str) -> dict | None:
    """El comando `nombre` del cmux.json (JSONC: se quitan las líneas de comentario)."""
    texto = re.sub(r"^\s*//.*$", "", ruta.read_text(encoding="utf-8"), flags=re.MULTILINE)
    for comando in json.loads(texto).get("commands", []):
        if comando.get("name") == nombre:
            return comando
    return None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--nombre", default="Flota")
    a = p.parse_args(argv)
    ruta = Path(os.environ.get("FLOTA_CMUX_JSON") or Path.home() / ".config" / "cmux" / "cmux.json")
    try:
        comando = leer_comando(ruta, a.nombre)
    except (OSError, ValueError) as e:
        print(f"no se pudo leer {ruta}: {e}", file=sys.stderr)
        return 1
    espacio = (comando or {}).get("workspace")
    if not espacio:
        print(f"{ruta} no tiene un comando «{a.nombre}» con espacio de trabajo", file=sys.stderr)
        return 1
    cwd = str(Path(espacio.get("cwd", "~")).expanduser())
    nombre = espacio.get("name", a.nombre)
    orden = [
        "cmux",
        "new-workspace",
        "--name",
        nombre,
        "--focus",
        "true",
        "--cwd",
        cwd,
        "--layout",
        json.dumps(espacio["layout"]),
    ]
    try:
        r = subprocess.run(orden, capture_output=True, text=True, timeout=30, check=False)
    except FileNotFoundError:
        print("no se encontró cmux en PATH", file=sys.stderr)
        return 1
    if r.returncode != 0:
        print(f"cmux no abrió el espacio: {(r.stderr or r.stdout).strip()}", file=sys.stderr)
        print("Corre este comando desde una terminal de cmux (cmux solo acepta procesos nacidos dentro de él).",
              file=sys.stderr)  # fmt: skip
        return 1
    print(r.stdout.strip() or f"espacio «{a.nombre}» abierto")
    return 0


if __name__ == "__main__":
    sys.exit(main())
