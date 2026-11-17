"""Núcleo de «En vivo»: contexto común, detectores con caché y qué archivos se pueden servir.

Contrato completo en references/vivo-contrato.md. Cada detector (vivo_<tipo>.py) expone `detectar(ctx)`; si uno
falla o no existe, los demás siguen.
"""

from __future__ import annotations

import importlib
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
