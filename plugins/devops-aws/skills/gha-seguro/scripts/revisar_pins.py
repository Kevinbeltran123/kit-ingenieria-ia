"""Revisa workflows de GitHub Actions: todo `uses:` fijado por SHA y `permissions:` declarado.

Uso: python3 revisar_pins.py [carpeta .github o archivo .yml ...]
Sale con 1 si encuentra problemas, 0 si todo está bien.
"""

import re
import sys
from pathlib import Path

USES = re.compile(r"^\s*(?:-\s*)?uses:\s*['\"]?([^'\"\s#]+)")
SHA = re.compile(r"@[0-9a-f]{40}$")
DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$")


def archivos(rutas: list[str]) -> list[Path]:
    encontrados = []
    for r in map(Path, rutas):
        if r.is_dir():
            encontrados += sorted(p for p in r.rglob("*") if p.suffix in (".yml", ".yaml"))
        elif r.exists():
            encontrados.append(r)
    return encontrados


def revisar(ruta: Path) -> list[str]:
    problemas = []
    lineas = ruta.read_text().splitlines()
    for n, linea in enumerate(lineas, 1):
        m = USES.match(linea)
        if not m:
            continue
        ref = m.group(1)
        if ref.startswith("./"):
            continue
        if ref.startswith("docker://"):
            if not DIGEST.search(ref):
                problemas.append(f"{ruta}:{n}: imagen sin digest sha256: {ref}")
        elif not SHA.search(ref):
            problemas.append(f"{ruta}:{n}: action sin SHA de 40 caracteres: {ref}")

    es_workflow = "workflows" in ruta.parts
    if es_workflow and not any(re.match(r"^permissions:", l) for l in lineas):
        problemas.append(f"{ruta}: falta `permissions:` a nivel de workflow")
    return problemas


def main(argv: list[str]) -> int:
    rutas = archivos(argv or [".github"])
    problemas = [p for r in rutas for p in revisar(r)]
    for p in problemas:
        print(p)
    if problemas:
        print(f"\n{len(problemas)} problema(s). Para fijar por SHA: `pinact run`.")
        return 1
    print(f"OK: {len(rutas)} archivo(s) revisado(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
