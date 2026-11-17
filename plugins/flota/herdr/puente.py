"""Plugin de herdr: cada cambio de estado de un agente queda en eventos.jsonl y, si cmux está abierto, se ve allí.

herdr lo corre por cada evento `pane.agent_status_changed` o `pane.closed`, con el evento en HERDR_PLUGIN_EVENT_JSON.
- Siempre: agrega una línea a <estado>/<sesión>/eventos.jsonl (el tablero de la flota la lee para la línea de tiempo).
- Con cmux: estado del agente en la barra del espacio (`cmux set-status`), una línea en su log (`cmux log`) y un aviso
  (`cmux notify`) cuando un agente queda esperándote o termina su turno.
El espacio de cmux es el de la terminal donde arrancó el servidor de herdr (CMUX_WORKSPACE_ID heredado).

Configuración opcional en <config del plugin>/config.json: {"avisos": "todos" | "sin-claude" | "ninguno"}.
"sin-claude" deja los avisos de Claude a los hooks propios de cmux, para no recibirlos dos veces.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ETIQUETAS = {"working": "trabajando", "blocked": "te espera", "idle": "quieto", "done": "terminó", "unknown": "?"}
COLORES = {"working": "#3B82F6", "blocked": "#EF4444", "idle": "#9CA3AF", "done": "#22C55E", "unknown": "#9CA3AF"}
ICONOS = {
    "working": "bolt",
    "blocked": "exclamationmark.bubble",
    "idle": "pause",
    "done": "checkmark",
    "unknown": "questionmark",
}


def dir_estado(sesion: str) -> Path:
    base = os.environ.get("FLOTA_EVENTOS_DIR") or os.environ.get("HERDR_PLUGIN_STATE_DIR")
    if not base:
        base = str(Path.home() / ".local" / "state" / "herdr" / "plugins" / "kit.flota.puente")
    return Path(base) / sesion


def config() -> dict:
    d = os.environ.get("HERDR_PLUGIN_CONFIG_DIR")
    if not d:
        return {}
    try:
        return json.loads((Path(d) / "config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def nombre_agente(pane: str) -> str | None:
    """Nombre del agente que ocupa el pane (los carriles lo tienen; un claude suelto no)."""
    herdr = os.environ.get("HERDR_BIN_PATH", "herdr")
    try:
        r = subprocess.run([herdr, "agent", "get", pane], capture_output=True, text=True, timeout=5, check=False)
        return json.loads(r.stdout)["result"]["agent"].get("name")
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired):
        return None


def cmux(*args: str) -> None:
    """Llama a cmux; si falla (cmux cerrado, servidor de herdr arrancado fuera de cmux), lo deja en cmux-errores.log."""
    exe = shutil.which("cmux")
    if not exe:
        return
    ws = os.environ.get("CMUX_WORKSPACE_ID")
    extra = ["--workspace", ws] if ws else []
    try:
        r = subprocess.run([exe, *args, *extra], capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        error = str(e)
    else:
        if r.returncode == 0:
            return
        error = (r.stderr or r.stdout).strip()[:300]
    with contextlib.suppress(OSError):
        ruta = dir_estado(os.environ.get("HERDR_SESSION") or "default") / "cmux-errores.log"
        with ruta.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} cmux {args[0]}: {error}\n")


def decidir_aviso(previo: str | None, nuevo: str, agente: str | None, modo: str) -> str | None:
    """Texto del aviso para esta transición, o None si no merece uno."""
    if modo == "ninguno" or (modo == "sin-claude" and agente == "claude"):
        return None
    if nuevo == "blocked" and previo != "blocked":
        return "te espera: responde en herdr"
    if previo == "working" and nuevo in ("idle", "done"):
        return "terminó su turno"
    return None


@contextlib.contextmanager
def candado(ruta: Path):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def manejar(evento: dict, sesion: str) -> dict | None:
    datos = evento.get("data") or {}
    tipo = datos.get("type") or evento.get("event")
    pane = datos.get("pane_id")
    if not pane:
        return None
    base = dir_estado(sesion)
    with candado(base / ".candado"):
        ruta_estado = base / "estado.json"
        try:
            estado = json.loads(ruta_estado.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            estado = {}
        previo = estado.get(pane, {})
        if tipo == "pane_closed":
            estado.pop(pane, None)
            registro = {
                "t": time.time(),
                "pane": pane,
                "nombre": previo.get("nombre"),
                "de": previo.get("estado"),
                "a": "cerrado",
                "agente": previo.get("agente"),
            }
        else:
            nuevo = datos.get("agent_status") or "unknown"
            nombre = previo.get("nombre") or nombre_agente(pane)
            agente = datos.get("agent")
            estado[pane] = {"estado": nuevo, "nombre": nombre, "agente": agente, "desde": time.time()}
            registro = {
                "t": time.time(),
                "pane": pane,
                "nombre": nombre,
                "de": previo.get("estado"),
                "a": nuevo,
                "agente": agente,
                "workspace": datos.get("workspace_id"),
            }
        ruta_estado.write_text(json.dumps(estado), encoding="utf-8")
        with (base / "eventos.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    return registro


def reflejar_en_cmux(registro: dict) -> None:
    quien = registro.get("nombre") or f"{registro.get('agente') or 'agente'} {registro['pane']}"
    clave = f"flota-{registro.get('nombre') or registro['pane'].replace(':', '-')}"
    nuevo = registro["a"]
    if nuevo == "cerrado":
        cmux("clear-status", clave)
        cmux("log", "--source", "flota", f"{quien}: cerrado")
        return
    cmux(
        "set-status",
        clave,
        f"{quien}: {ETIQUETAS.get(nuevo, nuevo)}",
        "--color",
        COLORES.get(nuevo, "#9CA3AF"),
        "--icon",
        ICONOS.get(nuevo, "questionmark"),
    )
    nivel = "warning" if nuevo == "blocked" else "info"
    de = ETIQUETAS.get(registro.get("de") or "", registro.get("de") or "—")
    cmux("log", "--level", nivel, "--source", "flota", f"{quien}: {de} → {ETIQUETAS.get(nuevo, nuevo)}")
    aviso = decidir_aviso(registro.get("de"), nuevo, registro.get("agente"), config().get("avisos", "todos"))
    if aviso:
        cmux("notify", "--title", f"Flota · {quien}", "--body", aviso)


def main() -> int:
    try:
        evento = json.loads(os.environ.get("HERDR_PLUGIN_EVENT_JSON", "{}"))
    except ValueError:
        return 0
    sesion = os.environ.get("HERDR_SESSION") or "default"
    registro = manejar(evento, sesion)
    if registro:
        reflejar_en_cmux(registro)
    return 0


if __name__ == "__main__":
    sys.exit(main())
