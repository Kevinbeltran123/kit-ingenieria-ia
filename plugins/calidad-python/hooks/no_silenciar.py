"""PreToolUse: solo la persona silencia reglas.

Bloquea que Claude agregue en un .py o .pyi un comentario que apaga un sensor para una línea,
un bloque o el archivo: `# noqa`, `# ruff: noqa`, `# ruff: disable[...]`, `# type: ignore`,
`# ty: ignore`, `# pyright: ...` y `# mypy: ...` (salvo `strict`), `# pragma: no cover`,
`no branch` y `no mutate`, `# nosec`, `# nosemgrep` y `# pylint: disable`. Compara el archivo
entero antes y después del cambio: quitar una excepción, o editar o mover una línea que ya la
tenía, pasa; agregar una o cambiar su texto (por ejemplo, sumarle una regla) se bloquea.

Lo mismo con lo que hace que pytest dé por buena una prueba que no pasó, en cualquier .py: skip y
xfail (también `xfail(strict=True)`, que deja la suite en verde mientras la prueba falla),
`skipif(True)`, `pytest.skip()`, `SkipTest`, `pytest.exit(returncode=0)`, `os._exit(0)` y
`outcome = "passed"`. Un `skipif` o un `unittest.skipIf/skipUnless` nuevo no se bloquea: se le
pregunta a la persona, porque saltar una prueba sin GPU o en otro sistema es legítimo pero deja
código sin probar ahí. `pytest.importorskip` pasa.

En Bash bloquea las opciones que silencian de una vez todo lo que hoy falla (`ruff --add-noqa`,
`ty --add-ignore`, `ty --update-baseline`, `complexipy --snapshot-create`, `vulture
--make-whitelist`) y los comandos que escriben uno de esos comentarios en un .py con >, >>, tee,
sed -i o perl -i. Lo que va entre comillas cuenta como texto: mencionarlo en un mensaje de
commit no es correrlo.

La configuración de los sensores también se los apaga: sumar "C901" al `ignore` de ruff, subir
`max-complexity`, agregar carpetas a `extend-exclude` o `addopts = "--deselect ..."` a pytest. Por eso
todo cambio en las secciones de calidad del pyproject.toml ([tool.ruff*], [tool.ty*], [tool.pytest*],
[tool.coverage*], [tool.importlinter*], [tool.mypy*], [tool.vulture], [tool.complexipy], [tool.deptry],
[tool.pyright]) o en un archivo de configuración (ruff.toml, pytest.ini, .coveragerc, conftest.py,
.pre-commit-config.yaml...) se le pregunta a la persona, también al crearlo: un ruff.toml o un
pytest.ini nuevo reemplaza la configuración del pyproject.toml. Por terminal se pregunta si un >, tee,
sed -i o perl -i escribe en uno de esos archivos.

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
    r"noqa\b",  # ruff, flake8, complexipy: una línea
    r"(?:ruff|flake8):\s*(?:noqa|disable)\b",  # el archivo entero o un bloque
    r"type:\s*ignore\b",  # todo verificador de tipos (PEP 484)
    r"ty:\s*ignore\b",
    r"(?:pyright|mypy):\s*(?!strict\b)\S",  # ignore[...] o configuración del archivo
    r"pragma[:\s]?\s*no\s*(?:cover|branch|mutate)\b",  # coverage y mutmut
    r"nosec\b",
    r"nosemgrep\b",
    r"pylint:\s*disable\b",
]
EXCEPCION = re.compile(r"#\s*(?:" + "|".join(MARCAS) + r")[^\n]*", re.IGNORECASE)
SALTOS = [
    r"(?<![\w.])(?:pytest\.)?mark\.(?:skip|xfail)\b",  # decorador, pytestmark o marks=
    r"(?<![\w.])(?:pytest\.)?mark\.skipif\(\s*(?:True|1)\s*[,)]",  # un skip disfrazado
    r"(?<![\w.])pytest\.(?:skip|xfail)\s*\(|\bskip\.Exception\b",
    r"\bSkipTest\b|\.skipTest\s*\(|@(?:unittest\.)?(?:skip|expectedFailure)\b",
    r"(?<![\w.])pytest\.exit\([^\n]*returncode\s*=\s*0\b|\bos\._exit\s*\(\s*0\s*\)",  # salir en verde
    r"\.outcome\s*=\s*[\"']passed[\"']",  # reportar como pasada una que falló
]
SALTO = re.compile(r"(?:" + "|".join(SALTOS) + r")[^\n]*")
CONDICIONAL = re.compile(r"(?<![\w.])(?:(?:pytest\.)?mark\.skipif|(?:unittest\.)?skip(?:If|Unless))\b[^\n]*")
EN_BLOQUE = {"--add-noqa", "--add-ignore", "--update-baseline", "--snapshot-create", "--make-whitelist"}
REDIRECCIONES = {">", ">>", ">|", "&>", "&>>"}
PUNTUACION = set("();<>|&")
PYTHON = (".py", ".pyi")
CALIDAD = re.compile(
    r"tool\.(?:(?:ruff|ty|pytest|coverage|importlinter|mypy)(?:\..+)?|vulture|complexipy|deptry|pyright)"
)
CONFIGURACION = {
    "ruff.toml",
    ".ruff.toml",
    "ty.toml",
    "pytest.ini",
    ".coveragerc",
    ".importlinter",
    "mypy.ini",
    ".mypy.ini",
    "pyrightconfig.json",
    "conftest.py",
    ".pre-commit-config.yaml",
}
ENCABEZADO = re.compile(r"(?m)^[ \t]*(\[\[?[^\]\n]+\]\]?)")
PERMITIR = "CALIDAD_PYTHON_PERMITIR_SILENCIAR"
CONSEJO = (
    "Corrige el código para que cumpla la regla o pase la prueba. Si la prueba depende del entorno (GPU, "
    "sistema operativo, una dependencia opcional), usa `pytest.importorskip` o `@pytest.mark.skipif(<condición>, "
    "reason=...)`. Si es un falso positivo, explícale a la persona por qué y dile qué agregar y en qué línea: lo "
    "agrega ella. Aunque te lo pida, este hook no te deja."
)

AFLOJAR = (
    "Así se puede aflojar una regla sin que se note (un ignore, max-complexity, un exclude, addopts con "
    "--deselect). Confirma solo si tú pediste este cambio."
)


def excepciones(texto: str) -> Counter:
    return Counter(m.group(0).rstrip() for rx in (EXCEPCION, SALTO) for m in rx.finditer(texto))


def condicionales(texto: str) -> Counter:
    return Counter(m.group(0).rstrip() for m in CONDICIONAL.finditer(texto))


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


def agregadas(herramienta: str, entrada: dict) -> tuple[list[str], list[str]]:
    """(excepciones y saltos que el cambio agrega, saltos condicionales que agrega) en un .py o .pyi."""
    if not str(entrada.get("file_path") or "").endswith(PYTHON):
        return [], []
    antes, despues = archivo_antes_y_despues(herramienta, entrada)
    return (
        [*(excepciones(despues) - excepciones(antes)).elements()],
        [*(condicionales(despues) - condicionales(antes)).elements()],
    )


def secciones(texto: str) -> dict[str, list[str]]:
    """El texto de cada sección de un .toml o .ini, por encabezado; "" es lo que va antes del primero."""
    partes: dict[str, list[str]] = {}
    encabezado, inicio = "", 0
    for m in ENCABEZADO.finditer(texto):
        partes.setdefault(encabezado, []).append(texto[inicio : m.start()].strip())
        encabezado, inicio = m.group(1), m.end()
    partes.setdefault(encabezado, []).append(texto[inicio:].strip())
    return partes


def es_de_calidad(encabezado: str) -> bool:
    """`[tool.ruff.lint]` y `[[tool.importlinter.contracts]]` sí; `[tool.typos]` no."""
    return bool(CALIDAD.fullmatch(encabezado.strip("[]").replace(" ", "")))


def configuracion_cambiada(herramienta: str, entrada: dict) -> list[str]:
    """Las secciones de configuración de los sensores que el cambio toca; vacía si no toca ninguna."""
    nombre = Path(str(entrada.get("file_path") or "")).name
    if nombre != "pyproject.toml" and nombre not in CONFIGURACION:
        return []
    antes, despues = archivo_antes_y_despues(herramienta, entrada)
    if antes == despues:
        return []
    a, d = secciones(antes), secciones(despues)
    cambiadas = [s for s in dict.fromkeys([*a, *d]) if a.get(s) != d.get(s)]
    if nombre == "pyproject.toml":
        return [s for s in cambiadas if es_de_calidad(s)]
    if nombre.endswith((".py", ".yaml", ".json")) or cambiadas == [""]:
        return ["todo el archivo"]
    return [s or "lo de antes de la primera sección" for s in cambiadas]


def preguntar(motivo: str) -> None:
    salida = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": motivo,
        }
    }
    print(json.dumps(salida, ensure_ascii=False))


def palabras(comando: str) -> list[str]:
    """Palabras del comando: lo que va entre comillas es una sola, y >, |, ; quedan aparte."""
    lex = shlex.shlex(comando, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ""
    try:
        return list(lex)
    except ValueError:  # comillas sin cerrar
        return comando.split()


def es_python(ruta: str) -> bool:
    return ruta.endswith(PYTHON)


def es_configuracion(ruta: str) -> bool:
    return Path(ruta).name in CONFIGURACION or Path(ruta).name == "pyproject.toml"


def escribe_en(tokens: list[str], destino) -> str | None:
    """El archivo que cumple `destino` y en el que escribe el comando con >, tee, sed -i o perl -i."""
    for i, t in enumerate(tokens):
        if t in REDIRECCIONES and i + 1 < len(tokens) and destino(tokens[i + 1]):
            return tokens[i + 1]
        argumentos = []  # los del mismo comando simple, hasta el siguiente ;, | o >
        for a in tokens[i + 1 :]:
            if a and set(a) <= PUNTUACION:
                break
            argumentos.append(a)
        nombre = Path(t).name
        en_sitio = nombre == "tee" or (
            nombre in {"sed", "gsed", "perl"}
            and any(
                a.startswith("--in-place") or (a.startswith("-") and not a.startswith("--") and "i" in a)
                for a in argumentos
            )
        )
        if en_sitio:
            for a in argumentos:
                if destino(a):
                    return a
    return None


def silencia_por_terminal(comando: str) -> str | None:
    tokens = palabras(comando)
    for t in tokens:
        if t.split("=", 1)[0] in EN_BLOQUE:
            return f"`{t}` silencia de una vez todo lo que hoy falla"
    if (EXCEPCION.search(comando) or SALTO.search(comando)) and escribe_en(tokens, es_python):
        return (
            "el comando escribe una excepción en un .py (por terminal no se distingue si la agrega o la "
            "quita: para quitarla, usa Edit)"
        )
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
        nuevas, dudosas = agregadas(herramienta, entrada)
        if nuevas:
            lista = "\n".join(f"  {c[:120]}" for c in nuevas[:5])
            print(
                f"Bloqueado: solo la persona agrega excepciones a las reglas o salta pruebas. Este cambio agrega en "
                f"{entrada.get('file_path')}:\n{lista}\n{CONSEJO}",
                file=sys.stderr,
            )
            return 2
        motivos = []
        if dudosas:
            motivos.append(
                f"calidad-python: el cambio agrega en {entrada.get('file_path')} una prueba que se salta según "
                f"una condición: {'; '.join(c[:120] for c in dudosas[:3])}. Confirma solo si la condición es del "
                "entorno (GPU, sistema operativo, una dependencia opcional) y no una forma de esquivar una prueba "
                "que falla."
            )
        tocadas = configuracion_cambiada(herramienta, entrada)
        if tocadas:
            motivos.append(
                f"calidad-python: el cambio toca la configuración de los sensores en {entrada.get('file_path')}: "
                f"{', '.join(tocadas[:5])}. {AFLOJAR}"
            )
        if motivos:
            preguntar(" ".join(motivos))
    elif herramienta == "Bash":
        comando = entrada.get("command", "")
        motivo = silencia_por_terminal(comando)
        if motivo:
            print(f"Bloqueado: solo la persona agrega excepciones a las reglas: {motivo}.\n{CONSEJO}", file=sys.stderr)
            return 2
        archivo = escribe_en(palabras(comando), es_configuracion)
        if archivo:
            preguntar(
                f"calidad-python: el comando escribe por terminal en {archivo}, la configuración de los sensores, "
                f"y por terminal no se ve qué sección cambia. {AFLOJAR}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
