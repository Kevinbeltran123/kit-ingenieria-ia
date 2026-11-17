"""Detector «web» de En vivo: servidores de desarrollo en localhost cuyo cwd cae en una raíz del contexto.

Contrato en references/vivo-contrato.md. Los comandos externos (lsof) van con timeout corto y se pueden reemplazar
al llamar a `detectar` para probar sin lsof real.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

PUERTOS_TABLERO = frozenset({8790, 8791})
COMANDOS = ("node", "vite", "npm", "pnpm", "bun", "python", "deno", "astro", "next", "ruby", "php")
HOSTS = ("127.0.0.1", "localhost", "[::1]", "*", "0.0.0.0")
EXTENSIONES = frozenset({".html", ".css", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".astro"})
SALTAR = frozenset({"node_modules", ".git", "dist", "build", ".next", ".astro", ".venv", "__pycache__"})
TOPE_ENTRADAS = 20000
MAX_ARCHIVOS = 8
TIMEOUT = 1.5


def _lsof(args: list[str]) -> str:
    try:
        r = subprocess.run(["lsof", *args], capture_output=True, text=True, timeout=TIMEOUT, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    return r.stdout


def sockets_escucha() -> list[dict]:
    """Sockets TCP en escucha: [{"pid", "comando", "puerto", "host"}] (parsea el formato -F de lsof)."""
    salida = _lsof(["-nP", "-iTCP", "-sTCP:LISTEN", "-Fpcn"])
    encontrados, pid, comando = [], None, ""
    for linea in salida.splitlines():
        campo, valor = linea[:1], linea[1:]
        if campo == "p":
            pid, comando = (int(valor) if valor.isdigit() else None), ""
        elif campo == "c":
            comando = valor
        elif campo == "n" and pid is not None:
            host, _, puerto = valor.rpartition(":")
            if puerto.isdigit() and host in HOSTS:
                encontrados.append({"pid": pid, "comando": comando, "puerto": int(puerto), "host": host})
    return encontrados


def cwd_de(pid: int) -> str | None:
    """Directorio de trabajo del proceso, o None si no se pudo leer."""
    for linea in _lsof(["-a", "-p", str(pid), "-d", "cwd", "-Fn"]).splitlines():
        if linea.startswith("n") and len(linea) > 1:
            return linea[1:]
    return None


def _es_servidor_web(comando: str) -> bool:
    return comando.lower().startswith(COMANDOS)


def _cambios(raiz: str, desde: float) -> list[tuple[float, str]]:
    """Archivos de código web cambiados desde `desde` bajo `raiz`, el más nuevo primero."""
    pendientes, vistas, hallados = [(raiz, True)], 0, []
    while pendientes and vistas < TOPE_ENTRADAS:
        carpeta, es_raiz = pendientes.pop()
        try:
            with os.scandir(carpeta) as it:
                entradas = list(it)
        except OSError:
            continue
        for e in entradas:
            vistas += 1
            try:
                if e.is_dir(follow_symlinks=False):
                    if e.name not in SALTAR and not (es_raiz and e.name == "wt"):
                        pendientes.append((e.path, False))
                elif Path(e.name).suffix.lower() in EXTENSIONES:
                    t = e.stat().st_mtime
                    if t >= desde:
                        hallados.append((t, e.path))
            except OSError:
                continue
    hallados.sort(reverse=True)
    return hallados


def _raiz_de(cwd: str, raices: list[dict]) -> dict | None:
    """La raíz más específica que contiene a `cwd`."""
    mejor = None
    for r in raices:
        base = Path(r["ruta"])
        p = Path(cwd)
        if (p == base or base in p.parents) and (mejor is None or len(r["ruta"]) > len(mejor["ruta"])):
            mejor = r
    return mejor


def detectar(ctx: dict, escuchar=sockets_escucha, cwd=cwd_de) -> list[dict]:
    """Un producto `web` por servidor de desarrollo cuyo cwd está bajo una raíz del contexto."""
    productos, puertos, cambios = [], set(), {}
    for s in escuchar():
        if s["puerto"] in PUERTOS_TABLERO or s["puerto"] in puertos or not _es_servidor_web(s["comando"]):
            continue
        carpeta = cwd(s["pid"])
        raiz = _raiz_de(carpeta, ctx.get("raices", [])) if carpeta else None
        if raiz is None:
            continue
        puertos.add(s["puerto"])
        if raiz["ruta"] not in cambios:
            cambios[raiz["ruta"]] = _cambios(raiz["ruta"], ctx["desde"])
        hallados = cambios[raiz["ruta"]]
        ultimo = hallados[0][0] if hallados else None
        productos.append({
            "id": f"web:{s['puerto']}",
            "tipo": "web",
            "proyecto": raiz["proyecto"],
            "agente": raiz.get("agente"),
            "t": ultimo or ctx["desde"],
            "titulo": f"{raiz['proyecto']} · {s['puerto']}",
            "datos": {
                "url": f"http://127.0.0.1:{s['puerto']}/",
                "puerto": s["puerto"],
                "cwd": carpeta,
                "ultimo_cambio": ultimo,
                "archivos": [ruta for _, ruta in hallados[:MAX_ARCHIVOS]],
            },
        })  # fmt: skip
    return productos
