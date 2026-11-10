"""PreToolUse: impide que Claude modifique el evaluador y los splits.

Rutas protegidas: las de `.claude/ml-vision.json` ({"rutas_protegidas": ["eval/", ...]}).
Sin ese archivo, se protegen `eval/`, `splits/` y `data/splits/`, solo si existen.
El propio `.claude/ml-vision.json` también queda protegido: si el agente pudiera
cambiarlo, vaciaría la lista (o crearía una vacía) y después escribiría en `eval/`.

Bloquea Edit/Write/MultiEdit/NotebookEdit sobre esas rutas y comandos de Bash que
escriban en ellas (redirecciones, rm, mv, tee, sed -i, cp hacia ellas...). En Bash
las rutas relativas parten del cwd de la sesión y siguen los `cd`; también se
revisa lo que corre dentro de `bash -c` y `eval`. Cada archivo se compara con las
rutas protegidas del proyecto y con las de su propio worktree de git. Leer está
permitido. Ante un comando que no se puede analizar y menciona una ruta
protegida, bloquea (falla cerrado).
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

POR_DEFECTO = ["eval/", "splits/", "data/splits/"]
CONFIG = Path(".claude", "ml-vision.json")
ESCRIBEN = {"rm", "rmdir", "mv", "tee", "truncate", "touch", "chmod", "chown", "ln", "dd", "shred", "unlink"}
DESTINO_AL_FINAL = {"cp", "rsync", "install"}
PREFIJOS = {"sudo", "env", "command", "time", "nohup"}
SHELLS = {"bash", "sh", "zsh", "dash"}
PUNTUACION = "();<>|&`\n"
# shlex junta signos seguidos (");", "&&\n"); esto los separa en operadores de bash.
OPERADOR = re.compile(r"&>>|&>|>>|>\||>&|<>|<<<|<<|&&|\|\||\|&|;;|[;&|()<>`\n]")
SALIDA = {">", ">>", ">|", "&>", "&>>", ">&", "<>"}
ENTRADA = {"<", "<<", "<<<"}


def rutas_protegidas(raiz: Path) -> list[Path]:
    config = raiz / CONFIG
    if config.is_file():
        try:
            rutas = json.loads(config.read_text()).get("rutas_protegidas", [])
        except (json.JSONDecodeError, AttributeError):
            rutas = POR_DEFECTO  # config rota: proteger lo de siempre
        protegidas = [normalizar(raiz, r) for r in rutas]
    else:
        protegidas = [normalizar(raiz, r) for r in POR_DEFECTO if (raiz / r).exists()]
    if protegidas or config.is_file():
        protegidas.append(normalizar(raiz, str(CONFIG)))
    return protegidas


def normalizar(raiz: Path, ruta: str) -> Path:
    p = Path(ruta).expanduser()
    if not p.is_absolute():
        p = raiz / p
    return Path(os.path.normpath(os.path.realpath(p)))


def protegida(ruta: Path, protegidas: list[Path]) -> Path | None:
    for base in protegidas:
        if ruta == base or base in ruta.parents:
            return base
    return None


def raiz_git(ruta: Path) -> Path | None:
    """Carpeta del repo o worktree de git que contiene la ruta (la que tiene `.git`)."""
    for d in [ruta, *ruta.parents]:
        if (d / ".git").exists():
            return d
    return None


def tokens_bash(comando: str) -> list[str] | None:
    """Palabras y operadores del comando. None si no se pudo analizar."""
    # Como en bash: barra invertida + salto de línea une las líneas, y el salto de línea separa
    # comandos. Sin comentarios: shlex se come el salto de línea que cierra un `# ...`.
    lex = shlex.shlex(comando.replace("\\\n", " "), posix=True, punctuation_chars=PUNTUACION)
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""
    try:
        crudos = list(lex)
    except ValueError:
        return None
    tokens: list[str] = []
    for t in crudos:
        tokens += OPERADOR.findall(t) if t and set(t) <= set(PUNTUACION) else [t]
    return tokens


def objetivos_bash(comando: str, cwd: Path) -> list[Path] | None:
    """Rutas en las que el comando escribiría, ya resueltas. None si no se pudo analizar."""
    tokens = tokens_bash(comando)
    if tokens is None:
        return None
    objetivos: list[Path] = []
    actual = cwd
    pila: list[Path] = []  # directorio de afuera de cada subshell abierto
    en_backtick = False
    segmento: list[str] = []
    i = 0
    while i <= len(tokens):
        tok = tokens[i] if i < len(tokens) else ";"  # un separador al final cierra el último segmento
        i += 1
        if not OPERADOR.fullmatch(tok):
            segmento.append(tok)
            continue
        if tok in SALIDA or tok in ENTRADA:  # el token siguiente es el archivo de la redirección
            if i < len(tokens) and not OPERADOR.fullmatch(tokens[i]):
                if tok in SALIDA:
                    objetivos.append(normalizar(actual, tokens[i]))
                i += 1
            continue
        # Separador: el segmento se analiza con el directorio de ese momento.
        seg = sin_prefijos(segmento)
        segmento = []
        scripts = scripts_internos(seg)
        if seg[:1] == ["cd"]:
            destinos = [a for a in seg[1:] if not a.startswith("-")]
            # Un destino desconocido (variable, $(...), `cd -`, `cd` solo) no mueve el directorio:
            # así las rutas se siguen revisando desde donde estaban, como antes de seguir los cd.
            if destinos and "$" not in destinos[0]:
                actual = normalizar(actual, destinos[0])
        elif scripts is not None:
            for script in scripts:
                internos = objetivos_bash(script, actual)
                if internos is None:
                    return None
                objetivos += internos
        else:
            objetivos += [normalizar(actual, a) for a in objetivos_segmento(seg)]
        if tok == "(" or (tok == "`" and not en_backtick):
            pila.append(actual)
        elif tok in {")", "`"} and pila:
            actual = pila.pop()  # el cd de adentro no cambia el directorio de afuera
        if tok == "`":
            en_backtick = not en_backtick
    return objetivos


def sin_prefijos(seg: list[str]) -> list[str]:
    while seg and (("=" in seg[0] and not seg[0].startswith("-")) or seg[0] in PREFIJOS):
        seg = seg[1:]
    return seg


def scripts_internos(seg: list[str]) -> list[str] | None:
    """Textos que el segmento corre como comandos: `bash -c '...'` (y sh, zsh, dash) o `eval ...`."""
    cmd = Path(seg[0]).name if seg else ""
    if cmd == "eval":
        return [" ".join(seg[1:])]
    if cmd in SHELLS and any(a.startswith("-") and not a.startswith("--") and "c" in a for a in seg[1:]):
        # Todos los argumentos que no son opciones: así `-o pipefail -c '...'` no esconde el script.
        return [a for a in seg[1:] if not a.startswith("-")]
    return None


def objetivos_segmento(seg: list[str]) -> list[str]:
    if not seg:
        return []
    cmd = Path(seg[0]).name
    args = [a for a in seg[1:] if not a.startswith("-")]
    if cmd in ESCRIBEN:
        return args
    if cmd in DESTINO_AL_FINAL:
        return args[-1:]
    if cmd == "sed" and any(a.startswith("-i") or a == "--in-place" for a in seg[1:]):
        return args
    if cmd == "git" and seg[1:2] in (["checkout"], ["restore"], ["rm"], ["mv"]):
        return args[1:]
    return []


def main() -> int:
    try:
        datos = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    raiz = Path(os.environ.get("CLAUDE_PROJECT_DIR") or datos.get("cwd") or ".")
    cwd = Path(datos.get("cwd") or raiz)
    protegidas = rutas_protegidas(raiz)
    if not protegidas:
        return 0

    herramienta = datos.get("tool_name", "")
    entrada = datos.get("tool_input") or {}
    candidatas: list[Path] = []

    if herramienta in {"Edit", "Write", "MultiEdit", "NotebookEdit"}:
        ruta = entrada.get("file_path") or entrada.get("notebook_path")
        if ruta:
            candidatas = [normalizar(cwd, ruta)]
    elif herramienta == "Bash":
        comando = entrada.get("command", "")
        objetivos = objetivos_bash(comando, normalizar(cwd, "."))
        if objetivos is None:
            raiz_real = normalizar(raiz, ".")
            menciona = [str(b.relative_to(raiz_real)) if raiz_real in b.parents else str(b) for b in protegidas]
            if any(m.rstrip("/") in comando for m in menciona):
                print(
                    "Comando no analizable que menciona una ruta protegida del evaluador; bloqueado.", file=sys.stderr
                )
                return 2
            return 0
        candidatas = objetivos

    for c in candidatas:
        # También la copia de las rutas protegidas en el worktree donde está el archivo.
        propia = raiz_git(c)
        base = protegida(c, protegidas + (rutas_protegidas(propia) if propia else []))
        if base and base.parts[-2:] == CONFIG.parts:
            print(
                f"Bloqueado: '{c}' es la configuración que define qué protege este hook; solo la cambia "
                "la persona. Pídele el cambio.",
                file=sys.stderr,
            )
            return 2
        if base:
            print(
                f"Bloqueado: '{c}' está bajo '{base}', que es el evaluador o los splits protegidos. "
                "La métrica oficial no la cambia el agente. Para proponer una división nueva, escríbela "
                "fuera (por ejemplo `splits_propuesta/manifest.csv`), verifícala con la skill division-sin-fuga "
                "y pídele a la persona que la mueva. Para otro cambio, pídeselo a ella; edita "
                "`.claude/ml-vision.json` o el archivo a mano.",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
