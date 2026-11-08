"""Repos de git temporales y utilidades para probar el explicador."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
SCRIPTS = PLUGIN / "skills" / "explicar-cambios" / "scripts"
HOOK = PLUGIN / "hooks" / "exigir_explicacion.py"
# Aislado de la configuración de git de quien corre las pruebas (hooks, firma, alias).
ENV = {k: v for k, v in os.environ.items() if k != "EXPLICADOR_DESACTIVAR"}
ENV.update({"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"})

VIEJO = '''def sumar(a, b):
    return a + b


def restar(a, b):
    return a - b
'''
NUEVO = '''def sumar(a, b):
    """Suma dos números."""
    return a + b


def restar(a, b):
    return a - b


def multiplicar(a, b):
    return a * b
'''


def git(raiz: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=raiz, env=ENV, check=True, capture_output=True, text=True).stdout.strip()


def correr(script: Path, raiz: Path, *args: str, entrada: str | None = None, env: dict | None = None):
    return subprocess.run([sys.executable, "-I", str(script), *args], cwd=raiz, input=entrada,
                          capture_output=True, text=True, env={**ENV, **(env or {})})


def crear_repo(raiz: Path) -> Path:
    raiz.mkdir()
    git(raiz, "init", "-q", "-b", "main")
    git(raiz, "config", "user.email", "prueba@example.com")
    git(raiz, "config", "user.name", "Prueba")
    (raiz / "calc.py").write_text(VIEJO)
    (raiz / "uv.lock").write_text("version = 1\n")
    git(raiz, "add", ".")
    git(raiz, "commit", "-q", "-m", "base")
    git(raiz, "checkout", "-q", "-b", "feature/multiplicar")
    (raiz / "calc.py").write_text(NUEVO)
    (raiz / "uv.lock").write_text("version = 2\n")
    (raiz / "config.yml").write_text("nombre: calculadora\n")
    git(raiz, "add", ".")
    git(raiz, "commit", "-q", "-m", "multiplicar")
    return raiz


def carpeta(raiz: Path) -> Path:
    return raiz / ".explicaciones" / "feature_multiplicar"


def leer(raiz: Path, nombre: str) -> dict:
    return json.loads((carpeta(raiz) / nombre).read_text())


def completar(raiz: Path, alerta: dict | None = None) -> dict:
    """Llena textos.json como lo haría Claude: una nota por cada línea pedida."""
    textos = leer(raiz, "textos.json")
    textos["titulo"] = "Agrega multiplicar"
    textos["resumen"].update(problema="No se podía multiplicar.", solucion="Nueva función multiplicar.",
                             como_se_probo="pytest: 3 de 3")
    for paso in textos["pasos"]:
        paso["titulo"] = f"Paso {paso['id']}"
        paso["explicacion"] = "Qué hace el bloque y por qué cambió."
        paso["notas"] = {str(n): f"Nota de la línea {n}." for n in paso["lineas_nuevas"]}
        paso["notas_borradas"] = {str(n): f"Por qué se quitó la línea {n}." for n in paso["lineas_borradas"]}
    if alerta is not None:
        textos["pasos"][0]["alerta"] = alerta
    guardar(raiz, textos)
    return textos


def guardar(raiz: Path, textos: dict) -> None:
    (carpeta(raiz) / "textos.json").write_text(json.dumps(textos, ensure_ascii=False))
