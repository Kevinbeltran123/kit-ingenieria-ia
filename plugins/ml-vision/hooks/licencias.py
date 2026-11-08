"""PreToolUse: bloquea agregar dependencias con licencia restrictiva sin aprobación.

Vigila `ultralytics` (AGPL-3.0, alcanza también a los pesos entrenados) y
`rfdetr[plus]` (licencia no Apache). Se permite si `LICENSES.md` en la raíz del
proyecto tiene una línea como:

    APROBADO: ultralytics — licencia Enterprise n.º 123, legal (2026-11-07)

Revisa Edit/Write/MultiEdit en archivos de dependencias y comandos de instalación
en Bash (pip, uv, poetry, conda, pixi). Las líneas APROBADO: solo las escribe la
persona: si Claude intenta agregarlas a LICENSES.md (por edición o por Bash), se bloquea.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

PAQUETES = {
    "ultralytics": re.compile(r"(?<![\w-])ultralytics(?![\w])", re.IGNORECASE),
    "rfdetr[plus]": re.compile(r"(?<![\w-])rfdetr\s*\[[^\]]*\bplus\b[^\]]*\]", re.IGNORECASE),
}
ARCHIVOS_DEPENDENCIAS = re.compile(
    r"^(pyproject\.toml|setup\.cfg|setup\.py|environment\.ya?ml|pixi\.toml|requirements[\w.-]*\.(txt|in))$"
)
INSTALACION = re.compile(r"\b(pip3?|uv|poetry|conda|mamba|pixi)\b[^;&|]*?\b(install|add)\b", re.IGNORECASE)


def aprobados(raiz: Path) -> set[str]:
    archivo = raiz / "LICENSES.md"
    if not archivo.is_file():
        return set()
    texto = archivo.read_text(encoding="utf-8", errors="ignore")
    return {
        nombre for nombre in PAQUETES
        if re.search(rf"^\s*[-*]?\s*APROBADO:\s*{re.escape(nombre)}(?![\w\[])", texto, re.IGNORECASE | re.MULTILINE)
    }


def agregados(antes: str, despues: str) -> list[str]:
    return [n for n, rx in PAQUETES.items() if len(rx.findall(despues)) > len(rx.findall(antes))]


APROBACION = re.compile(r"^\s*[-*]?\s*APROBADO:", re.IGNORECASE | re.MULTILINE)
ESCRIBE = re.compile(r">|\btee\b|\bsed\s+(?:-\w+\s+)*-i|\bperl\s+-\w*i")
SOLO_LA_PERSONA = ("Bloqueado: solo la persona registra aprobaciones de licencia en LICENSES.md. "
                   "Pídele que agregue ella misma la línea 'APROBADO: <paquete> — <licencia y quién aprobó>'.")


def antes_y_despues(herramienta: str, entrada: dict) -> tuple[str, str]:
    if herramienta == "Write":
        ruta = Path(entrada.get("file_path", ""))
        actual = ruta.read_text(encoding="utf-8", errors="ignore") if ruta.is_file() else ""
        return actual, entrada.get("content", "")
    if herramienta == "Edit":
        return entrada.get("old_string", ""), entrada.get("new_string", "")
    edits = entrada.get("edits") or []
    return ("\n".join(e.get("old_string", "") for e in edits), "\n".join(e.get("new_string", "") for e in edits))


def agrega_aprobacion(herramienta: str, entrada: dict) -> bool:
    if herramienta in {"Edit", "Write", "MultiEdit"}:
        if Path(entrada.get("file_path", "")).name != "LICENSES.md":
            return False
        antes, despues = antes_y_despues(herramienta, entrada)
        return len(APROBACION.findall(despues)) > len(APROBACION.findall(antes))
    comando = entrada.get("command", "") if herramienta == "Bash" else ""
    return "APROBADO" in comando.upper() and "LICENSES.MD" in comando.upper() and bool(ESCRIBE.search(comando))


def main() -> int:
    try:
        datos = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    raiz = Path(os.environ.get("CLAUDE_PROJECT_DIR") or datos.get("cwd") or ".")
    herramienta = datos.get("tool_name", "")
    entrada = datos.get("tool_input") or {}
    nuevos: list[str] = []

    if agrega_aprobacion(herramienta, entrada):
        print(SOLO_LA_PERSONA, file=sys.stderr)
        return 2

    if herramienta in {"Edit", "Write", "MultiEdit"}:
        ruta = entrada.get("file_path", "")
        if not ARCHIVOS_DEPENDENCIAS.match(Path(ruta).name):
            return 0
        if herramienta == "Write":
            actual = Path(ruta).read_text(encoding="utf-8", errors="ignore") if Path(ruta).is_file() else ""
            nuevos = agregados(actual, entrada.get("content", ""))
        elif herramienta == "Edit":
            nuevos = agregados(entrada.get("old_string", ""), entrada.get("new_string", ""))
        else:
            edits = entrada.get("edits") or []
            nuevos = agregados("\n".join(e.get("old_string", "") for e in edits),
                               "\n".join(e.get("new_string", "") for e in edits))
    elif herramienta == "Bash":
        comando = entrada.get("command", "")
        for parte in re.split(r"&&|\|\||;|\|", comando):
            if INSTALACION.search(parte):
                nuevos += [n for n, rx in PAQUETES.items() if rx.search(parte)]

    pendientes = sorted(set(nuevos) - aprobados(raiz))
    if pendientes:
        print(
            f"Bloqueado: agregar {', '.join(pendientes)} requiere aprobación de licencia. "
            "Ultralytics es AGPL-3.0 (también los pesos entrenados); rfdetr[plus] no es Apache. "
            "Usa una alternativa Apache (RF-DETR Nano–Large sin [plus]) o pide a la persona que registre "
            "la aprobación en LICENSES.md con una línea 'APROBADO: <paquete> — <licencia y quién aprobó>'. "
            "Ver la skill licencias-vision.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
