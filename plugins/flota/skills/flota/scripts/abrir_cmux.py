"""Abre el espacio «Flota» de cmux desde una terminal de cmux, sin pasar por la paleta de comandos.

Uso (dentro de una terminal de cmux): python3 -I abrir_cmux.py [--nombre Flota]
Lee el comando con ese nombre del cmux.json de usuario (~/.config/cmux/cmux.json, o FLOTA_CMUX_JSON) y crea el
espacio con `cmux new-workspace --layout`, así el diseño vive en un solo sitio. Después cierra los espacios viejos
con el mismo nombre (por ejemplo, la copia sin procesos que cmux restaura al reabrir la app).
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


def espacios_con_nombre(nombre: str) -> list[str]:
    """Referencias de los espacios de cmux que se llaman `nombre` (JSON si cmux lo da; si no, el texto de la lista)."""
    r = subprocess.run(["cmux", "workspace", "list", "--json"], capture_output=True, text=True, timeout=15, check=False)
    if r.returncode == 0:
        try:
            datos = json.loads(r.stdout)
        except ValueError:
            datos = None
        if datos is not None:
            filas = datos.get("workspaces", datos) if isinstance(datos, dict) else datos
            return [str(w.get("ref") or w.get("id")) for w in filas if isinstance(w, dict) and
                    nombre in (w.get("title"), w.get("name"))]  # fmt: skip
    r = subprocess.run(["cmux", "workspace", "list"], capture_output=True, text=True, timeout=15, check=False)
    patron = re.compile(r"(workspace:\d+)\s+(.*)$")
    refs = []
    for linea in r.stdout.splitlines():
        m = patron.search(linea.strip().lstrip("*").strip())
        if m and re.sub(r"\s*\[.*\]\s*$", "", m.group(2)).strip() == nombre:
            refs.append(m.group(1))
    return refs


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
        viejos = espacios_con_nombre(nombre)
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
    propio = os.environ.get("CMUX_WORKSPACE_ID", "")
    # El espacio desde donde se corre va al final: al cerrarlo, se cierra también esta terminal.
    for ref in sorted(viejos, key=lambda x: x == propio):
        subprocess.run(["cmux", "workspace", "close", ref], capture_output=True, timeout=15, check=False)
    if viejos:
        print(f"cerré {len(viejos)} espacio(s) «{nombre}» anteriores")
    return 0


if __name__ == "__main__":
    sys.exit(main())
