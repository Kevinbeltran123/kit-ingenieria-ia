"""Piezas compartidas por los scripts de la flota: llamar a herdr, leer el directorio de la corrida.

Solo biblioteca estándar y compatible con Python 3.9. Los scripts lo importan con la carpeta de scripts en sys.path.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

# Una línea de entrega: "<NOMBRE>-READY ..." al principio de una línea, con viñetas o comillas opcionales delante.
LISTO = re.compile(r"^[-*>` ]*([A-Z0-9][A-Z0-9-]*)-READY(?: +(.*?))?\s*$")
# Revisión entregada: "REVIEW-READY <carril> <veredicto>".
REVISION = re.compile(r"^[-*>` ]*REVIEW-READY +(\S+)(?: +(.*?))?\s*$")
# Teclas que se pueden mandar a un carril desde el tablero (las que sirven para responder un diálogo).
TECLAS = ("enter", "esc", "up", "down", "tab", "ctrl+c", "1", "2", "3", "y", "n")


class HerdrError(RuntimeError):
    """herdr respondió con un error en JSON o no se pudo ejecutar."""

    def __init__(self, codigo: str, mensaje: str) -> None:
        super().__init__(f"{codigo}: {mensaje}")
        self.codigo = codigo
        self.mensaje = mensaje


def herdr_bin() -> str:
    return os.environ.get("FLOTA_HERDR", "herdr")


def herdr(sesion: str, *args: str, timeout: float = 60, json_salida: bool = True) -> Any:
    """Corre `herdr --session <sesion> <args>` y devuelve el JSON (o el texto si json_salida es False).

    Se quita HERDR_SESSION del entorno para que la sesión pedida mande aunque el script corra dentro de otra.
    """
    env = {k: v for k, v in os.environ.items() if k != "HERDR_SESSION"}
    try:
        r = subprocess.run(
            [herdr_bin(), "--session", sesion, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except FileNotFoundError as e:
        raise HerdrError("sin_herdr", "no se encontró herdr en PATH (brew install herdr)") from e
    except subprocess.TimeoutExpired as e:
        raise HerdrError("timeout", f"herdr {' '.join(args[:2])} no respondió en {timeout:.0f} s") from e
    if r.returncode != 0:
        try:
            err = json.loads(r.stderr or r.stdout).get("error", {})
            raise HerdrError(err.get("code", "error"), err.get("message", r.stderr.strip()))
        except (ValueError, AttributeError):
            raise HerdrError("error", (r.stderr or r.stdout).strip()[:400]) from None
    if not json_salida:
        return r.stdout
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {"texto": r.stdout}


def agentes(sesion: str) -> list[dict]:
    """Agentes vivos de la sesión; lista vacía si el servidor no está corriendo."""
    try:
        return herdr(sesion, "agent", "list", timeout=10).get("result", {}).get("agents", [])
    except HerdrError:
        return []


def pantalla(sesion: str, agente: str, fuente: str = "visible", lineas: int = 0) -> str:
    args = ["agent", "read", agente, "--source", fuente]
    if lineas:
        args += ["--lines", str(lineas)]
    return herdr(sesion, *args, timeout=15, json_salida=False)


# --- Directorio de la corrida -------------------------------------------------------------------------------------


def archivo_carriles(run: Path) -> Path:
    return run / "carriles.json"


def cargar_carriles(run: Path) -> dict[str, dict]:
    try:
        datos = json.loads(archivo_carriles(run).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return datos if isinstance(datos, dict) else {}


def guardar_carriles(run: Path, carriles: dict[str, dict]) -> None:
    """Escritura atómica: el tablero lee el archivo mientras el coordinador lo cambia."""
    run.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(run), prefix=".carriles-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(carriles, f, ensure_ascii=False, indent=2)
        f.write("\n")
    Path(tmp).replace(archivo_carriles(run))


def lineas_listo(run: Path) -> list[dict]:
    """Líneas READY de las entregas y REVIEW-READY de las revisiones, en orden de archivo."""
    salida = []
    for patron in ("handover-*.md", "review-*.md"):
        for ruta in sorted(run.glob(patron)):
            try:
                texto = ruta.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for linea in texto.splitlines():
                m = REVISION.match(linea)
                if m:
                    salida.append(
                        {"tipo": "revision", "carril": m.group(1), "resto": m.group(2) or "", "archivo": ruta.name}
                    )
                    continue
                m = LISTO.match(linea)
                if m and m.group(1) != "REVIEW":
                    resto = m.group(2) or ""
                    salida.append({"tipo": "listo", "carril": m.group(1).lower(), "resto": resto, "archivo": ruta.name})
    return salida


def puerta(run: Path) -> dict[str, list[str]]:
    """Secciones de gate/queue.md: '## En cola', '## Probando', '## Done' (u otras), con sus líneas no vacías."""
    ruta = run / "gate" / "queue.md"
    secciones: dict[str, list[str]] = {}
    actual = None
    try:
        texto = ruta.read_text(encoding="utf-8")
    except OSError:
        return secciones
    for linea in texto.splitlines():
        if linea.startswith("## "):
            actual = linea[3:].strip()
            secciones.setdefault(actual, [])
        elif actual is not None and linea.strip():
            secciones[actual].append(linea.strip().lstrip("-* ").strip())
    return secciones


def bitacora(run: Path, ultimas: int = 12) -> list[str]:
    try:
        lineas = (run / "STATE.md").read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [linea[2:] for linea in lineas if linea.startswith("- ")][-ultimas:]


def anotar(run: Path, texto: str) -> None:
    """Agrega una línea fechada a la bitácora de STATE.md."""
    ruta = run / "STATE.md"
    marca = time.strftime("%Y-%m-%d %H:%M")
    with ruta.open("a", encoding="utf-8") as f:
        f.write(f"- {marca} {texto}\n")


# --- Registro de proyectos (una sola sesión de herdr para todos) -----------------------------------------------------


def archivo_registro() -> Path:
    return Path(os.environ.get("FLOTA_REGISTRO") or Path.home() / ".local" / "state" / "flota" / "corridas.json")


def nombre_proyecto(repo: str) -> str:
    """Nombre corto del proyecto a partir de la carpeta del repo: minúsculas, dígitos y guiones."""
    nombre = re.sub(r"[^a-z0-9-]+", "-", Path(repo).name.lower()).strip("-")
    return (nombre or "proyecto")[:24]


def corridas() -> dict[str, dict]:
    """Proyectos registrados: {proyecto: {"repo": ..., "run": ...}}."""
    try:
        datos = json.loads(archivo_registro().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return datos if isinstance(datos, dict) else {}


def registrar_corrida(proyecto: str, repo: str, run: str, modelo_coordinador: str | None = None) -> None:
    """Registra (o actualiza) un proyecto; conserva el modelo de coordinador ya elegido si no se pasa otro."""
    ruta = archivo_registro()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    datos = corridas()
    previo = datos.get(proyecto, {})
    datos[proyecto] = {"repo": repo, "run": run}
    modelo = modelo_coordinador or previo.get("modelo_coordinador")
    if modelo:
        datos[proyecto]["modelo_coordinador"] = modelo
    fd, tmp = tempfile.mkstemp(dir=str(ruta.parent), prefix=".corridas-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
        f.write("\n")
    Path(tmp).replace(ruta)


def dir_eventos(sesion: str) -> Path:
    """Dónde escribe el puente de herdr los cambios de estado (uno por línea, JSON) de una sesión."""
    base = os.environ.get("FLOTA_EVENTOS_DIR")
    if base:
        return Path(base) / sesion
    return Path.home() / ".local" / "state" / "herdr" / "plugins" / "kit.flota.puente" / sesion


def eventos(sesion: str, ultimos: int = 400) -> list[dict]:
    ruta = dir_eventos(sesion) / "eventos.jsonl"
    try:
        lineas = ruta.read_text(encoding="utf-8").splitlines()[-ultimos:]
    except OSError:
        return []
    salida = []
    for linea in lineas:
        try:
            salida.append(json.loads(linea))
        except ValueError:
            continue
    return salida
