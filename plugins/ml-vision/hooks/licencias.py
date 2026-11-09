"""PreToolUse: bloquea agregar dependencias con licencia restrictiva sin aprobación.

Vigila `ultralytics` (AGPL-3.0, alcanza también a los pesos entrenados) y
`rfdetr[plus]` (licencia no Apache). Se permite si `LICENSES.md` en la raíz del
proyecto tiene una línea como:

    APROBADO: ultralytics — licencia Enterprise n.º 123, legal (2026-11-07)

Revisa Edit/Write/MultiEdit en archivos de dependencias (también `requirements/*.txt`
y el bloque PEP 723 `# /// script` de un .py), en los Dockerfile y Containerfile (lo que
instalan sus RUN, también en forma exec o con heredoc, y la imagen de FROM) y, en Bash, los comandos que instalan
o ejecutan paquetes (pip, uv, uvx, `uv run --with`, pipx, poetry, conda, pixi), también
dentro de `bash -c` o `ssh`. Las comillas se respetan: un mensaje de commit o un grep
que menciona una instalación no es una instalación. Las líneas APROBADO: solo las
escribe la persona: si Claude intenta agregarlas a LICENSES.md (por edición o por
Bash), se bloquea.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

PAQUETES = {
    "ultralytics": re.compile(r"(?<![\w-])ultralytics(?![\w])", re.IGNORECASE),
    "rfdetr[plus]": re.compile(r"(?<![\w-])rfdetr\s*\[[^\]]*\bplus\b[^\]]*\]", re.IGNORECASE),
}
ARCHIVOS_DEPENDENCIAS = re.compile(
    r"^(pyproject\.toml|setup\.cfg|setup\.py|environment\.ya?ml|pixi\.toml|requirements[\w.-]*\.(txt|in))$"
)
PEP723 = re.compile(r"^# /// script\s*$(.*?)^# ///\s*$", re.MULTILINE | re.DOTALL)
DOCKERFILE = re.compile(r"^(?:dockerfile|containerfile)(?:[.-][\w.-]+)?$|\.(?:dockerfile|containerfile)$", re.IGNORECASE)
FORMA_EXEC = re.compile(r"^(\s*(?:RUN|CMD|ENTRYPOINT)\s+)(\[.*\])\s*$", re.IGNORECASE | re.MULTILINE)
IMAGEN = re.compile(r"^\s*FROM\s+(?:--\S+\s+)*(\S+)", re.IGNORECASE | re.MULTILINE)
INSTALADORES = {"pip", "pip3", "uv", "uvx", "poetry", "conda", "mamba", "micromamba", "pixi", "pipx"}
SHELLS = {"bash", "sh", "zsh", "dash"}
PUNTUACION = "();<>|&`\n"
OPCIONES_CON_PAQUETE = {"--with", "--with-editable", "--from", "--spec"}
CON_VALOR = OPCIONES_CON_PAQUETE | {"--python", "-p"}
INSTALAN = (["install"], ["add"], ["inject"], ["create"])
INSTALAN_2 = (["pip", "install"], ["tool", "install"], ["global", "install"])


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


def es_dependencias(ruta: Path) -> bool:
    return bool(ARCHIVOS_DEPENDENCIAS.match(ruta.name)) or (
        ruta.parent.name == "requirements" and ruta.suffix in {".txt", ".in"})


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


def segmentos(comando: str) -> list[list[str]]:
    """Comandos simples del texto de Bash, ya en palabras; lo que va entre comillas es una sola."""
    lex = shlex.shlex(comando.replace("\\\n", " "), posix=True, punctuation_chars=PUNTUACION)
    lex.whitespace = " \t\r"  # el salto de línea separa comandos
    lex.whitespace_split = True
    try:
        tokens = list(lex)
    except ValueError:  # comillas sin cerrar: separar por espacios
        tokens = re.sub(r"[;&|()`\n]", " ; ", comando).split()
    segs: list[list[str]] = [[]]
    for t in tokens:
        if t and set(t) <= set(PUNTUACION):
            segs.append([])
        else:
            segs[-1].append(t)
    return [s for s in segs if s]


def paquetes_que_instala(seg: list[str]) -> list[str]:
    """Palabras de `seg` (empieza por el instalador) que se instalarían o ejecutarían."""
    cmd, args = seg[0], seg[1:]
    if cmd == "uvx":  # uvx es `uv tool run`
        cmd, args = "uv", ["tool", "run", *args]
    valores = [v for o, v in zip(args, args[1:]) if o in OPCIONES_CON_PAQUETE]
    valores += [a.split("=", 1)[1] for a in args if a.split("=", 1)[0] in OPCIONES_CON_PAQUETE and "=" in a]
    sub = [a for a in args if not a.startswith("-")]
    if sub[:2] == ["tool", "run"] or (cmd == "pipx" and sub[:1] == ["run"]):
        # La herramienta es el primer argumento que no es opción ni valor de una; lo demás es suyo.
        resto = args[args.index("run") + 1:]
        herramienta = [a for o, a in zip(["-"] + resto, resto) if not a.startswith("-") and o not in CON_VALOR]
        return valores + herramienta[:1]
    if sub[:1] == ["run"]:
        return valores  # `uv run`, `poetry run`, `pixi run`: solo instalan lo de --with
    if sub[:1] in INSTALAN or sub[:2] in INSTALAN_2:
        return args
    return []


def restringidos_en_bash(comando: str) -> list[str]:
    """Paquetes restringidos que el comando instalaría o ejecutaría, donde sea que esté el instalador."""
    encontrados: list[str] = []
    for seg in segmentos(comando):
        for i, palabra in enumerate(seg):
            nombre, resto = os.path.basename(palabra), seg[i + 1:]
            if nombre == "ssh" or (nombre in SHELLS and any(
                    a.startswith("-") and not a.startswith("--") and "c" in a for a in resto)):
                # Lo que corren `bash -c '...'` o `ssh host '...'` es otro comando.
                for texto in (a for a in resto if not a.startswith("-")):
                    encontrados += restringidos_en_bash(texto)
            elif nombre == "eval":
                encontrados += restringidos_en_bash(" ".join(resto))
            elif nombre in INSTALADORES or (re.fullmatch(r"python[\d.]*", nombre) and resto[:2] == ["-m", "pip"]):
                instalador = [nombre, *resto] if nombre in INSTALADORES else ["pip", *resto[2:]]
                paquetes = paquetes_que_instala(instalador)
                encontrados += [n for n, rx in PAQUETES.items() if any(rx.search(p) for p in paquetes)]
    return encontrados


def restringidos_en_dockerfile(texto: str) -> list[str]:
    """Paquetes restringidos que traen los RUN (y CMD/ENTRYPOINT con `uv run --with`) y las imágenes de FROM."""
    def a_shell(m: re.Match) -> str:  # RUN ["pip", "install", "x"] -> RUN pip install x
        try:
            return m.group(1) + " ".join(shlex.quote(str(p)) for p in json.loads(m.group(2)))
        except (ValueError, TypeError):
            return m.group(0)
    texto = FORMA_EXEC.sub(a_shell, texto)
    # Las líneas que no son RUN no instalan nada, y las continuaciones y heredocs ya los lee segmentos().
    encontrados = restringidos_en_bash(texto)
    for imagen in IMAGEN.findall(texto):
        encontrados += [n for n, rx in PAQUETES.items() if rx.search(imagen)]
    return encontrados


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
        if DOCKERFILE.search(Path(ruta).name):
            antes, despues = (restringidos_en_dockerfile(t) for t in archivo_antes_y_despues(herramienta, entrada))
            nuevos = [n for n in set(despues) if despues.count(n) > antes.count(n)]
        elif Path(ruta).suffix == ".py" and not ARCHIVOS_DEPENDENCIAS.match(Path(ruta).name):
            # Dependencias del bloque PEP 723, que `uv run script.py` instala.
            antes, despues = archivo_antes_y_despues(herramienta, entrada)
            nuevos = agregados("\n".join(PEP723.findall(antes)), "\n".join(PEP723.findall(despues)))
        elif not es_dependencias(Path(ruta)):
            return 0
        elif herramienta == "Write":
            actual = Path(ruta).read_text(encoding="utf-8", errors="ignore") if Path(ruta).is_file() else ""
            nuevos = agregados(actual, entrada.get("content", ""))
        elif herramienta == "Edit":
            nuevos = agregados(entrada.get("old_string", ""), entrada.get("new_string", ""))
        else:
            edits = entrada.get("edits") or []
            nuevos = agregados("\n".join(e.get("old_string", "") for e in edits),
                               "\n".join(e.get("new_string", "") for e in edits))
    elif herramienta == "Bash":
        nuevos = restringidos_en_bash(entrada.get("command", ""))

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
