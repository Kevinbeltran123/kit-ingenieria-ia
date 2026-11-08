"""Revisa la cadena de suministro de un repo Python y resume los hallazgos.

Pasos (solo los que apliquen): lock al día (uv lock --check), enfriamiento
`exclude-newer` configurado, pip-audit, osv-scanner, gitleaks y zizmor.
Sale con 1 si algún paso falla, falta una protección básica o falta una
herramienta: lo que no se revisó no cuenta como OK.

Uso: python3 suministro.py [raiz]
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

MAX_LINEAS = 20


def buscar_herramienta(raiz: Path, nombre: str) -> str | None:
    local = raiz / ".venv" / "bin" / nombre
    return str(local) if local.exists() else shutil.which(nombre)


def enfriamiento_configurado(pyproject: str) -> bool:
    """True si [tool.uv] fija exclude-newer en una línea sin comentar.

    Va línea por línea porque tomllib no existe en Python 3.9. `[tool.uv.pip]` no cuenta:
    solo aplica a `uv pip`, no al lock.
    """
    tabla = ""
    for linea in pyproject.splitlines():
        linea = linea.strip()
        if linea.startswith("["):
            tabla = linea.split("#", 1)[0].strip()
        elif tabla == "[tool.uv]" and re.match(r"exclude-newer\s*=", linea):
            return True
    return False


def pasos(raiz: Path) -> tuple[list[tuple[str, list[str]]], list[str], list[str]]:
    """Devuelve (pasos a correr, avisos de configuración, herramientas faltantes)."""
    lista, avisos, faltan = [], [], []
    pyproject = raiz / "pyproject.toml"
    texto = pyproject.read_text() if pyproject.exists() else ""

    uv = buscar_herramienta(raiz, "uv")
    if (raiz / "uv.lock").exists() and uv:
        lista.append(("uv lock --check", [uv, "lock", "--check"]))
    elif (raiz / "uv.lock").exists():
        faltan.append("uv")
    elif pyproject.exists():
        avisos.append("No hay uv.lock: las dependencias no están fijadas con hashes.")
    if pyproject.exists() and not enfriamiento_configurado(texto):
        avisos.append('Falta `exclude-newer = "7 days"` en [tool.uv]: se instalarían versiones recién publicadas.')

    # Sin argumentos, pip-audit revisa el entorno donde está instalado: uno global (pipx,
    # Homebrew) revisaría sus propias dependencias y no las del proyecto.
    pip_audit = raiz / ".venv" / "bin" / "pip-audit"
    if pip_audit.exists():
        lista.append(("pip-audit", [str(pip_audit)]))
    else:
        faltan.append("pip-audit (en el .venv: uv add --dev pip-audit)")

    for nombre, args in [
        ("osv-scanner", ["scan", "source", "-r", "."]),
        ("gitleaks", ["git", "--no-banner", "."]),
    ]:
        herramienta = buscar_herramienta(raiz, nombre)
        if herramienta:
            lista.append((nombre, [herramienta, *args]))
        else:
            faltan.append(nombre)

    if (raiz / ".github" / "workflows").is_dir():
        zizmor = buscar_herramienta(raiz, "zizmor")
        if zizmor:
            lista.append(("zizmor", [zizmor, ".github/workflows"]))
        else:
            faltan.append("zizmor")
    return lista, avisos, faltan


def main() -> int:
    raiz = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    lista, avisos, faltan = pasos(raiz)
    fallos = 0
    for nombre, cmd in lista:
        r = subprocess.run(cmd, cwd=raiz, capture_output=True, text=True)
        if r.returncode == 0:
            print(f"OK    {nombre}")
            continue
        fallos += 1
        print(f"FALLA {nombre}")
        for linea in (r.stdout + r.stderr).strip().splitlines()[-MAX_LINEAS:]:
            print(f"      {linea}")
    for aviso in avisos:
        print(f"AVISO {aviso}")
    if faltan:
        print(f"\nNo instalados (no se revisó): {', '.join(faltan)}")
    if not lista:
        print("\nNada se revisó: instala las herramientas de arriba y vuelve a correrlo.")
        return 1
    print(f"\n{len(lista) - fallos}/{len(lista)} pasos OK, {len(avisos)} avisos, {len(faltan)} sin revisar")
    return 1 if fallos or avisos or faltan else 0


if __name__ == "__main__":
    sys.exit(main())
