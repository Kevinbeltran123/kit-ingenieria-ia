"""Tablero de la flota: una página local e interactiva (o una vista de terminal) con todos los proyectos y sus carriles.

Uso:
  tablero.py --sesion S [--puerto N] [--abrir]            todos los proyectos registrados (los registra carril.py)
  tablero.py --sesion S --terminal [--intervalo 5]        la misma vista en la terminal
  tablero.py --sesion S --run DIR --repo REPO [...]       solo una corrida

La página agrupa por proyecto: carriles por columna de flujo (trabajando, te espera, quieto, listo, puerta, enviado),
línea de tiempo de estados (de los eventos del puente de herdr), entregas, puerta y bitácora. Desde ella se lee la
pantalla de un carril, se le escribe, se le mandan teclas, se enfoca en herdr y se arranca el coordinador de un
proyecto. Escucha solo en 127.0.0.1 y pide el token que imprime al arrancar (va en la URL); --abrir la abre en cmux.
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
import threading
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
    corridas,
    eventos,
    herdr,
    lineas_listo,
    nombre_proyecto,
    pantalla,
    puerta,
)

AQUI = Path(__file__).resolve().parent
ESTADO_FLOTA = Path.home() / ".local" / "state" / "flota"
PUERTO_FIJO = 8790
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

    arboles = [x for x in g("worktree", "list", "--porcelain").splitlines() if x.startswith("worktree ")]
    datos = {
        "rama": g("branch", "--show-current"),
        "head": g("rev-parse", "--short", "HEAD"),
        "commits": [linea for linea in g("log", "--oneline", "-4").splitlines() if linea],
        "worktrees": max(0, len(arboles) - 1),
    }
    _cache_git[repo] = (ahora, datos)
    return datos


def resumir_macmon(m: dict) -> dict:
    """Lo que el tablero muestra en una línea: uso de CPU y GPU, memoria, potencia y temperatura."""
    mem = m.get("memory") or {}
    temp = m.get("temp") or {}
    gib = 1024**3
    return {
        "cpu": round(100 * (m.get("cpu_usage_pct") or 0)),
        "gpu": round(100 * (m.get("gpu_active_ratio") or 0)),
        "ram": round((mem.get("ram_usage") or 0) / gib, 1),
        "ram_total": round((mem.get("ram_total") or 0) / gib),
        "swap": round((mem.get("swap_usage") or 0) / gib, 1),
        "presion": mem.get("pressure_percent"),
        "w": round(m.get("all_power") or 0, 1),
        "temp_cpu": round(temp.get("cpu_temp_avg") or 0),
        "temp_gpu": round(temp.get("gpu_temp_avg") or 0),
    }


class Monitor(threading.Thread):
    """Lee `macmon pipe` en segundo plano y guarda la última muestra; sin macmon, el tablero no muestra la línea."""

    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.ultimo: dict | None = None

    def run(self) -> None:
        exe = shutil.which("macmon")
        if not exe:
            return
        try:
            proc = subprocess.Popen(
                [exe, "pipe", "-i", "2000"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
            )
        except OSError:
            return
        for linea in proc.stdout or []:
            with contextlib.suppress(ValueError, TypeError, AttributeError):
                self.ultimo = {**resumir_macmon(json.loads(linea)), "t": time.time()}


MONITOR: Monitor | None = None


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


def proyecto_de(cwd: str | None, proyectos: dict[str, dict]) -> str | None:
    """Proyecto al que pertenece una carpeta (el repo o la corrida con sus worktrees)."""
    if not cwd:
        return None
    for nombre, d in proyectos.items():
        for raiz in (d.get("repo"), d.get("run")):
            if raiz and (cwd == raiz or cwd.startswith(raiz.rstrip("/") + "/")):
                return nombre
    return None


def estado(proyectos: dict[str, dict], sesion: str) -> dict:
    """Todo lo que muestra el tablero, de todos los proyectos, en un solo diccionario."""
    vivos = {ag.get("name") or ag.get("pane_id"): ag for ag in agentes(sesion)}
    evs = eventos(sesion)
    desde: dict[str, float] = {}
    for e in evs:
        clave = e.get("nombre") or e.get("pane")
        if clave:
            desde[clave] = e.get("t", 0)
    filas, entregas, lineas_bitacora, info = [], [], [], []
    puertas: dict[str, dict] = {}
    for proyecto, d in proyectos.items():
        run = Path(d["run"])
        carriles = cargar_carriles(run)
        propias = [{**e, "proyecto": proyecto} for e in lineas_listo(run)]
        entregas += propias
        puertas[proyecto] = puerta(run)
        # Un carril está en la puerta si alguna línea lo nombra sin FAIL; con FAIL vuelve a su columna.
        texto_puerta = " ".join(x for v in puertas[proyecto].values() for x in v if "FAIL" not in x).lower()
        listos = {e["carril"]: e for e in propias if e["tipo"] == "listo"}
        for nombre, c in carriles.items():
            ag = vivos.get(nombre)
            vivo = ag.get("agent_status") if ag else None
            en_puerta = bool(re.search(rf"(?<![a-z0-9-]){re.escape(nombre)}(?![a-z0-9-])", texto_puerta))
            filas.append({
                **c,
                "proyecto": proyecto,
                "vivo": vivo or ("cerrado" if c.get("estado") == "cerrado" else "fuera"),
                "pane_actual": ag.get("pane_id") if ag else None,
                "columna": columna(c, vivo, listo=nombre in listos, en_puerta=en_puerta),
                "listo": listos.get(nombre),
                "desde": desde.get(nombre),
            })  # fmt: skip
        lineas_bitacora += [(x[:16], f"{proyecto} · {x[17:]}", x) for x in bitacora(run, 40)]
        coord = vivos.get(f"coord-{proyecto}"[:32])
        info.append({
            "nombre": proyecto, "repo": d.get("repo"), "run": str(run), "git": info_git(d.get("repo")),
            "coordinador": coord.get("agent_status") if coord else None,
        })  # fmt: skip
    de_carril = {f["nombre"] for f in filas}
    coord_de = {f"coord-{p}"[:32]: p for p in proyectos}
    otros = [
        {"nombre": k, "agente": ag.get("agent"), "vivo": ag.get("agent_status"), "pane": ag.get("pane_id"),
         "cwd": ag.get("cwd"), "desde": desde.get(k),
         "proyecto": coord_de.get(k) or proyecto_de(ag.get("cwd"), proyectos)}
        for k, ag in vivos.items() if k not in de_carril
    ]  # fmt: skip
    for p in info:
        p["resumen"] = {
            col: sum(1 for f in filas if f["proyecto"] == p["nombre"] and f["columna"] == col) for col in COLUMNAS
        }
    lineas_bitacora.sort(key=lambda x: x[0])
    return {
        "sesion": sesion,
        "ahora": time.time(),
        "servidor_herdr": bool(vivos) or _servidor_vivo(sesion),
        "proyectos": info,
        "carriles": filas,
        "otros": otros,
        "resumen": {col: sum(1 for f in filas if f["columna"] == col) for col in COLUMNAS},
        "entregas": entregas,
        "puerta": puertas,
        "bitacora": [f"{x[0]} {x[1]}" for x in lineas_bitacora[-40:]],
        "eventos": evs,
        "sistema": MONITOR.ultimo if MONITOR else None,
    }


def _servidor_vivo(sesion: str) -> bool:
    try:
        herdr(sesion, "workspace", "list", timeout=5)
        return True
    except HerdrError:
        return False


def buscar_carril(proyectos: dict[str, dict], nombre: str) -> tuple[Path, dict] | None:
    for d in proyectos.values():
        run = Path(d["run"])
        c = cargar_carriles(run).get(nombre)
        if c:
            return run, c
    return None


def archivo_permitido(run: Path, carril: dict | None, cual: str, nombre: str) -> Path | None:
    if cual == "brief" and carril and carril.get("brief"):
        return Path(carril["brief"])
    if cual in ("handover", "review"):
        return run / f"{cual}-{nombre}.md"
    return None


class Tablero(BaseHTTPRequestHandler):
    server_version = "flota-tablero"
    ctx: ClassVar[dict] = {}

    def log_message(self, *_: object) -> None:  # silencio: el tablero consulta cada 2 s
        return

    def proyectos(self) -> dict[str, dict]:
        """La corrida fija de --run, o el registro (se relee: un proyecto nuevo aparece sin reiniciar)."""
        return self.ctx.get("fijos") or corridas()

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

    def _nombre_conocido(self, nombre: str) -> bool:
        if buscar_carril(self.proyectos(), nombre):
            return True
        return any(ag.get("name") == nombre for ag in agentes(self.ctx["sesion"]))

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
            aviso = "Abre la URL completa que imprimió tablero.py (lleva ?t=...)."
            return self._enviar(403, aviso.encode(), "text/plain; charset=utf-8")
        sesion = self.ctx["sesion"]
        if url.path == "/":
            return self._enviar(200, (AQUI / "tablero.html").read_bytes(), "text/html; charset=utf-8")
        if url.path == "/api/estado":
            return self._json(200, estado(self.proyectos(), sesion))
        if url.path == "/api/leer":
            nombre = (q.get("nombre") or [""])[0]
            if not self._nombre_conocido(nombre):
                return self._json(404, {"error": f"no hay agente {nombre}"})
            # Lo visible no mueve nada. El historial hace que herdr desplace la pantalla del agente para recogerlo
            # (la terminal salta), así que solo se pide cuando la persona lo pide, nunca en la consulta periódica.
            historial = (q.get("historial") or [""])[0] == "1"
            lineas = min(400, max(20, int((q.get("lineas") or ["200"])[0] or 200)))
            try:
                if historial:
                    texto = pantalla(sesion, nombre, "recent-unwrapped", lineas)
                else:
                    texto = pantalla(sesion, nombre, "visible")
            except HerdrError as e:
                return self._json(409, {"error": str(e)})
            return self._json(200, {"texto": texto.rstrip()})
        if url.path == "/api/archivo":
            nombre, cual = (q.get("nombre") or [""])[0], (q.get("cual") or [""])[0]
            hallado = buscar_carril(self.proyectos(), nombre)
            ruta = archivo_permitido(hallado[0], hallado[1], cual, nombre) if hallado else None
            if not ruta or not ruta.is_file():
                return self._json(404, {"error": "todavía no existe"})
            texto = ruta.read_text(encoding="utf-8", errors="replace")[-60000:]
            return self._json(200, {"ruta": str(ruta), "texto": texto})
        return self._json(404, {"error": "ruta desconocida"})

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
        if url.path == "/api/coordinador":
            return self._coordinador(str(datos.get("proyecto", "")))
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

    def _coordinador(self, proyecto: str) -> None:
        """Arranca el coordinador de un proyecto registrado (carril.py coordinador); solo proyectos del registro."""
        d = self.proyectos().get(proyecto)
        if not d:
            return self._json(404, {"error": f"no hay proyecto {proyecto}"})
        orden = [sys.executable, "-I", str(AQUI / "carril.py"), "coordinador", "--sesion", self.ctx["sesion"],
                 "--repo", d["repo"], "--run", d["run"], "--proyecto", proyecto]  # fmt: skip
        try:
            r = subprocess.run(orden, capture_output=True, text=True, timeout=150, check=False)
        except subprocess.TimeoutExpired:
            return self._json(504, {"error": "el coordinador tardó más de 150 s en arrancar"})
        if r.returncode not in (0, 3):
            return self._json(409, {"error": (r.stderr or r.stdout).strip()[-400:]})
        return self._json(200, {"ok": True, "salida": (r.stdout or r.stderr).strip()[-400:]})


# --- vista de terminal --------------------------------------------------------------------------------------------
COLOR = {"trabajando": "34", "espera": "31", "quieto": "33", "listo": "32", "puerta": "35", "enviado": "36"}
TITULO = {"trabajando": "Trabajando", "espera": "Te espera", "quieto": "Quieto", "listo": "Listo", "puerta": "Puerta",
          "enviado": "Enviado"}  # fmt: skip


def hace(t: float | None, ahora: float) -> str:
    if not t:
        return ""
    s = int(ahora - t)
    return f"{s}s" if s < 60 else f"{s // 60}m" if s < 3600 else f"{s // 3600}h{(s % 3600) // 60:02d}"


def vista_terminal(d: dict) -> str:
    ahora = d["ahora"]
    salida = [f"\033[1mFlota · {d['sesion']}\033[0m  {time.strftime('%H:%M:%S')}"]
    if not d["servidor_herdr"]:
        salida.append("\033[31mherdr: la sesión no está corriendo\033[0m")
    salida.append("  ".join(f"\033[{COLOR[c]}m● {TITULO[c]} {d['resumen'][c]}\033[0m" for c in COLUMNAS))
    for p in d["proyectos"]:
        g = p.get("git") or {}
        coord = p["coordinador"] or "sin coordinador"
        salida += ["", f"\033[1m{p['nombre']}\033[0m  {g.get('rama', '')} @ {g.get('head', '')} · coordinador: {coord}"]
        for f in sorted(
            (x for x in d["carriles"] if x["proyecto"] == p["nombre"]), key=lambda x: COLUMNAS.index(x["columna"])
        ):
            col = f["columna"]
            listo = f["listo"]["resto"] if f.get("listo") else ""
            salida.append(f"  \033[{COLOR[col]}m{TITULO[col]:<11}\033[0m {f['nombre']:<16} {f['tipo']:<6} "
                          f"{f.get('modelo') or '-'!s:<18} {hace(f.get('desde'), ahora):>6}  {listo}")  # fmt: skip
    sueltos = [o for o in d["otros"] if not o.get("proyecto")]
    if sueltos:
        salida += ["", "\033[1mOtros agentes\033[0m"]
        salida += [f"  {o['nombre']:<16} {o.get('agente') or '':<6} {o.get('vivo')}" for o in sueltos]
    if d["bitacora"]:
        salida += ["", "\033[1mBitácora\033[0m"] + [f"  {linea[:150]}" for linea in d["bitacora"][-6:]]
    return "\n".join(salida)


def abrir_en_cmux(url: str) -> bool:
    exe = shutil.which("cmux")
    if not exe or not os.environ.get("CMUX_WORKSPACE_ID"):
        return False
    r = subprocess.run([exe, "open", url], capture_output=True, timeout=10, check=False)
    return r.returncode == 0


def escribir_privado(ruta: Path, texto: str) -> Path:
    """Escribe un archivo que solo el dueño puede leer (lleva el token del tablero)."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(texto)
    ruta.chmod(0o600)
    return ruta


def token_fijo() -> str:
    """Token que se crea una vez y se reúsa, para que el panel de navegador de cmux tenga una dirección estable."""
    ruta = ESTADO_FLOTA / "token"
    with contextlib.suppress(OSError):
        guardado = ruta.read_text(encoding="utf-8").strip()
        if len(guardado) >= 20:
            return guardado
    nuevo = secrets.token_urlsafe(24)
    escribir_privado(ruta, nuevo + "\n")
    return nuevo


PAGINA_INICIO = """<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Flota</title>
<style>body{background:#0b0b0c;color:#9b9ba1;font:13px ui-monospace,Menlo,monospace;display:grid;place-items:center;
height:100vh;margin:0}</style></head><body><p id="m">Esperando al tablero de la flota…</p><script>
const url = "__URL__";
async function probar() {
  try { await fetch(url.split("?")[0] + "fuentes/IBMPlexMono-400.woff2", { mode: "no-cors" }); location.replace(url); }
  catch (e) { setTimeout(probar, 1000); }
}
probar();
</script></body></html>
"""


def pagina_inicio(url: str) -> Path:
    """Página local (file://) que espera a que el servidor responda y abre el tablero: el panel de cmux la carga."""
    return escribir_privado(ESTADO_FLOTA / "abrir.html", PAGINA_INICIO.replace("__URL__", url))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sesion", required=True)
    p.add_argument("--run", help="solo esta corrida (con --repo); sin él, todos los proyectos registrados")
    p.add_argument("--repo")
    p.add_argument("--puerto", type=int, default=0)
    p.add_argument("--abrir", action="store_true")
    p.add_argument("--terminal", action="store_true")
    p.add_argument("--intervalo", type=float, default=5)
    p.add_argument("--fijo", action="store_true", help=f"puerto {PUERTO_FIJO} y token guardado (para el panel de cmux)")
    a = p.parse_args(argv)
    fijos = None
    if a.run:
        repo = str(Path(a.repo).expanduser().resolve()) if a.repo else ""
        fijos = {nombre_proyecto(repo or a.run): {"repo": repo, "run": str(Path(a.run).expanduser().resolve())}}
    if a.terminal:
        try:
            while True:
                print("\033[2J\033[H" + vista_terminal(estado(fijos or corridas(), a.sesion)), flush=True)
                time.sleep(a.intervalo)
        except KeyboardInterrupt:
            return 0
    global MONITOR
    MONITOR = Monitor()
    MONITOR.start()
    mimetypes.add_type("font/woff2", ".woff2")
    token = token_fijo() if a.fijo else secrets.token_urlsafe(18)
    Tablero.ctx = {"fijos": fijos, "sesion": a.sesion, "token": token}
    try:
        servidor = ThreadingHTTPServer(("127.0.0.1", a.puerto or (PUERTO_FIJO if a.fijo else 0)), Tablero)
    except OSError as e:
        print(f"no se pudo abrir el puerto: {e} (¿ya hay otro tablero corriendo?)", file=sys.stderr)
        return 1
    url = f"http://127.0.0.1:{servidor.server_address[1]}/?t={token}"
    ruta = escribir_privado(ESTADO_FLOTA / "tablero-url", url + "\n")
    if a.fijo:
        pagina_inicio(url)
    print(f"tablero de la flota en {url}  (Ctrl+C para pararlo; la URL queda en {ruta})", flush=True)
    if a.abrir and not abrir_en_cmux(url):
        print("no se pudo abrir en cmux: abre la URL de arriba en el navegador", flush=True)
    with contextlib.suppress(KeyboardInterrupt):
        servidor.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
