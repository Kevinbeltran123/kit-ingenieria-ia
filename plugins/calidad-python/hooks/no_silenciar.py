"""PreToolUse: solo la persona silencia reglas.

Bloquea que Claude agregue en un .py o .pyi un comentario que apaga un sensor para una línea,
un bloque o el archivo: `# noqa`, `# ruff: noqa`, `# ruff: disable[...]`, `# type: ignore`,
`# ty: ignore`, `# pyright: ...` y `# mypy: ...` (salvo `strict`), `# pragma: no cover`,
`no branch` y `no mutate`, `# nosec`, `# nosemgrep` y `# pylint: disable`. Compara el archivo
entero antes y después del cambio: quitar una excepción, o editar o mover una línea que ya la
tenía, pasa; agregar una o cambiar su texto (por ejemplo, sumarle una regla) se bloquea.

En Bash bloquea las opciones que silencian de una vez todo lo que hoy falla (`ruff --add-noqa`,
`ty --add-ignore`, `ty --update-baseline`, `complexipy --snapshot-create`, `vulture
--make-whitelist`) y los comandos que escriben uno de esos comentarios en un .py con >, >>, tee,
sed -i o perl -i. Lo que va entre comillas cuenta como texto: mencionarlo en un mensaje de
commit no es correrlo.

Si un falso positivo merece la excepción, Claude le dice a la persona cuál y en qué línea, y ella
la agrega. Para una sesión en la que sí quiere que Claude las agregue (la línea base al adoptar
ruff en un repo viejo, por ejemplo), la persona arranca Claude Code con
CALIDAD_PYTHON_PERMITIR_SILENCIAR=1. Falla abierto: es una guía de calidad, no una barrera de
seguridad.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from collections import Counter
from pathlib import Path

MARCAS = [
    r"noqa\b",                                         # ruff, flake8, complexipy: una línea
    r"(?:ruff|flake8):\s*(?:noqa|disable)\b",          # ruff: el archivo o un bloque
    r"type:\s*ignore\b",                               # todo verificador de tipos (PEP 484)
    r"ty:\s*ignore\b",
    r"(?:pyright|mypy):\s*(?!strict\b)\S",             # ignore[...] o configuración del archivo
    r"pragma[:\s]?\s*no\s*(?:cover|branch|mutate)\b",  # coverage y mutmut
    r"nosec\b",
    r"nosemgrep\b",
    r"pylint:\s*disable\b",
]
EXCEPCION = re.compile(r"#\s*(?:" + "|".join(MARCAS) + r")[^\n]*", re.IGNORECASE)
EN_BLOQUE = {"--add-noqa", "--add-ignore", "--update-baseline", "--snapshot-create", "--make-whitelist"}
REDIRECCIONES = {">", ">>", ">|", "&>", "&>>"}
PUNTUACION = set("();<>|&")
PYTHON = (".py", ".pyi")
PERMITIR = "CALIDAD_PYTHON_PERMITIR_SILENCIAR"
CONSEJO = ("Corrige el código para que cumpla la regla. Si es un falso positivo, explícale a la persona por qué "
           "y dile qué comentario agregar y en qué línea: lo agrega ella. Aunque te lo pida, este hook no te deja.")


def excepciones(texto: str) -> Counter:
    return Counter(m.group(0).rstrip() for m in EXCEPCION.finditer(texto))


def archivo_antes_y_despues(herramienta: str, entrada: dict) -> tuple[str, str]:
    """El archivo completo antes y después del cambio (Edit y MultiEdit traen solo fragmentos)."""
    ruta = Path(entrada.get("file_path", ""))
    antes = ruta.read_text(encoding="utf-8", errors="ignore") if ruta.is_file() else ""
    if herramienta == "Write":
        return antes, entrada.get("content", "")
    despues = antes
    for e in entrada.get("edits") or [entrada]:
        viejo, nuevo = e.get("old_string", ""), e.get("new_string", "")
        despues = despues.replace(viejo, nuevo) if e.get("replace_all") else despues.replace(viejo, nuevo, 1)
    return antes, despues


def agregadas(herramienta: str, entrada: dict) -> list[str]:
    if not str(entrada.get("file_path") or "").endswith(PYTHON):
        return []
    antes, despues = archivo_antes_y_despues(herramienta, entrada)
    return list((excepciones(despues) - excepciones(antes)).elements())


def palabras(comando: str) -> list[str]:
    """Palabras del comando: lo que va entre comillas es una sola, y >, |, ; quedan aparte."""
    lex = shlex.shlex(comando, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ""
    try:
        return list(lex)
    except ValueError:  # comillas sin cerrar
        return comando.split()


def escribe_en_un_py(tokens: list[str]) -> bool:
    for i, t in enumerate(tokens):
        if t in REDIRECCIONES and i + 1 < len(tokens) and tokens[i + 1].endswith(PYTHON):
            return True
        argumentos = []  # los del mismo comando simple, hasta el siguiente ;, | o >
        for a in tokens[i + 1:]:
            if a and set(a) <= PUNTUACION:
                break
            argumentos.append(a)
        nombre = os.path.basename(t)
        en_sitio = nombre == "tee" or (nombre in {"sed", "gsed", "perl"} and any(
            a.startswith("--in-place") or (a.startswith("-") and not a.startswith("--") and "i" in a)
            for a in argumentos))
        if en_sitio and any(a.endswith(PYTHON) for a in argumentos):
            return True
    return False


def silencia_por_terminal(comando: str) -> str | None:
    tokens = palabras(comando)
    for t in tokens:
        if t.split("=", 1)[0] in EN_BLOQUE:
            return f"`{t}` silencia de una vez todo lo que hoy falla"
    if EXCEPCION.search(comando) and escribe_en_un_py(tokens):
        return ("el comando escribe una excepción en un .py (por terminal no se distingue si la agrega o la "
                "quita: para quitarla, usa Edit)")
    return None


def main() -> int:
    try:
        datos = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if not isinstance(datos, dict) or os.environ.get(PERMITIR) == "1":
        return 0
    herramienta = datos.get("tool_name", "")
    entrada = datos.get("tool_input") or {}

    if herramienta in {"Edit", "Write", "MultiEdit"}:
        nuevas = agregadas(herramienta, entrada)
        if nuevas:
            lista = "\n".join(f"  {c[:120]}" for c in nuevas[:5])
            print(f"Bloqueado: solo la persona agrega excepciones a las reglas. Este cambio agrega en "
                  f"{entrada.get('file_path')}:\n{lista}\n{CONSEJO}", file=sys.stderr)
            return 2
    elif herramienta == "Bash":
        motivo = silencia_por_terminal(entrada.get("command", ""))
        if motivo:
            print(f"Bloqueado: solo la persona agrega excepciones a las reglas: {motivo}.\n{CONSEJO}",
                  file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
