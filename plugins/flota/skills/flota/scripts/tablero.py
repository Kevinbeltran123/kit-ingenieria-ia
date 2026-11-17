"""Tablero de la flota: una página local e interactiva (o una vista de terminal) con todo lo que pasa en la corrida.

Uso:
  tablero.py --run DIR --sesion S [--repo REPO] [--puerto N] [--abrir]   servidor web en 127.0.0.1
  tablero.py --run DIR --sesion S [--repo REPO] --terminal [--intervalo 5]  vista de terminal que se redibuja

La página muestra los carriles por columna de flujo (trabajando, te espera, quieto, listo, puerta, enviado), la línea de
tiempo de estados (de los eventos que registra el puente de herdr), la bitácora, la puerta y las entregas. Desde ella se
lee la pantalla de un carril, se le escribe, se le mandan teclas para responder un diálogo y se enfoca en herdr.
Escucha solo en 127.0.0.1 y pide el token que imprime al arrancar (va en la URL); --abrir la abre en cmux.
"""

from __future__ import annotations

import argparse
import contextlib
import hmac
import json
import mimetypes
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import (
    TECLAS,
    HerdrError,
    agentes,
    bitacora,
    cargar_carriles,
    eventos,
    herdr,
    lineas_listo,
    pantalla,
    puerta,
)

AQUI = Path(__file__).resolve().parent
COLUMNAS = ("trabajando", "espera", "quieto", "listo", "puerta", "enviado")
_cache_git: dict[str, tuple[float, dict]] = {}


def info_git(repo: str | None) -> dict:
    """Rama, head y últimos commits del repo; se guarda 10 s para no correr git en cada consulta."""
    if not repo:
        return {}
    ahora = time.time()
    if repo in _cache_git and ahora - _cache_git[repo][0] < 10:
        return _cache_git[repo][1]

    def g(*args: str) -> str:
        r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, timeout=10, check=False)
        return r.stdout.strip() if r.returncode == 0 else ""

    datos = {
        "rama": g("branch", "--show-current"),
        "head": g("rev-parse", "--short", "HEAD"),
        "commits": [linea for linea in g("log", "--oneline", "-6").splitlines() if linea],
        "worktrees": max(
            0, len([x for x in g("worktree", "list", "--porcelain").splitlines() if x.startswith("worktree ")]) - 1
        ),
    }
    _cache_git[repo] = (ahora, datos)
    return datos


def columna(c: dict, vivo: str | None, *, listo: bool, en_puerta: bool) -> str:
    if c.get("estado") == "enviado":
        return "enviado"
    if c.get("estado") == "gate" or en_puerta:
        return "puerta"
    if listo:
        return "listo"
    if vivo == "blocked":
        return "espera"
    if vivo == "working":
        return "trabajando"
    return "quieto"


def estado(run: Path, sesion: str, repo: str | None) -> dict:
    carriles = cargar_carriles(run)
    vivos = {ag.get("name") or ag.get("pane_id"): ag for ag in agentes(sesion)}
    entregas = lineas_listo(run)
    seccion_puerta = puerta(run)
    # Un carril está en la puerta si alguna línea lo nombra sin FAIL; con FAIL vuelve a su columna para corregirse.
    texto_puerta = " ".join(linea for v in seccion_puerta.values() for linea in v if "FAIL" not in linea).lower()
    evs = eventos(sesion)
    desde: dict[str, float] = {}
    for e in evs:
        clave = e.get("nombre") or e.get("pane")
        if clave:
            desde[clave] = e.get("t", 0)
    listos = {e["carril"]: e for e in entregas if e["tipo"] == "listo"}
    filas = []
    for nombre, c in carriles.items():
        ag = vivos.get(nombre)
        vivo = ag.get("agent_status") if ag else None
        en_puerta = bool(re.search(rf"(?<![a-z0-9-]){re.escape(nombre)}(?![a-z0-9-])", texto_puerta))
        filas.append(
            {
                **c,
                "vivo": vivo or ("cerrado" if c.get("estado") == "cerrado" else "fuera"),
                "pane_actual": ag.get("pane_id") if ag else None,
                "columna": columna(c, vivo, listo=nombre in listos, en_puerta=en_puerta),
                "listo": listos.get(nombre),
                "desde": desde.get(nombre),
            }
        )
    otros = [
        {
            "nombre": k,
            "agente": ag.get("agent"),
            "vivo": ag.get("agent_status"),
            "pane": ag.get("pane_id"),
            "cwd": ag.get("cwd"),
            "desde": desde.get(k),
        }
        for k, ag in vivos.items()
        if k not in carriles
    ]
    resumen = {col: sum(1 for f in filas if f["columna"] == col) for col in COLUMNAS}
    return {
        "sesion": sesion,
        "run": str(run),
        "ahora": time.time(),
        "servidor_herdr": bool(vivos) or _servidor_vivo(sesion),
        "carriles": filas,
        "otros": otros,
        "resumen": resumen,
        "entregas": entregas,
        "puerta": seccion_puerta,
        "bitacora": bitacora(run, 40),
        "eventos": evs,
        "git": info_git(repo),
    }


def _servidor_vivo(sesion: str) -> bool:
    try:
        herdr(sesion, "workspace", "list", timeout=5)
        return True
    except HerdrError:
        return False


def archivo_permitido(run: Path, carril: dict | None, cual: str, nombre: str) -> Path | None:
    if cual == "brief" and carril and carril.get("brief"):
        return Path(carril["brief"])
    if cual in ("handover", "review"):
        return run / f"{cual}-{nombre}.md"
    if cual == "state":
        return run / "STATE.md"
    if cual == "common":
        return run / "common.md"
    return None


class Tablero(BaseHTTPRequestHandler):
    server_version = "flota-tablero"
    ctx: ClassVar[dict] = {}

    def log_message(self, *_: object) -> None:  # silencio: el tablero consulta cada 2 s
        return

    # --- respuestas -------------------------------------------------------------------------------------------
    def _enviar(self, codigo: int, cuerpo: bytes, tipo: str) -> None:
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(cuerpo)

    def _json(self, codigo: int, datos: object) -> None:
        self._enviar(codigo, json.dumps(datos, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _host_valido(self) -> bool:
        puerto = self.server.server_address[1]
        return self.headers.get("Host", "") in (f"127.0.0.1:{puerto}", f"localhost:{puerto}")

    def _token_valido(self, consulta: dict) -> bool:
        dado = self.headers.get("X-Flota-Token") or (consulta.get("t") or [""])[0]
        return hmac.compare_digest(dado.encode(), self.ctx["token"].encode())

    # --- GET --------------------------------------------------------------------------------------------------
    def do_GET(self) -> None:
        url = urlparse(self.path)
        q = parse_qs(url.query)
        if not self._host_valido():
            return self._json(403, {"error": "host no permitido"})
        if url.path.startswith("/fuentes/"):
            ruta = AQUI / "fuentes" / Path(url.path).name
            if ruta.suffix == ".woff2" and ruta.is_file():
                return self._enviar(200, ruta.read_bytes(), "font/woff2")
            return self._json(404, {"error": "no existe"})
        if not self._token_valido(q):
            return self._enviar(
                403,
                "Abre la URL completa que imprimió tablero.py (lleva ?t=...).".encode(),
                "text/plain; charset=utf-8",
            )
        run, sesion = self.ctx["run"], self.ctx["sesion"]
        if url.path == "/":
            return self._enviar(200, (AQUI / "tablero.html").read_bytes(), "text/html; charset=utf-8")
        if url.path == "/api/estado":
            return self._json(200, estado(run, sesion, self.ctx.get("repo")))
        if url.path == "/api/leer":
            nombre = (q.get("nombre") or [""])[0]
            if not self._nombre_conocido(nombre):
                return self._json(404, {"error": f"no hay agente {nombre}"})
            lineas = min(400, max(20, int((q.get("lineas") or ["120"])[0] or 120)))
            try:
                texto = pantalla(sesion, nombre, "recent-unwrapped", lineas)
            except HerdrError as e:
                return self._json(409, {"error": str(e)})
            return self._json(200, {"texto": texto.rstrip()})
        if url.path == "/api/archivo":
            nombre, cual = (q.get("nombre") or [""])[0], (q.get("cual") or [""])[0]
            carril = cargar_carriles(run).get(nombre)
            ruta = archivo_permitido(run, carril, cual, nombre)
            if not ruta or not ruta.is_file():
                return self._json(404, {"error": "todavía no existe"})
            return self._json(
                200, {"ruta": str(ruta), "texto": ruta.read_text(encoding="utf-8", errors="replace")[-60000:]}
            )
        return self._json(404, {"error": "ruta desconocida"})

    def _nombre_conocido(self, nombre: str) -> bool:
        if nombre in cargar_carriles(self.ctx["run"]):
            return True
        return any(ag.get("name") == nombre for ag in agentes(self.ctx["sesion"]))

    # --- POST -------------------------------------------------------------------------------------------------
    def do_POST(self) -> None:
        url = urlparse(self.path)
        if not self._host_valido() or not self.headers.get("X-Flota-Token") or not self._token_valido({}):
            return self._json(403, {"error": "token o host inválido"})
        if not self.headers.get("Content-Type", "").startswith("application/json"):
            return self._json(415, {"error": "se espera JSON"})
        origen = self.headers.get("Origin")
        if origen and urlparse(origen).netloc != self.headers.get("Host"):
            return self._json(403, {"error": "origen no permitido"})
        try:
            largo = min(int(self.headers.get("Content-Length", "0")), 64_000)
            datos = json.loads(self.rfile.read(largo) or b"{}")
        except ValueError:
            return self._json(400, {"error": "JSON inválido"})
        nombre = str(datos.get("nombre", ""))
        if not self._nombre_conocido(nombre):
            return self._json(404, {"error": f"no hay agente {nombre}"})
        sesion = self.ctx["sesion"]
        try:
            if url.path == "/api/enviar":
                texto = str(datos.get("texto", "")).strip()
                if not texto:
                    return self._json(400, {"error": "texto vacío"})
                herdr(sesion, "agent", "prompt", nombre, texto, timeout=20)
            elif url.path == "/api/teclas":
                tecla = str(datos.get("tecla", ""))
                if tecla not in TECLAS:
                    return self._json(400, {"error": f"tecla no permitida: {tecla}"})
                herdr(sesion, "agent", "send-keys", nombre, tecla)
            elif url.path == "/api/enfocar":
                herdr(sesion, "agent", "focus", nombre)
            else:
                return self._json(404, {"error": "ruta desconocida"})
        except HerdrError as e:
            return self._json(409, {"error": str(e)})
        return self._json(200, {"ok": True})


# --- vista de terminal --------------------------------------------------------------------------------------------
COLOR = {"trabajando": "34", "espera": "31", "quieto": "33", "listo": "32", "puerta": "35", "enviado": "36"}
TITULO = {
    "trabajando": "Trabajando",
    "espera": "Te espera",
    "quieto": "Quieto",
    "listo": "Listo",
    "puerta": "Puerta",
    "enviado": "Enviado",
}


def hace(t: float | None, ahora: float) -> str:
    if not t:
        return ""
    s = int(ahora - t)
    return f"{s}s" if s < 60 else f"{s // 60}m" if s < 3600 else f"{s // 3600}h{(s % 3600) // 60:02d}"


def vista_terminal(d: dict) -> str:
    ahora = d["ahora"]
    salida = [f"\033[1mFlota · {d['sesion']}\033[0m  {time.strftime('%H:%M:%S')}  {d['run']}"]
    if d.get("git"):
        g = d["git"]
        salida.append(f"repo: {g.get('rama')} @ {g.get('head')} · {g.get('worktrees', 0)} worktrees")
    if not d["servidor_herdr"]:
        salida.append("\033[31mherdr: la sesión no está corriendo\033[0m")
    salida.append("  ".join(f"\033[{COLOR[c]}m● {TITULO[c]} {d['resumen'][c]}\033[0m" for c in COLUMNAS))
    salida.append("")
    for f in sorted(d["carriles"], key=lambda x: COLUMNAS.index(x["columna"])):
        col = f["columna"]
        listo = f["listo"]["resto"] if f.get("listo") else ""
        salida.append(
            f"  \033[{COLOR[col]}m{TITULO[col]:<11}\033[0m {f['nombre']:<16} {f['tipo']:<6} "
            f"{f.get('modelo') or '-'!s:<18} {hace(f.get('desde'), ahora):>6}  {listo}"
        )
    salida += [
        f"  \033[2m{'otro':<11}\033[0m {o['nombre']:<16} {o.get('agente') or '':<6} {o.get('vivo')}" for o in d["otros"]
    ]
    if d["bitacora"]:
        salida += ["", "\033[1mBitácora\033[0m"] + [f"  {linea[:150]}" for linea in d["bitacora"][-6:]]
    return "\n".join(salida)


def abrir_en_cmux(url: str) -> bool:
    exe = shutil.which("cmux")
    if not exe or not os.environ.get("CMUX_WORKSPACE_ID"):
        return False
    r = subprocess.run([exe, "open", url], capture_output=True, timeout=10, check=False)
    return r.returncode == 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run", required=True)
    p.add_argument("--sesion", required=True)
    p.add_argument("--repo")
    p.add_argument("--puerto", type=int, default=0)
    p.add_argument("--abrir", action="store_true")
    p.add_argument("--terminal", action="store_true")
    p.add_argument("--intervalo", type=float, default=5)
    a = p.parse_args(argv)
    run = Path(a.run).expanduser().resolve()
    repo = str(Path(a.repo).expanduser().resolve()) if a.repo else None
    if a.terminal:
        try:
            while True:
                print("\033[2J\033[H" + vista_terminal(estado(run, a.sesion, repo)), flush=True)
                time.sleep(a.intervalo)
        except KeyboardInterrupt:
            return 0
    mimetypes.add_type("font/woff2", ".woff2")
    Tablero.ctx = {"run": run, "sesion": a.sesion, "repo": repo, "token": secrets.token_urlsafe(18)}
    servidor = ThreadingHTTPServer(("127.0.0.1", a.puerto), Tablero)
    url = f"http://127.0.0.1:{servidor.server_address[1]}/?t={Tablero.ctx['token']}"
    run.mkdir(parents=True, exist_ok=True)
    # La URL lleva el token: solo el dueño puede leer el archivo.
    fd = os.open(run / ".tablero-url", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(url + "\n")
    (run / ".tablero-url").chmod(0o600)
    print(f"tablero de la flota en {url}  (Ctrl+C para pararlo)", flush=True)
    if a.abrir and not abrir_en_cmux(url):
        print("no se pudo abrir en cmux: abre la URL de arriba en el navegador", flush=True)
    with contextlib.suppress(KeyboardInterrupt):
        servidor.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
