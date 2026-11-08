"""PostToolUse: corre ruff sobre el archivo .py que Claude acaba de editar.

Corrige lo que se pueda, formatea y, si quedan errores, sale con 2 para que
Claude los vea. Además anota el archivo para que el hook de Stop sepa que
hubo cambios de Python en esta sesión.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def buscar_herramienta(raiz: Path, nombre: str) -> str | None:
    local = raiz / ".venv" / "bin" / nombre
    return str(local) if local.exists() else shutil.which(nombre)


def main() -> int:
    datos = json.load(sys.stdin)
    archivo = (datos.get("tool_input") or {}).get("file_path", "")
    if not archivo.endswith((".py", ".pyi")) or not Path(archivo).exists():
        return 0

    raiz = Path(os.environ.get("CLAUDE_PROJECT_DIR") or datos.get("cwd") or ".")

    sesion = re.sub(r"[^A-Za-z0-9_-]", "", datos.get("session_id", "")) or "sin-sesion"
    marcas = Path(tempfile.gettempdir()) / "claude-calidad-python"
    marcas.mkdir(exist_ok=True)
    with open(marcas / sesion, "a") as f:
        f.write(archivo + "\n")

    ruff = buscar_herramienta(raiz, "ruff")
    if ruff is None:
        return 0

    check = subprocess.run(
        [ruff, "check", "--fix", "--force-exclude", "--output-format", "concise", archivo],
        cwd=raiz, capture_output=True, text=True,
    )
    subprocess.run([ruff, "format", "--force-exclude", archivo], cwd=raiz, capture_output=True)

    if check.returncode != 0:
        print(f"ruff encontró errores que no pudo corregir solo:\n{check.stdout}{check.stderr}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
