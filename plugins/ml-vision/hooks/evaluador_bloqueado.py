"""PreToolUse: impide que Claude modifique el evaluador y los splits.

Rutas protegidas: las de `.claude/ml-vision.json` ({"rutas_protegidas": ["eval/", ...]}).
Sin ese archivo, se protegen `eval/`, `splits/` y `data/splits/`, solo si existen.

Bloquea Edit/Write/MultiEdit/NotebookEdit sobre esas rutas y comandos de Bash que
escriban en ellas (redirecciones, rm, mv, tee, sed -i, cp hacia ellas...). Leer
está permitido. Ante un comando que no se puede analizar y menciona una ruta
protegida, bloquea (falla cerrado).
"""

from __future__ import annotations

import json
import os
import shlex
import sys
from pathlib import Path

POR_DEFECTO = ["eval/", "splits/", "data/splits/"]
ESCRIBEN = {"rm", "rmdir", "mv", "tee", "truncate", "touch", "chmod", "chown", "ln", "dd", "shred", "unlink"}
DESTINO_AL_FINAL = {"cp", "rsync", "install"}
SEPARADORES = {";", "&&", "||", "|", "&", "(", ")"}
REDIRECCIONES = {">", ">>", ">|", "&>", "&>>", ">&"}


def rutas_protegidas(raiz: Path) -> list[Path]:
    config = raiz / ".claude" / "ml-vision.json"
    if config.is_file():
        try:
            rutas = json.loads(config.read_text()).get("rutas_protegidas", [])
        except (json.JSONDecodeError, AttributeError):
            rutas = POR_DEFECTO  # config rota: proteger lo de siempre
        return [normalizar(raiz, r) for r in rutas]
    return [normalizar(raiz, r) for r in POR_DEFECTO if (raiz / r).exists()]


def normalizar(raiz: Path, ruta: str) -> Path:
    p = Path(os.path.expanduser(ruta))
    if not p.is_absolute():
        p = raiz / p
    return Path(os.path.normpath(os.path.realpath(p)))


def protegida(ruta: Path, protegidas: list[Path]) -> Path | None:
    for base in protegidas:
        if ruta == base or base in ruta.parents:
            return base
    return None


def objetivos_bash(comando: str) -> list[str] | None:
    """Rutas en las que el comando escribiría. None si no se pudo analizar."""
    try:
        lex = shlex.shlex(comando, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:
        return None

    objetivos = []
    segmento: list[str] = []
    for i, tok in enumerate(tokens):
        if tok in REDIRECCIONES or (tok.endswith(">") and tok.rstrip(">").rstrip("&").isdigit()):
            if i + 1 < len(tokens):
                objetivos.append(tokens[i + 1])
            continue
        if tok in SEPARADORES:
            objetivos += objetivos_segmento(segmento)
            segmento = []
            continue
        segmento.append(tok)
    objetivos += objetivos_segmento(segmento)
    return objetivos


def objetivos_segmento(seg: list[str]) -> list[str]:
    while seg and ("=" in seg[0] and not seg[0].startswith("-") or seg[0] in {"sudo", "env", "command"}):
        seg = seg[1:]
    if not seg:
        return []
    cmd = os.path.basename(seg[0])
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
    protegidas = rutas_protegidas(raiz)
    if not protegidas:
        return 0

    herramienta = datos.get("tool_name", "")
    entrada = datos.get("tool_input") or {}
    candidatas: list[str] = []

    if herramienta in {"Edit", "Write", "MultiEdit", "NotebookEdit"}:
        ruta = entrada.get("file_path") or entrada.get("notebook_path")
        if ruta:
            candidatas = [ruta]
    elif herramienta == "Bash":
        comando = entrada.get("command", "")
        objetivos = objetivos_bash(comando)
        if objetivos is None:
            raiz_real = normalizar(raiz, ".")
            menciona = [str(b.relative_to(raiz_real)) if raiz_real in b.parents else str(b) for b in protegidas]
            if any(m.rstrip("/") in comando for m in menciona):
                print("Comando no analizable que menciona una ruta protegida del evaluador; bloqueado.", file=sys.stderr)
                return 2
            return 0
        candidatas = objetivos

    for c in candidatas:
        base = protegida(normalizar(raiz, c), protegidas)
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
