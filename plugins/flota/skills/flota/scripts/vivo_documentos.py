"""Detector de documentos de «En vivo»: archivos .md y .html que cambian mientras un agente los escribe.

Contrato en references/vivo-contrato.md. Recorre las raíces del contexto con os.scandir, sin entrar en carpetas de
dependencias o cachés, con un tope de entradas para no pasar de unos 300 ms.
"""

from __future__ import annotations

import os
from pathlib import Path

FORMATOS = {".md": "md", ".html": "html"}
SALTAR = frozenset(
    {".git", "node_modules", ".venv", "venv", "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache"}
    | {".cache", ".tox", ".next", ".claude", "dist", "build"}
)
TOPE_ENTRADAS = 20000
TOPE_DOCUMENTOS = 60
TAMANO_MAXIMO = 5 * 1024 * 1024
LECTURA_TITULO = 64 * 1024


def _ruido(nombre: str) -> bool:
    return nombre.upper().startswith("CHANGELOG")


def _lineas(ruta: str) -> int | None:
    try:
        with Path(ruta).open("rb") as f:
            datos = f.read(TAMANO_MAXIMO + 1)
    except OSError:
        return None
    if not datos:
        return 0
    return datos.count(b"\n") + (0 if datos.endswith(b"\n") else 1)


def _encabezado(ruta: str) -> str | None:
    """El primer encabezado `# ` de un .md (fuera de bloques de código), o None."""
    try:
        with Path(ruta).open("rb") as f:
            texto = f.read(LECTURA_TITULO).decode("utf-8", errors="replace")
    except OSError:
        return None
    en_bloque = False
    for linea in texto.splitlines():
        if linea.lstrip().startswith("```"):
            en_bloque = not en_bloque
        elif not en_bloque and linea.startswith("# "):
            return linea[2:].strip() or None
    return None


def _recorrer(raiz: dict, ctx: dict, otras: set[str], estado: dict) -> list[dict]:
    """Documentos cambiados bajo una raíz; `estado` comparte entre raíces las rutas vistas y el presupuesto."""
    encontrados = []
    corridas = {str(Path(d["run"]).expanduser().resolve()) for d in ctx.get("proyectos", {}).values() if d.get("run")}
    pila = [raiz["ruta"]]
    while pila and estado["entradas"] < TOPE_ENTRADAS:
        carpeta = pila.pop()
        try:
            with os.scandir(carpeta) as it:
                for e in it:
                    estado["entradas"] += 1
                    if estado["entradas"] > TOPE_ENTRADAS:
                        break
                    try:
                        if e.is_dir(follow_symlinks=False):
                            if e.name in SALTAR or e.path in otras:
                                continue
                            if e.name == "wt" and carpeta in corridas:
                                continue
                            pila.append(e.path)
                            continue
                        formato = FORMATOS.get(Path(e.name).suffix.lower())
                        if not formato or _ruido(e.name) or e.path in estado["vistas"]:
                            continue
                        st = e.stat(follow_symlinks=False)
                    except OSError:
                        continue
                    if st.st_mtime < ctx["desde"] or st.st_size > TAMANO_MAXIMO:
                        continue
                    estado["vistas"].add(e.path)
                    encontrados.append((e.path, e.name, formato, st))
        except OSError:
            continue
    return encontrados


def detectar(ctx: dict) -> list[dict]:
    estado = {"entradas": 0, "vistas": set()}
    rutas_raices = {r["ruta"] for r in ctx.get("raices", [])}
    candidatos = []
    for raiz in ctx.get("raices", []):
        otras = rutas_raices - {raiz["ruta"]}
        candidatos += [(raiz, *c) for c in _recorrer(raiz, ctx, otras, estado)]
    candidatos.sort(key=lambda c: c[4].st_mtime, reverse=True)
    productos = []
    for raiz, ruta, nombre, formato, st in candidatos[:TOPE_DOCUMENTOS]:
        lineas = _lineas(ruta)
        if lineas is None:
            continue
        encabezado = _encabezado(ruta) if formato == "md" else None
        productos.append(
            {
                "id": "documento:" + ruta,
                "tipo": "documento",
                "proyecto": raiz["proyecto"],
                "agente": raiz["agente"],
                "t": st.st_mtime,
                "titulo": f"{nombre}: {encabezado}" if encabezado else nombre,
                "datos": {"archivo": ruta, "formato": formato, "tamano": st.st_size, "lineas": lineas},
            }
        )
    return productos
