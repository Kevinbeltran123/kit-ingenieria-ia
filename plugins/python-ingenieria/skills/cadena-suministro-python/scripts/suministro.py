"""Revisa la cadena de suministro de un repo Python y resume los hallazgos.

Pasos (solo los que apliquen): lock al día (uv lock --check), enfriamiento
`exclude-newer` configurado, pip-audit, osv-scanner, gitleaks y zizmor.
Sale con 1 si algún paso falla o falta una protección básica.

Uso: python3 suministro.py [raiz]
"""

import shutil
import subprocess
import sys
from pathlib import Path

MAX_LINEAS = 20


def buscar_herramienta(raiz: Path, nombre: str) -> str | None:
    local = raiz / ".venv" / "bin" / nombre
    return str(local) if local.exists() else shutil.which(nombre)


def pasos(raiz: Path) -> tuple[list[tuple[str, list[str]]], list[str], list[str]]:
    """Devuelve (pasos a correr, avisos de configuración, herramientas faltantes)."""
    lista, avisos, faltan = [], [], []
    pyproject = raiz / "pyproject.toml"
    texto = pyproject.read_text() if pyproject.exists() else ""

    uv = buscar_herramienta(raiz, "uv")
    if (raiz / "uv.lock").exists() and uv:
        lista.append(("uv lock --check", [uv, "lock", "--check"]))
    elif pyproject.exists() and not (raiz / "uv.lock").exists():
        avisos.append("No hay uv.lock: las dependencias no están fijadas con hashes.")
    if pyproject.exists() and "exclude-newer" not in texto:
        avisos.append('Falta `exclude-newer = "7 days"` en [tool.uv]: se instalarían versiones recién publicadas.')

    for nombre, args in [
        ("pip-audit", []),
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
    print(f"\n{len(lista) - fallos}/{len(lista)} pasos OK, {len(avisos)} avisos")
    return 1 if fallos or avisos else 0


if __name__ == "__main__":
    sys.exit(main())
