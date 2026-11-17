"""Núcleo de «En vivo»: contexto común, detectores con caché y qué archivos se pueden servir.

Contrato completo en references/vivo-contrato.md. Cada detector (vivo_<tipo>.py) expone `detectar(ctx)`; si uno
falla o no existe, los demás siguen.
"""

from __future__ import annotations

import importlib
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import agentes, cargar_carriles, corridas

DETECTORES = ("vivo_registro", "vivo_imagenes", "vivo_metricas", "vivo_web", "vivo_documentos")
EXTENSIONES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".md": "text/markdown; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".csv": "text/csv; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".log": "text/plain; charset=utf-8",
    ".html": "text/html; charset=utf-8",
}
VENTANA = 3600.0
TTL = 4.0
_cache: dict[str, tuple[float, list[dict]]] = {}


def contexto(sesion: str, proyectos: dict[str, dict] | None = None, ventana: float = VENTANA) -> dict:
    """Proyectos, agentes conocidos y raíces a vigilar, sin repetir."""
    proyectos = proyectos if proyectos is not None else corridas()
    ahora = time.time()
    lista_agentes, raices, vistas = [], [], set()

    def raiz(ruta: str | None, proyecto: str, agente: str | None) -> None:
        if not ruta:
            return
        real = str(Path(ruta).expanduser().resolve())
        if real in vistas or not Path(real).is_dir():
            return
        vistas.add(real)
        raices.append({"ruta": real, "proyecto": proyecto, "agente": agente})

    for nombre, d in proyectos.items():
        run = d.get("run")
        for c in cargar_carriles(Path(run)).values() if run else []:
            lista_agentes.append({"nombre": c.get("nombre"), "proyecto": nombre, "cwd": c.get("worktree"),
                                  "sesion_agente": c.get("sesion_agente"), "tipo": c.get("tipo")})  # fmt: skip
            raiz(c.get("worktree"), nombre, c.get("nombre"))
        raiz(d.get("repo"), nombre, None)
        raiz(run, nombre, None)
    conocidos = {a["nombre"] for a in lista_agentes}
    for ag in agentes(sesion):
        nombre = ag.get("name")
        if not nombre or nombre in conocidos:
            continue
        cwd = ag.get("cwd")
        proyecto = next((p for p, d in proyectos.items() if cwd and (cwd == d.get("repo") or
                         cwd.startswith(str(d.get("repo", "")).rstrip("/") + "/"))), None)  # fmt: skip
        lista_agentes.append({"nombre": nombre, "proyecto": proyecto, "cwd": cwd, "sesion_agente": None,
                              "tipo": ag.get("agent")})  # fmt: skip
    return {"ahora": ahora, "desde": ahora - ventana, "proyectos": proyectos, "agentes": lista_agentes,
            "raices": raices}  # fmt: skip


def recolectar(ctx: dict) -> dict:
    """Llama a cada detector (con caché de TTL segundos) y devuelve los productos ordenados por último cambio."""
    productos, errores = [], {}
    for nombre in DETECTORES:
        guardado = _cache.get(nombre)
        if guardado and ctx["ahora"] - guardado[0] < TTL:
            productos += guardado[1]
            continue
        try:
            modulo = importlib.import_module(nombre)
            encontrados = [p for p in modulo.detectar(ctx) if isinstance(p, dict) and p.get("id")]
        except ModuleNotFoundError:
            encontrados = []
        except Exception as e:  # un detector roto no tumba la página
            errores[nombre] = f"{type(e).__name__}: {e}"[:200]
            encontrados = []
        _cache[nombre] = (ctx["ahora"], encontrados)
        productos += encontrados
    productos.sort(key=lambda p: p.get("t") or 0, reverse=True)
    return {"ahora": ctx["ahora"], "productos": productos, "errores": errores}


def ruta_permitida(ruta: str, ctx: dict) -> Path | None:
    """La ruta, si está bajo una raíz del contexto y tiene una extensión que se puede servir; si no, None."""
    try:
        real = Path(ruta).expanduser().resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    if real.suffix.lower() not in EXTENSIONES or not real.is_file():
        return None
    for r in ctx.get("raices", []):
        base = Path(r["ruta"])
        if real == base or base in real.parents:
            return real
    return None


# --- Vista por carril (portada en tarjetas) -----------------------------------------------------------------------
VISUALES = ("web", "metricas", "imagenes")  # lo que se ve; los documentos de texto los lee el coordinador
ACTIVOS = ("working", "blocked")
RECIENTE = 900.0  # un producto de un carril activo cuenta si cambió en los últimos 15 min
AHORA_MISMO = 180.0  # lo que no lanzó un agente (pueue, una página tuya) cuenta solo si cambia en estos 3 min
IMAGEN = (".png", ".jpg", ".jpeg", ".webp", ".gif")


def _relativa_en(texto: str, ruta: str, raices: list[dict]) -> bool:
    """¿Algún comando del agente nombra esta carpeta (ruta absoluta o relativa a una raíz)?"""
    if ruta in texto:
        return True
    for r in raices:
        base = r["ruta"].rstrip("/") + "/"
        if ruta.startswith(base) and ruta[len(base) :] in texto:
            return True
    return False


def ruido(producto: dict, raices: list[dict]) -> bool:
    """Archivos de carpetas ocultas o de caché (README de una caché, HTML de .explicaciones): no son un producto."""
    datos = producto.get("datos") or {}
    ruta = datos.get("archivo") or datos.get("carpeta")
    if not ruta:
        return False
    base = next((r["ruta"] for r in raices if str(ruta).startswith(r["ruta"].rstrip("/") + "/")), None)
    partes = Path(str(ruta)[len(base) + 1 :] if base else str(ruta)).parts[:-1]
    return any(p.startswith(".") or "cache" in p.lower() for p in partes)


def agrupar(ctx: dict, productos: list[dict], estados: dict[str, str]) -> dict:
    """Productos visibles agrupados por carril; fuera lo que ningún agente de la flota produjo.

    Solo carriles con agente activo (trabajando o esperando a la persona) y solo producto visual reciente: lo que no
    está en marcha no aparece.
    - imagenes: cuentan si están en el worktree de un agente o si el agente las escribió o nombró en un comando.
    - metricas: si están en un worktree, o si un comando del agente nombra su carpeta; las de pueue van al proyecto.
    - web: el servidor de un worktree va con su agente; uno del repo (lo levantó la persona) va al proyecto.
    - codigo: no es tarjeta; es la lista de archivos que tocó el carril. comando: no se muestra.
    """
    escritos = {
        p["datos"].get("archivo"): p["agente"] for p in productos if p.get("tipo") == "codigo" and p.get("agente")
    }
    comandos = [
        (p["agente"], p["datos"].get("comando", ""))
        for p in productos
        if p.get("tipo") == "comando" and p.get("agente")
    ]
    proyecto_de = {a["nombre"]: a.get("proyecto") for a in ctx.get("agentes", [])}
    carriles: dict[str, dict] = {}
    proyecto_suelto: list[dict] = []

    def carril(nombre: str) -> dict:
        if nombre not in carriles:
            carriles[nombre] = {"nombre": nombre, "proyecto": proyecto_de.get(nombre), "estado": estados.get(nombre),
                                "productos": [], "archivos": []}  # fmt: skip
        return carriles[nombre]

    for p in productos:
        tipo, datos = p.get("tipo"), p.get("datos") or {}
        agente = p.get("agente")
        if tipo == "codigo" and agente:
            carril(agente)["archivos"].append({"archivo": datos.get("archivo"), "mas": datos.get("mas"),
                                               "menos": datos.get("menos"), "t": p.get("t")})  # fmt: skip
            continue
        if tipo not in VISUALES or ruido(p, ctx["raices"]):
            continue
        if not agente and tipo == "imagenes":
            carpeta = datos.get("carpeta", "")
            agente = next((a for f, a in escritos.items() if f and str(f).startswith(carpeta.rstrip("/") + "/")), None)
            agente = agente or next(
                (a for a, c in comandos if carpeta and _relativa_en(c, carpeta, ctx["raices"])), None
            )
        if not agente and tipo == "metricas" and datos.get("archivo"):
            carpeta = str(Path(datos["archivo"]).parent)
            agente = next((a for a, c in comandos if _relativa_en(c, carpeta, ctx["raices"])), None)
        edad = ctx["ahora"] - (p.get("t") or 0)
        if agente:
            if estados.get(agente) in ACTIVOS and (tipo == "web" or edad <= RECIENTE):
                carril(agente)["productos"].append(p)
        elif tipo in ("web", "metricas") and p.get("proyecto"):
            cambio = datos.get("ultimo_cambio") if tipo == "web" else p.get("t")
            if cambio and ctx["ahora"] - cambio <= AHORA_MISMO:
                proyecto_suelto.append(p)
    for c in carriles.values():
        webs = [str(p["datos"].get("cwd") or "") for p in c["productos"] if p.get("tipo") == "web"]
        if webs:  # el HTML de una página que ya se ve en vivo no se repite como documento
            c["productos"] = [
                p
                for p in c["productos"]
                if not (
                    p.get("tipo") == "documento"
                    and str(p["datos"].get("archivo", "")).endswith(".html")
                    and any(w and str(p["datos"]["archivo"]).startswith(w) for w in webs)
                )
            ]
        c["productos"].sort(key=lambda p: p.get("t") or 0, reverse=True)
        c["archivos"].sort(key=lambda a: a.get("t") or 0, reverse=True)
        c["principal"] = c["productos"][0]["id"] if c["productos"] else None
        c["t"] = max([p.get("t") or 0 for p in c["productos"]] + [a.get("t") or 0 for a in c["archivos"]] + [0])
    visibles = [c for c in carriles.values() if c["principal"]]  # un carril sin nada visual en marcha no se muestra
    activos = sum(1 for n, e in estados.items() if e in ACTIVOS and n in proyecto_de)
    orden = sorted(visibles, key=lambda c: -(c["t"] or 0))
    return {
        "ahora": ctx["ahora"],
        "carriles": orden,
        "proyecto": proyecto_suelto,
        "activos": activos,
        "esperan": sorted(n for n, e in estados.items() if e == "blocked"),
    }


def imagenes_de(carpeta: str, ctx: dict, tope: int = 240) -> list[dict]:
    """Las imágenes más recientes de una carpeta permitida, con su hora, para la rejilla grande."""
    base = Path(carpeta).expanduser()
    try:
        real = base.resolve(strict=True)
    except (OSError, RuntimeError):
        return []
    if not any(real == Path(r["ruta"]) or Path(r["ruta"]) in real.parents for r in ctx.get("raices", [])):
        return []
    try:
        with os.scandir(real) as it:
            salida = [{"ruta": str(real / e.name), "t": e.stat().st_mtime} for e in it
                      if e.is_file() and e.name.lower().endswith(IMAGEN)]  # fmt: skip
    except OSError:
        return []
    salida.sort(key=lambda x: x["t"], reverse=True)
    return salida[:tope]
