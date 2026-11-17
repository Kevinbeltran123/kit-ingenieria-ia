"""Detector de «En vivo» que lee los registros de sesión de Claude Code: archivos escritos o editados y comandos.

Cada agente con cwd tiene su carpeta en ~/.claude/projects/<cwd codificado>/; se lee su `sesion_agente` o, si no la
trae, el .jsonl más reciente. Solo se lee el final del archivo (TAIL bytes) y se cachea por (ruta, tamaño, mtime).
Contrato en references/vivo-contrato.md.
"""

from __future__ import annotations

import difflib
import json
import os
import re
from datetime import datetime
from pathlib import Path

TAIL = 2 * 1024 * 1024
MAX_FRAGMENTO = 60
MAX_RESULTADO = 20
MAX_COMANDOS = 10
HERRAMIENTAS_CODIGO = ("Write", "Edit", "MultiEdit", "NotebookEdit")
_cache: dict[str, tuple[int, float, dict]] = {}


def carpeta_sesiones(cwd: str) -> Path:
    """Carpeta de los registros de un cwd: Claude Code cambia todo lo que no es letra o número por «-»."""
    base = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    return base / "projects" / re.sub(r"[^A-Za-z0-9]", "-", cwd)


def archivo_sesion(agente: dict) -> Path | None:
    """El registro del agente: el de su `sesion_agente` o, si no la trae, el .jsonl más reciente de su carpeta."""
    cwd = agente.get("cwd")
    if not cwd:
        return None
    carpeta = carpeta_sesiones(cwd)
    sesion = agente.get("sesion_agente")
    if sesion:
        ruta = carpeta / f"{sesion}.jsonl"
        return ruta if ruta.is_file() else None
    mejor, mejor_t = None, -1.0
    try:
        for ruta in carpeta.glob("*.jsonl"):
            try:
                t = ruta.stat().st_mtime
            except OSError:
                continue
            if t > mejor_t:
                mejor, mejor_t = ruta, t
    except OSError:
        return None
    return mejor


def _epoch(texto: object) -> float | None:
    if not isinstance(texto, str) or not texto:
        return None
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00")).timestamp()
    except ValueError:
        try:
            return datetime.strptime(texto[:19], "%Y-%m-%dT%H:%M:%S").timestamp()
        except ValueError:
            return None


def _texto_resultado(contenido: object) -> str:
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list):
        return "\n".join(b.get("text", "") for b in contenido if isinstance(b, dict) and b.get("type") == "text")
    return ""


def leer_registro(ruta: Path) -> dict:
    """{"usos": {id: {nombre, entrada, t}}, "resultados": {id: {texto, error, t}}} del final del registro."""
    try:
        st = ruta.stat()
    except OSError:
        return {"usos": {}, "resultados": {}}
    clave = str(ruta)
    guardado = _cache.get(clave)
    if guardado and guardado[0] == st.st_size and guardado[1] == st.st_mtime:
        return guardado[2]
    usos, resultados = {}, {}
    try:
        with ruta.open("rb") as f:
            inicio = max(0, st.st_size - TAIL)
            f.seek(inicio)
            crudo = f.read()
    except OSError:
        return {"usos": {}, "resultados": {}}
    lineas = crudo.split(b"\n")
    if inicio > 0:
        lineas = lineas[1:]  # la primera quedó cortada
    for linea in lineas:
        if b"tool_" not in linea:
            continue
        try:
            d = json.loads(linea)
        except ValueError:
            continue
        if not isinstance(d, dict) or d.get("type") not in ("assistant", "user"):
            continue
        contenido = (d.get("message") or {}).get("content")
        if not isinstance(contenido, list):
            continue
        t = _epoch(d.get("timestamp"))
        for b in contenido:
            if not isinstance(b, dict) or t is None:
                continue
            if b.get("type") == "tool_use" and b.get("id") and isinstance(b.get("input"), dict):
                usos[b["id"]] = {"nombre": b.get("name"), "entrada": b["input"], "t": t}
            elif b.get("type") == "tool_result" and b.get("tool_use_id"):
                resultados[b["tool_use_id"]] = {
                    "texto": _texto_resultado(b.get("content")),
                    "error": bool(b.get("is_error")),
                    "t": t,
                }
    datos = {"usos": usos, "resultados": resultados}
    _cache[clave] = (st.st_size, st.st_mtime, datos)
    return datos


def _diff(viejo: str, nuevo: str, archivo: str) -> list[str]:
    lineas = list(
        difflib.unified_diff(viejo.splitlines(), nuevo.splitlines(), f"a/{archivo}", f"b/{archivo}", lineterm="", n=2)
    )
    return lineas[2:]  # sin las cabeceras ---/+++


def cambio(nombre: str, entrada: dict) -> tuple[str, list[str]] | None:
    """(archivo, líneas del diff) de una herramienta que escribe; None si no se entiende."""
    if nombre == "NotebookEdit":
        archivo = entrada.get("notebook_path")
        if entrada.get("edit_mode") == "delete":
            return (archivo, []) if isinstance(archivo, str) else None
        nuevo = entrada.get("new_source")
        lineas = ["+" + linea for linea in nuevo.splitlines()] if isinstance(nuevo, str) else []
        return (archivo, lineas) if isinstance(archivo, str) else None
    archivo = entrada.get("file_path")
    if not isinstance(archivo, str):
        return None
    if nombre == "Write":
        contenido = entrada.get("content")
        return archivo, ["+" + linea for linea in contenido.splitlines()] if isinstance(contenido, str) else []
    ediciones = [entrada] if nombre == "Edit" else [e for e in entrada.get("edits") or [] if isinstance(e, dict)]
    lineas: list[str] = []
    for e in ediciones:
        viejo, nuevo = e.get("old_string"), e.get("new_string")
        if isinstance(viejo, str) and isinstance(nuevo, str):
            lineas += _diff(viejo, nuevo, archivo)
    return archivo, lineas


def _cuenta(lineas: list[str]) -> tuple[int, int]:
    mas = sum(1 for linea in lineas if linea.startswith("+"))
    menos = sum(1 for linea in lineas if linea.startswith("-"))
    return mas, menos


def _recortar(lineas: list[str]) -> str:
    if len(lineas) > MAX_FRAGMENTO:
        lineas = [*lineas[: MAX_FRAGMENTO - 1], f"… {len(lineas) - MAX_FRAGMENTO + 1} líneas más"]
    return "\n".join(lineas)


def _corta(archivo: str, cwd: str | None) -> str:
    if cwd:
        base = cwd.rstrip("/") + "/"
        if archivo.startswith(base):
            return archivo[len(base) :]
    return "/".join(Path(archivo).parts[-2:])


def _pruebas(texto: str) -> str:
    partes = [f"{m.group(1)} {m.group(2)}" for m in re.finditer(r"\b(\d+) (passed|failed)\b", texto)]
    return ", ".join(dict.fromkeys(partes))


def detectar(ctx: dict) -> list[dict]:
    desde = ctx.get("desde") or 0.0
    codigo: dict[str, dict] = {}
    comandos: list[dict] = []
    leidos = set()
    for agente in ctx.get("agentes", []):
        ruta = archivo_sesion(agente)
        if ruta is None or str(ruta) in leidos:
            continue
        leidos.add(str(ruta))
        try:
            if ruta.stat().st_mtime < desde:
                continue
        except OSError:
            continue
        registro = leer_registro(ruta)
        nombre_agente, proyecto, cwd = agente.get("nombre"), agente.get("proyecto"), agente.get("cwd")
        propios = []
        for uid, uso in sorted(registro["usos"].items(), key=lambda par: par[1]["t"]):
            if uso["t"] < desde:
                continue
            resultado = registro["resultados"].get(uid)
            if uso["nombre"] in HERRAMIENTAS_CODIGO:
                if resultado and resultado["error"]:
                    continue  # la edición no se aplicó
                hecho = cambio(uso["nombre"], uso["entrada"])
                if not hecho:
                    continue
                archivo, lineas = hecho
                mas, menos = _cuenta(lineas)
                previo = codigo.get(archivo)
                if previo:
                    mas += previo["datos"]["mas"]
                    menos += previo["datos"]["menos"]
                corta = _corta(archivo, cwd)
                codigo[archivo] = {
                    "id": f"codigo:{archivo}",
                    "tipo": "codigo",
                    "proyecto": proyecto,
                    "agente": nombre_agente,
                    "t": uso["t"],
                    "titulo": f"{corta} +{mas} −{menos}",
                    "datos": {
                        "archivo": archivo,
                        "mas": mas,
                        "menos": menos,
                        "fragmento": _recortar(lineas),
                        "herramienta": uso["nombre"],
                    },
                }
            elif uso["nombre"] == "Bash":
                comando = uso["entrada"].get("command")
                if not isinstance(comando, str):
                    continue
                texto = resultado["texto"] if resultado else ""
                primera = (comando.strip().splitlines() or [""])[0]
                titulo = primera if len(primera) <= 80 else primera[:79] + "…"
                pruebas = _pruebas(texto)
                if pruebas:
                    titulo += f" · {pruebas}"
                propios.append(
                    {
                        "id": f"comando:{uid}",
                        "tipo": "comando",
                        "proyecto": proyecto,
                        "agente": nombre_agente,
                        "t": resultado["t"] if resultado else uso["t"],
                        "titulo": titulo,
                        "datos": {
                            "comando": comando,
                            "resultado": texto.splitlines()[-MAX_RESULTADO:],
                            "ok": (not resultado["error"]) if resultado else None,
                            "duracion": round(resultado["t"] - uso["t"], 3) if resultado else None,
                        },
                    }
                )
        comandos += propios[-MAX_COMANDOS:]
    for clave in [c for c in _cache if c not in leidos]:
        del _cache[clave]
    return [*codigo.values(), *comandos]
