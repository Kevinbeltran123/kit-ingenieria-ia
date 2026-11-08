"""Aplica las plantillas del kit a un repo sin sobrescribir nada.

Uso:
    python3 bin/adoptar.py /ruta/al/repo [--perfil base|datos|ml] [--dry-run]
                           [--marketplace-github OWNER/REPO [--ref REF]] [--sin-docker]

- Copia cada plantilla solo si el archivo no existe en el repo.
- Si el repo ya tiene .claude/settings.json, agrega lo que falte sin borrar ni cambiar valores.
- Con --dry-run solo muestra lo que haría.
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
PLANTILLAS = KIT / "plantillas"
MARKETPLACE = "kit-ingenieria-ia"

PLUGINS = {
    "base": ["calidad-python", "barreras", "flujo", "python-ingenieria"],
    "datos": ["calidad-python", "barreras", "flujo", "python-ingenieria", "datos-optimizacion", "devops-aws"],
    "ml": ["calidad-python", "barreras", "flujo", "python-ingenieria", "ml-vision", "devops-aws"],
}

COPIAS = [
    ("python/.pre-commit-config.yaml", ".pre-commit-config.yaml"),
    ("claude/CLAUDE.md", "CLAUDE.md"),
    ("github/workflows/ci.yml", ".github/workflows/ci.yml"),
    ("github/workflows/claude-review.yml", ".github/workflows/claude-review.yml"),
    ("github/dependabot.yml", ".github/dependabot.yml"),
]
DOCKER = [("docker/Dockerfile", "Dockerfile"), ("docker/.dockerignore", ".dockerignore")]


def settings_para(perfil: str, github: str | None, ref: str | None) -> dict:
    datos = json.loads((PLANTILLAS / "claude" / "settings.json").read_text())
    if github:
        fuente = {"source": "github", "repo": github}
        if ref:
            fuente["ref"] = ref
    else:
        fuente = {"source": "directory", "path": str(KIT)}
    datos["extraKnownMarketplaces"][MARKETPLACE]["source"] = fuente
    datos["enabledPlugins"] = {f"{p}@{MARKETPLACE}": True for p in PLUGINS[perfil]}
    return datos


def fusionar(existente: dict, nuevo: dict) -> tuple[dict, list[str]]:
    """Agrega a `existente` lo que falte de `nuevo`. Nunca cambia ni borra valores existentes."""
    resultado = copy.deepcopy(existente)
    agregados: list[str] = []

    def recorrer(destino: dict, origen: dict, ruta: str) -> None:
        for clave, valor in origen.items():
            camino = f"{ruta}.{clave}" if ruta else clave
            if clave not in destino:
                destino[clave] = copy.deepcopy(valor)
                agregados.append(camino)
            elif isinstance(destino[clave], dict) and isinstance(valor, dict):
                recorrer(destino[clave], valor, camino)
            elif isinstance(destino[clave], list) and isinstance(valor, list):
                for item in valor:
                    if item not in destino[clave]:
                        destino[clave].append(copy.deepcopy(item))
                        agregados.append(f"{camino}[+] {json.dumps(item, ensure_ascii=False)}")

    recorrer(resultado, nuevo, "")
    return resultado, agregados


def adoptar(repo: Path, perfil: str, dry_run: bool, github: str | None, ref: str | None,
            sin_docker: bool) -> list[str]:
    informe: list[str] = []
    prefijo = "[dry-run] " if dry_run else ""

    for origen, destino in COPIAS + ([] if sin_docker else DOCKER):
        objetivo = repo / destino
        if objetivo.exists():
            informe.append(f"ya existe, no se tocó: {destino}")
            continue
        informe.append(f"{prefijo}creado: {destino}")
        if not dry_run:
            objetivo.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(PLANTILLAS / origen, objetivo)

    nuevo = settings_para(perfil, github, ref)
    ruta_settings = repo / ".claude" / "settings.json"
    if ruta_settings.exists():
        existente = json.loads(ruta_settings.read_text())
        final, agregados = fusionar(existente, nuevo)
        if agregados:
            informe.append(f"{prefijo}fusionado: .claude/settings.json ({len(agregados)} cosas agregadas)")
            informe.extend(f"    + {a}" for a in agregados)
        else:
            informe.append("ya tenía todo: .claude/settings.json")
    else:
        final = nuevo
        informe.append(f"{prefijo}creado: .claude/settings.json (perfil {perfil})")
    if not dry_run:
        ruta_settings.parent.mkdir(parents=True, exist_ok=True)
        ruta_settings.write_text(json.dumps(final, indent=2, ensure_ascii=False) + "\n")
    return informe


PASOS = """
Pasos manuales siguientes:
  1. Copia del fragmento las secciones que falten en pyproject.toml:
       {fragmento}
     Cambia "app" por el paquete real y ajusta las capas de import-linter.
  2. uv sync && uvx prek install
  3. Rellena los huecos <...> de CLAUDE.md.
  4. Abre Claude Code en el repo, acepta la confianza de la carpeta e instala los plugins:
       claude plugin install <plugin>@kit-ingenieria-ia --scope project
  5. Para la revisión en CI: agrega el secreto ANTHROPIC_API_KEY al repo (o borra claude-review.yml).
  6. Revisa el diff antes de commitear: git status && git diff
"""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Aplica las plantillas del kit a un repo sin sobrescribir.")
    p.add_argument("repo", type=Path)
    p.add_argument("--perfil", choices=sorted(PLUGINS), default="base")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--marketplace-github", metavar="OWNER/REPO",
                   help="usar el kit desde GitHub en vez de la ruta local")
    p.add_argument("--ref", help="rama o tag del kit en GitHub")
    p.add_argument("--sin-docker", action="store_true")
    args = p.parse_args(argv)

    repo = args.repo.resolve()
    if not repo.is_dir():
        print(f"No existe la carpeta: {repo}", file=sys.stderr)
        return 1
    if args.ref and not args.marketplace_github:
        print("--ref solo tiene sentido con --marketplace-github", file=sys.stderr)
        return 1

    for linea in adoptar(repo, args.perfil, args.dry_run, args.marketplace_github, args.ref,
                         args.sin_docker):
        print(linea)
    print(PASOS.format(fragmento=PLANTILLAS / "python" / "pyproject.toml.fragmento"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
