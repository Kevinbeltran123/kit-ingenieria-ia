"""Detector de «En vivo» para entrenamientos y procesos largos (`metricas`).

Fuentes:
- CSV de métricas cambiados en la ventana bajo las raíces (`metrics.csv`, `*metrics*.csv`, `progress.csv`,
  `history.csv`, `log*.csv`, también el de Lightning en `lightning_logs/version_*/`). Columnas numéricas como
  series alineadas por fila (`None` donde la celda está vacía o no es finita); eje x `step`, si no `epoch`, si no
  la fila. Filas seguidas con el mismo x se juntan (Lightning escribe la pérdida y la validación en filas aparte).
- El log de la carpeta del CSV (`log.txt`, `*.log`; si el CSV está en `version_*`, también dos carpetas arriba):
  últimas líneas, líneas con error y progreso (`Epoch 14/40`, `época 14 de 40`, `step 300/1000`, `14/40 [`).
- Tareas de pueue en curso (`pueue status --json`), si pueue está en PATH.

Contrato en references/vivo-contrato.md.
"""

from __future__ import annotations

import csv
import fnmatch
import io
import json
import math
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Callable

SALTAR = {".git", "node_modules", ".venv", "__pycache__", ".mypy_cache", ".ruff_cache"}
NOMBRES = ("metrics.csv", "*metrics*.csv", "progress.csv", "history.csv", "log*.csv")
TOPE_ENTRADAS = 40000
TOPE_CSV = 20
MAX_PUNTOS = 500
MAX_SERIES = 40
LINEAS_LOG = 15
LEER_CSV = 8 * 1024 * 1024
LEER_LOG = 1024 * 1024
TOPE_PUEUE = 5
ESPERA_PUEUE = 1.5

ERROR = re.compile(r"error|traceback|\bnan\b|\binf\b", re.IGNORECASE)
PROGRESO = (
    re.compile(r"\b(?:epoch|época|epoca)\s*[:=]?\s*(\d+)\s*(?:/|de|of)\s*(\d+)", re.IGNORECASE),
    re.compile(r"\b(?:step|paso|iter(?:ation)?)\s*[:=]?\s*(\d+)\s*(?:/|de|of)\s*(\d+)", re.IGNORECASE),
    re.compile(r"(\d+)\s*/\s*(\d+)\s*\["),
)
PERDIDA = re.compile(r"loss", re.IGNORECASE)
METRICA = re.compile(r"f1|acc|map|recall", re.IGNORECASE)

Ejecutar = Callable[[list], "str | None"]


def detectar(ctx: dict, ejecutar: Ejecutar | None = None) -> list[dict]:
    """Un producto por CSV de métricas reciente y otro por tarea de pueue en curso."""
    productos = []
    for ruta, raiz in _csvs(ctx):
        try:
            productos.append(_producto_csv(ruta, raiz))
        except (OSError, ValueError, csv.Error):
            continue
    productos += tareas_pueue(ctx, ejecutar)
    return productos


# --- CSV ------------------------------------------------------------------------------------------------------


def _es_csv(nombre: str) -> bool:
    bajo = nombre.lower()
    return any(fnmatch.fnmatchcase(bajo, patron) for patron in NOMBRES)


def _csvs(ctx: dict) -> list[tuple[Path, dict]]:
    """Los CSV de métricas cambiados en la ventana, cada uno con la primera raíz que lo contiene."""
    raices = ctx.get("raices", [])
    otras = {r["ruta"] for r in raices}
    corridas = {str(d.get("run")) for d in ctx.get("proyectos", {}).values() if d.get("run")}
    desde = ctx.get("desde", 0)
    vistos, hallados, entradas = set(), [], 0
    for raiz in raices:
        base = raiz["ruta"]
        pila = [base]
        while pila and entradas < TOPE_ENTRADAS:
            carpeta = pila.pop()
            try:
                with os.scandir(carpeta) as it:
                    for e in it:
                        entradas += 1
                        if entradas > TOPE_ENTRADAS:
                            break
                        try:
                            if e.is_dir(follow_symlinks=False):
                                if e.name in SALTAR or e.path in otras:
                                    continue
                                if e.name == "wt" and carpeta == base and base in corridas:
                                    continue
                                pila.append(e.path)
                            elif _es_csv(e.name) and e.is_file() and e.stat().st_mtime > desde:
                                real = os.path.realpath(e.path)
                                if real not in vistos:
                                    vistos.add(real)
                                    hallados.append((Path(e.path), raiz, e.stat().st_mtime))
                        except OSError:
                            continue
            except OSError:
                continue
    hallados.sort(key=lambda x: x[2], reverse=True)
    return [(ruta, raiz) for ruta, raiz, _ in hallados[:TOPE_CSV]]


def _leer_texto(ruta: Path, tope: int) -> tuple[str, bool]:
    """El final del archivo (hasta `tope` bytes) y si se cortó el principio."""
    with ruta.open("rb") as f:
        tamano = f.seek(0, os.SEEK_END)
        f.seek(max(0, tamano - tope))
        crudo = f.read()
    return crudo.decode("utf-8", errors="replace"), tamano > tope


def _numero(celda: str) -> float | None:
    try:
        valor = float(celda)
    except ValueError:
        return None
    return valor if math.isfinite(valor) else None


def leer_csv(ruta: Path) -> dict:
    """`x`, `series` (alineadas, hasta MAX_PUNTOS filas, con la última) y `ultima` de un CSV de métricas."""
    texto, cortado = _leer_texto(ruta, LEER_CSV)
    if cortado:  # el principio se cortó: la cabecera es la primera línea del archivo
        with ruta.open("r", encoding="utf-8", errors="replace") as f:
            cabecera = f.readline()
        texto = cabecera + texto.split("\n", 1)[-1]
    filas = list(csv.reader(io.StringIO(texto)))
    if not filas:
        return {"x": "fila", "series": {}, "ultima": {}}
    cabecera = [c.strip().lstrip("\ufeff") for c in filas[0]]
    cuerpo = [f for f in filas[1:] if any(c.strip() for c in f)]
    numericas = []
    for i, nombre in enumerate(cabecera):
        celdas = [f[i].strip() for f in cuerpo if i < len(f) and f[i].strip()]
        if nombre and celdas and all(_es_numero(c) for c in celdas):
            numericas.append((i, nombre))
    numericas = numericas[:MAX_SERIES]
    nombres = [n for _, n in numericas]
    x = "step" if "step" in nombres else "epoch" if "epoch" in nombres else "fila"
    columnas: dict[str, list[float | None]] = {n: [] for n in nombres}
    for f in cuerpo:
        valores = {n: _numero(f[i].strip()) if i < len(f) and f[i].strip() else None for i, n in numericas}
        anterior = columnas[x][-1] if x != "fila" and columnas[x] else None
        if anterior is not None and valores[x] == anterior and _juntables(columnas, valores):
            for n, v in valores.items():
                if v is not None:
                    columnas[n][-1] = v
            continue
        for n, v in valores.items():
            columnas[n].append(v)
    ultima = {}
    for n, serie in columnas.items():
        valor = next((v for v in reversed(serie) if v is not None), None)
        if valor is not None:
            ultima[n] = valor
    filas_elegidas = _submuestra(columnas, [n for n in nombres if n != x])
    series = {n: [serie[i] for i in filas_elegidas] for n, serie in columnas.items()}
    return {"x": x, "series": series, "ultima": ultima}


def _es_numero(celda: str) -> bool:
    try:
        float(celda)
    except ValueError:
        return False
    return True


def _juntables(columnas: dict, valores: dict) -> bool:
    """La fila nueva solo llena celdas vacías de la anterior (no pisa un valor distinto)."""
    for n, v in valores.items():
        previo = columnas[n][-1]
        if v is not None and previo is not None and previo != v:
            return False
    return True


def _submuestra(columnas: dict, medidas: list[str]) -> list[int]:
    """Índices de fila a conservar: hasta MAX_PUNTOS, con la última, sin dejar sin puntos a las series ralas.

    Cada serie aporta hasta `cupo` de sus filas con valor, repartidas con el mismo paso; el cupo baja hasta que la
    unión cabe. Así una validación por época no desaparece entre miles de pasos de entrenamiento.
    """
    total = len(next(iter(columnas.values()), []))
    if total <= MAX_PUNTOS:
        return list(range(total))
    con_valor = [[i for i, v in enumerate(columnas[n]) if v is not None] for n in medidas] or [list(range(total))]
    cupo = MAX_PUNTOS - 1
    while True:
        elegidas = {total - 1}
        for filas in con_valor:
            elegidas.update(_parejo(filas, cupo))
        if len(elegidas) <= MAX_PUNTOS or cupo <= 2:
            return sorted(elegidas)[-MAX_PUNTOS:]
        cupo = max(2, int(cupo * 0.8))


def _parejo(filas: list[int], cupo: int) -> list[int]:
    if len(filas) <= cupo:
        return filas
    paso = (len(filas) - 1) / (cupo - 1)
    return [filas[round(k * paso)] for k in range(cupo)]


def principales(series: dict, x: str) -> tuple[str | None, str | None]:
    """La pérdida y la métrica principal: primero las de validación (`val_`), luego las demás."""

    def elegir(patron: re.Pattern) -> str | None:
        candidatas = [n for n in series if n != x and patron.search(n)]
        validacion = [n for n in candidatas if n.lower().startswith("val")]
        return (validacion or candidatas or [None])[0]

    return elegir(PERDIDA), elegir(METRICA)


# --- log y progreso -------------------------------------------------------------------------------------------


def buscar_log(csv_ruta: Path, raiz: str) -> Path | None:
    """El log más reciente en la carpeta del CSV; si el CSV está en `version_*`, también hasta dos carpetas arriba."""
    carpetas = [csv_ruta.parent]
    if csv_ruta.parent.name.startswith("version_"):
        carpetas += [csv_ruta.parent.parent, csv_ruta.parent.parent.parent]
    base = Path(raiz)
    for carpeta in carpetas:
        if carpeta != base and base not in carpeta.parents:
            break
        try:
            candidatos = [p for p in carpeta.iterdir() if (p.name == "log.txt" or p.suffix == ".log") and p.is_file()]
        except OSError:
            continue
        if candidatos:
            return max(candidatos, key=lambda p: p.stat().st_mtime)
    return None


def resumir_log(texto: str) -> dict:
    """Últimas líneas, cuántas tienen error y el progreso más reciente que se reconoce."""
    lineas = [linea.rstrip() for linea in texto.splitlines() if linea.strip()]
    return {
        "log": lineas[-LINEAS_LOG:],
        "errores": sum(1 for linea in lineas if ERROR.search(linea)),
        "progreso": progreso(lineas),
    }


def progreso(lineas: list[str]) -> dict | None:
    """`{actual, total}` de la última línea con un patrón de progreso; las épocas mandan sobre los pasos."""
    for linea in reversed(lineas):
        for patron in PROGRESO:
            m = patron.search(linea)
            if m:
                actual, total = int(m.group(1)), int(m.group(2))
                if total > 0 and actual <= total:
                    return {"actual": actual, "total": total}
    return None


# --- producto -------------------------------------------------------------------------------------------------


def _formato(valor: float) -> str:
    return f"{valor:.4g}"


def _producto_csv(ruta: Path, raiz: dict) -> dict:
    datos = leer_csv(ruta)
    t = ruta.stat().st_mtime
    log = buscar_log(ruta, raiz["ruta"])
    resumen = {"log": [], "errores": 0, "progreso": None}
    if log is not None:
        try:
            resumen = resumir_log(_leer_texto(log, LEER_LOG)[0])
            if log.stat().st_mtime > t:
                t = log.stat().st_mtime
        except OSError:
            pass
    carpeta = ruta.parent
    if carpeta.name.startswith("version_") and carpeta.parent.name == "lightning_logs":
        carpeta = carpeta.parent.parent
    try:
        nombre = str(carpeta.relative_to(raiz["ruta"]))
    except ValueError:
        nombre = carpeta.name
    nombre = Path(raiz["ruta"]).name if nombre == "." else nombre
    partes = [nombre]
    p = resumen["progreso"]
    if p:
        partes.append(f"{p['actual']}/{p['total']}")
    perdida, metrica = principales(datos["series"], datos["x"])
    partes += [f"{col} {_formato(datos['ultima'][col])}" for col in (perdida, metrica) if col in datos["ultima"]]
    if resumen["errores"]:
        partes.append(f"{resumen['errores']} con error")
    return {
        "id": f"metricas:{ruta}",
        "tipo": "metricas",
        "proyecto": raiz.get("proyecto"),
        "agente": raiz.get("agente"),
        "t": t,
        "titulo": " · ".join(partes),
        "datos": {"archivo": str(ruta), **datos, **resumen},
    }


# --- pueue ----------------------------------------------------------------------------------------------------


def _ejecutar(args: list) -> str | None:
    if not shutil.which("pueue"):
        return None
    try:
        r = subprocess.run(["pueue", *args], capture_output=True, text=True, timeout=ESPERA_PUEUE, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def _fecha(texto: object) -> float | None:
    """Epoch de una fecha ISO de pueue (con nanosegundos y zona); None si no se entiende."""
    if not isinstance(texto, str):
        return None
    limpio = re.sub(r"(\.\d{6})\d+", r"\1", texto.replace("Z", "+00:00"))
    try:
        return datetime.fromisoformat(limpio).timestamp()
    except ValueError:
        return None


def _en_curso(tarea: dict) -> dict | None:
    """Los datos del estado Running (pueue 4: `{"Running": {...}}`; pueue 3: `"Running"`), o None."""
    estado = tarea.get("status")
    if estado == "Running":
        return {"start": tarea.get("start")}
    if isinstance(estado, dict) and isinstance(estado.get("Running"), dict):
        return estado["Running"]
    return None


def _duracion(segundos: float) -> str:
    m = int(segundos // 60)
    return f"{m // 60}h{m % 60:02d}" if m >= 60 else f"{m}m"


def tareas_pueue(ctx: dict, ejecutar: Ejecutar | None = None) -> list[dict]:
    """Un producto `metricas` por tarea de pueue en curso; nada si pueue no está o no responde."""
    ejecutar = ejecutar or _ejecutar
    try:
        tareas = json.loads(ejecutar(["status", "--json"]) or "{}").get("tasks", {})
    except (ValueError, AttributeError):
        return []
    if not isinstance(tareas, dict):
        return []
    ahora = ctx.get("ahora", 0)
    productos = []
    for clave, tarea in tareas.items():
        if not isinstance(tarea, dict):
            continue
        curso = _en_curso(tarea)
        if curso is None or len(productos) >= TOPE_PUEUE:
            continue
        ident = tarea.get("id", clave)
        inicio = _fecha(curso.get("start"))
        comando = str(tarea.get("command") or tarea.get("original_command") or "")
        etiqueta = tarea.get("label")
        resumen = {"log": [], "errores": 0, "progreso": None}
        try:
            salida = json.loads(ejecutar(["log", "--json", "--lines", str(LINEAS_LOG), str(ident)]) or "{}")
            texto = (salida.get(str(ident)) or {}).get("output") or ""
            resumen = resumir_log(texto if isinstance(texto, str) else "")
        except (ValueError, AttributeError):
            pass
        proyecto, agente = _duenio(str(tarea.get("path") or ""), ctx)
        partes = [f"pueue {ident}", etiqueta or comando[:60]]
        if resumen["progreso"]:
            partes.append(f"{resumen['progreso']['actual']}/{resumen['progreso']['total']}")
        if inicio:
            partes.append(_duracion(max(0.0, ahora - inicio)))
        productos.append(
            {
                "id": f"metricas:pueue:{ident}",
                "tipo": "metricas",
                "proyecto": proyecto,
                "agente": agente,
                "t": ahora,
                "titulo": " · ".join(partes),
                "datos": {
                    "archivo": None,
                    "x": "fila",
                    "series": {},
                    "ultima": {},
                    **resumen,
                    "pueue": {
                        "id": ident,
                        "label": etiqueta,
                        "comando": comando,
                        "grupo": tarea.get("group"),
                        "inicio": inicio,
                        "duracion": max(0.0, ahora - inicio) if inicio else None,
                    },
                },
            }
        )
    return productos


def _duenio(ruta: str, ctx: dict) -> tuple[str | None, str | None]:
    """Proyecto y agente de la raíz más específica que contiene la carpeta de la tarea."""
    mejor = None
    for r in ctx.get("raices", []):
        if (ruta == r["ruta"] or ruta.startswith(r["ruta"].rstrip("/") + "/")) and (
            mejor is None or len(r["ruta"]) > len(mejor["ruta"])
        ):
            mejor = r
    return (mejor.get("proyecto"), mejor.get("agente")) if mejor else (None, None)
