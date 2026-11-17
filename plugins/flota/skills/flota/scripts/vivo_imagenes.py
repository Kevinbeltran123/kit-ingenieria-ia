"""Detector de «En vivo»: imágenes nuevas agrupadas por carpeta (producto `imagenes`).

Solo hace `stat` (nunca abre archivos) y recorre cada raíz con tope de profundidad, de entradas y de tiempo.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

EXTENSIONES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
SALTAR = {".git", "node_modules", ".venv", "venv", "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache",
          ".cache", ".tox", ".next", "dist", "build", ".idea"}  # fmt: skip
MAX_ENTRADAS = 20000
MAX_PROFUNDIDAD = 6
MAX_SEGUNDOS = 0.25
RECIENTES = 12


def _recorrer(raiz: Path, saltar: set[str], desde: float, limite: float, vistas: set[str]) -> dict[str, dict]:
    """Por carpeta con imágenes: {"total", "nuevas": [(t, ruta)]}. Salta `saltar` (rutas de otras raíces)."""
    carpetas: dict[str, dict] = {}
    pendientes = [(str(raiz), 0)]
    entradas = 0
    while pendientes and entradas < MAX_ENTRADAS and time.monotonic() < limite:
        ruta, nivel = pendientes.pop()
        if ruta in vistas:
            continue
        vistas.add(ruta)
        try:
            with os.scandir(ruta) as it:
                for e in it:
                    entradas += 1
                    try:
                        if e.is_dir(follow_symlinks=False):
                            if e.name in SALTAR or e.path in saltar or nivel + 1 > MAX_PROFUNDIDAD:
                                continue
                            pendientes.append((e.path, nivel + 1))
                        elif Path(e.name).suffix.lower() in EXTENSIONES and e.is_file(follow_symlinks=False):
                            t = e.stat(follow_symlinks=False).st_mtime
                            c = carpetas.setdefault(ruta, {"total": 0, "nuevas": []})
                            c["total"] += 1
                            if t >= desde:
                                c["nuevas"].append((t, e.path))
                    except OSError:
                        continue
        except OSError:
            continue
    return carpetas


def _miles(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def detectar(ctx: dict) -> list[dict]:
    """Un producto `imagenes` por carpeta con imágenes cambiadas dentro de la ventana."""
    desde = ctx["desde"]
    limite = time.monotonic() + MAX_SEGUNDOS * 4
    raices = ctx.get("raices", [])
    rutas = {r["ruta"] for r in raices}
    corridas = {str(Path(d["run"]).expanduser().resolve()) for d in ctx.get("proyectos", {}).values() if d.get("run")}
    productos, vistas = [], set()
    for r in raices:
        base = r["ruta"]
        saltar = rutas - {base}
        if base in corridas:
            saltar.add(str(Path(base) / "wt"))
        carpetas = _recorrer(Path(base), saltar, desde, limite, vistas)
        for carpeta, c in carpetas.items():
            if not c["nuevas"]:
                continue
            nuevas = sorted(c["nuevas"], reverse=True)
            n = len(nuevas)
            rel = os.path.relpath(carpeta, base)
            nombre = "imagen nueva" if n == 1 else "imágenes nuevas"
            titulo = f"{_miles(n)} {nombre} en {rel if rel != '.' else Path(base).name}"
            if c["total"] > n:
                titulo += f" ({_miles(c['total'])} en total)"
            productos.append({
                "id": f"imagenes:{carpeta}",
                "tipo": "imagenes",
                "proyecto": r["proyecto"],
                "agente": r["agente"],
                "t": nuevas[0][0],
                "titulo": titulo,
                "datos": {"carpeta": carpeta, "total": c["total"], "nuevas": n,
                          "recientes": [ruta for _, ruta in nuevas[:RECIENTES]]},
            })  # fmt: skip
    productos.sort(key=lambda p: p["t"], reverse=True)
    return productos
