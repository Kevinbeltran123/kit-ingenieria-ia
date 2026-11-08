"""PreToolUse (Bash): antes de `gh pr create`, exige la explicación del cambio al día.

Deja pasar si .explicaciones/<rama>/ultimo.json es del commit actual (HEAD) y no tiene posibles
errores abiertos. Si falta, es de otro commit o marcó errores sin resolver, bloquea (exit 2) y le
dice a Claude qué hacer. Falla abierto: ante un error interno deja pasar, porque no es una barrera
de seguridad. Se desactiva con EXPLICADOR_DESACTIVAR=1 o con {"desactivar": true} en
.claude/explicador.json.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ABRIR_PR = re.compile(r"(^|[;&|()\s])gh\s+pr\s+create\b")
SKILL = "la skill explicar-cambios (plugin explicador)"


def git(cwd: str | Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=5)
    return r.stdout.strip() if r.returncode == 0 else ""


def carpeta_de_rama(rama: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", rama) or "sin-rama"


def bloquear(mensaje: str) -> int:
    print(f"explicador: {mensaje}", file=sys.stderr)
    return 2


def desactivado(raiz: Path) -> bool:
    if os.environ.get("EXPLICADOR_DESACTIVAR") == "1":
        return True
    config = raiz / ".claude" / "explicador.json"
    try:
        return config.is_file() and json.loads(config.read_text()).get("desactivar") is True
    except (ValueError, AttributeError):
        return False


def evaluar(datos: dict) -> int:
    if datos.get("tool_name") != "Bash":
        return 0
    if not ABRIR_PR.search((datos.get("tool_input") or {}).get("command", "")):
        return 0
    raiz_texto = git(datos.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or ".", "rev-parse", "--show-toplevel")
    if not raiz_texto:
        return 0
    raiz = Path(raiz_texto)
    if desactivado(raiz):
        return 0
    rama, head = git(raiz, "rev-parse", "--abbrev-ref", "HEAD"), git(raiz, "rev-parse", "HEAD")
    ultimo = raiz / ".explicaciones" / carpeta_de_rama(rama) / "ultimo.json"
    if not ultimo.is_file():
        return bloquear(f"antes de abrir el PR, genera la explicación del cambio con {SKILL}. "
                        "La persona necesita entender el cambio línea por línea antes de revisarlo.")
    info = json.loads(ultimo.read_text())
    if info.get("hasta") != head:
        hecha = str(info.get("hasta") or "cambios sin commit")[:10]
        return bloquear(f"la explicación es de {hecha} y HEAD es {head[:7]}. Vuelve a generarla con {SKILL}.")
    abiertos = [a for a in info.get("alertas", []) if a.get("tipo") == "bug" and a.get("estado") == "abierta"]
    if abiertos:
        lista = "\n".join(f"- {a.get('donde', '')}: {a.get('texto', '')}" for a in abiertos)
        return bloquear(f"la explicación marcó {len(abiertos)} posible(s) error(es) sin resolver:\n{lista}\n"
                        "Corrígelos y vuelve a generar la explicación, o pregúntale a la persona si los descarta.")
    return 0


def main() -> int:
    try:
        return evaluar(json.load(sys.stdin))
    except Exception:  # falla abierto: no es una barrera de seguridad
        return 0


if __name__ == "__main__":
    sys.exit(main())
