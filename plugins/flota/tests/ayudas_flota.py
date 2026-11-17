"""Ayudas de las pruebas de la flota: un herdr y un cmux falsos que registran sus llamadas."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN / "skills" / "flota" / "scripts"
PUENTE = PLUGIN / "herdr" / "puente.py"
sys.path.insert(0, str(SCRIPTS))

# herdr falso: lee el estado de $FALSO_ESTADO (JSON), registra cada llamada en $FALSO_LLAMADAS y responde como herdr.
# El estado tiene "agentes": {nombre: {status, pane, pantallas: [texto, ...]}} y "caido": bool.
HERDR_FALSO = r"""#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
if args[:1] == ["--session"]:
    args = args[2:]
ruta = os.environ["FALSO_ESTADO"]
estado = json.load(open(ruta))
with open(os.environ["FALSO_LLAMADAS"], "a") as f:
    f.write(json.dumps(args) + "\n")
def guardar():
    json.dump(estado, open(ruta, "w"))
def ok(res):
    print(json.dumps({"id": "x", "result": res})); sys.exit(0)
def error(codigo, msg="falso"):
    sys.stderr.write(json.dumps({"id": "x", "error": {"code": codigo, "message": msg}})); sys.exit(1)
if estado.get("caido"):
    error("server_not_running")
ags = estado.setdefault("agentes", {})
g, c = (args + ["", ""])[:2]
if (g, c) == ("agent", "list"):
    ok({"agents": [{"name": n, "agent_status": a["status"], "pane_id": a.get("pane", "w9:p1"), "agent": a.get("kind", "claude")} for n, a in ags.items()]})
if (g, c) == ("agent", "get"):
    nombre = next((n for n, a in ags.items() if args[2] in (n, a.get("pane"))), None) or error("agent_not_found")
    a = ags[nombre]
    ok({"agent": {"name": nombre, "agent_status": a["status"], "pane_id": a.get("pane")}})
if (g, c) == ("agent", "read"):
    a = ags.get(args[2]) or error("agent_not_found")
    pantallas = a.get("pantallas") or [""]
    print(pantallas[0])
    if len(pantallas) > 1 and "--source" in args and args[args.index("--source") + 1] == "visible":
        a["pantallas"] = pantallas[1:]
        guardar()
    sys.exit(0)
if (g, c) == ("agent", "start"):
    nombre = args[2]
    ags[nombre] = {"status": estado.get("arranque_status", "idle"), "pane": args[args.index("--pane") + 1],
                   "kind": args[args.index("--kind") + 1], "pantallas": estado.get("arranque_pantallas", ["listo"])}
    guardar()
    if estado.get("arranque_error"):
        error(estado["arranque_error"])
    ok({"agent": {"name": nombre}})
if (g, c) in (("agent", "send-keys"), ("agent", "prompt"), ("agent", "focus")):
    if args[2] not in ags:
        error("agent_not_found")
    ok({"type": "ok"})
if (g, c) == ("worktree", "create"):
    ok({"root_pane": {"pane_id": "w2:p1"}, "workspace": {"workspace_id": "w2"}})
if (g, c) == ("workspace", "create"):
    ok({"root_pane": {"pane_id": "w3:p1"}, "workspace": {"workspace_id": "w3"}})
if (g, c) in (("workspace", "list"), ("workspace", "close")):
    ok({"workspaces": []})
error("no_soportado", " ".join(args))
"""

CMUX_FALSO = r"""#!/bin/sh
printf '%s\n' "$*" >> "$FALSO_CMUX"
"""


def preparar_falsos(tmp: Path, estado: dict | None = None) -> dict:
    """Crea los binarios falsos y devuelve el entorno para correr los scripts con ellos."""
    bin_dir = tmp / "bin"
    bin_dir.mkdir(exist_ok=True)
    for nombre, texto in (("herdr", HERDR_FALSO), ("cmux", CMUX_FALSO)):
        ruta = bin_dir / nombre
        ruta.write_text(texto)
        ruta.chmod(0o755)
    (tmp / "estado.json").write_text(json.dumps(estado or {"agentes": {}}))
    env = dict(os.environ)
    env.update(
        PATH=f"{bin_dir}:{env['PATH']}",
        FALSO_ESTADO=str(tmp / "estado.json"),
        FALSO_LLAMADAS=str(tmp / "llamadas.jsonl"),
        FALSO_CMUX=str(tmp / "cmux.log"),
        FLOTA_EVENTOS_DIR=str(tmp / "eventos"),
        FLOTA_HERDR=str(bin_dir / "herdr"),
    )
    return env


def llamadas(tmp: Path) -> list[list[str]]:
    ruta = tmp / "llamadas.jsonl"
    if not ruta.exists():
        return []
    return [json.loads(linea) for linea in ruta.read_text().splitlines()]


def correr(script: Path, *args: str, env: dict, timeout: float = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-I", str(script), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
        check=False,
    )


def git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return r.stdout.strip()


def crear_repo(ruta: Path) -> Path:
    ruta.mkdir(parents=True)
    git(ruta, "init", "-q", "-b", "main")
    git(ruta, "config", "user.email", "prueba@example.com")
    git(ruta, "config", "user.name", "Prueba")
    (ruta / "a.txt").write_text("a\n")
    git(ruta, "add", "a.txt")
    git(ruta, "commit", "-q", "-m", "base")
    return ruta
