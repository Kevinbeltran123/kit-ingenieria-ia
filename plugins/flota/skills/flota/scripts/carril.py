"""Carriles de la flota sobre herdr: preparar la corrida, iniciar un trabajador, hablarle, entregar y cerrar.

Uso (todas las rutas absolutas o relativas al directorio actual):
  carril.py preparar   --run DIR --repo REPO
  carril.py iniciar    --run DIR --sesion S --nombre N --tipo claude|codex --repo REPO [--modelo M] [--esfuerzo E]
                       [--permisos auto|abierto|preguntar] [--base REF] [--rama B] [--brief ARCHIVO] [--sin-worktree]
  carril.py enviar     --run DIR --sesion S --nombre N --texto "..."
  carril.py teclas     --sesion S --nombre N TECLA [TECLA ...]
  carril.py commit     --run DIR --nombre N -m "mensaje" [--incluir-nuevos]
  carril.py marcar     --run DIR --nombre N --estado activo|gate|enviado|cerrado
  carril.py cerrar     --run DIR --sesion S --nombre N
  carril.py lista      --run DIR --sesion S
  carril.py coordinador --run DIR --sesion S --repo REPO [--modelo M] [--permisos auto|preguntar]

Niveles de permisos (--permisos):
  auto       Claude en modo auto (un clasificador aprueba lo seguro); Codex con sandbox workspace-write y sin preguntas:
             escribe solo en su worktree y no puede hacer commit (.git queda de solo lectura), así que el commit lo hace
             el coordinador con `carril.py commit`. Es el valor por defecto.
  abierto    sin preguntas ni sandbox (bypassPermissions / danger-full-access). Solo en máquinas y repos donde aceptes
             que el trabajador haga cualquier cosa que tu usuario puede hacer. Exige FLOTA_PERMITIR_ABIERTO=1, que
             exporta la persona; la confirmación de Claude para ese modo la responde ella en herdr.
  preguntar  cada acción sensible se detiene en un diálogo; el coordinador o tú la responden.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import (
    TECLAS,
    HerdrError,
    agentes,
    anotar,
    cargar_carriles,
    guardar_carriles,
    herdr,
    lineas_listo,
    pantalla,
)

NOMBRE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
PLUGIN = Path(__file__).resolve().parents[3]  # plugins/flota

# Diálogos de arranque que el script responde solo, y el que nunca responde.
CONFIANZA_CLAUDE = "trust this folder"  # "Yes, I trust this folder" es la segunda opción: abajo + Enter
CONFIANZA_CODEX = "Trust this folder?"  # "1. Trust and continue" ya está marcada: Enter
BYPASS_CLAUDE = "Bypass Permissions mode"  # confirmación de bypassPermissions: siempre la responde la persona
HOOKS_CODEX = "need review"  # hooks de Codex sin confianza: lo decide la persona, no el script

ESTADO_INICIAL = """# Corrida de la flota

Repo: {repo}
Directorio de la corrida: {run}

## Meta
<qué significa terminar y la comprobación que lo demuestra>

## Permisos de esta corrida
<lo que la persona autorizó, con sus palabras y la fecha; lo demás se pregunta>

## Carriles
Los lleva carriles.json (lo escribe carril.py); aquí solo decisiones.

## Bitácora
"""

COMUN_INICIAL = """# Reglas comunes de los carriles

- Trabaja solo en tu worktree (el directorio donde arrancaste). No toques el checkout principal: {repo}
- Instala dependencias dentro del worktree con el gestor del proyecto (uv sync, npm ci...).
- Pruebas pesadas (build completo, suite larga): `python3 -I {scripts}/pesado.py <comando>` para turnarse con los
  demás carriles.
- Git: una rama por carril, nada de push ni de force; no borres archivos fuera de tu tarea.
- Al terminar, escribe tu entrega en {run}/handover-<tu-nombre>.md: qué hiciste, cómo lo verificaste (comandos y
  resultado) y lo que quedó pendiente. La última línea, sola: `<TU-NOMBRE>-READY <rama o PR> <head>`.
- Si necesitas una decisión, escribe la pregunta en tu handover con la línea `<TU-NOMBRE>-PREGUNTA` y espera.
"""

PUERTA_INICIAL = """# Puerta (gate)

## En cola

## Probando

## Done
"""


def git(repo: str, *args: str, timeout: float = 60) -> str:
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, timeout=timeout, check=False)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout.strip()


def argumentos_agente(
    tipo: str, modelo: str | None, esfuerzo: str | None, permisos: str, sesion_id: str | None
) -> list[str]:
    """Argumentos nativos del agente según tipo y nivel de permisos (van después de `--` en `herdr agent start`)."""
    if tipo == "claude":
        args = []
        if sesion_id:
            args += ["--session-id", sesion_id]
        if modelo:
            args += ["--model", modelo]
        if esfuerzo:
            args += ["--effort", esfuerzo]
        if permisos == "auto":
            args += ["--permission-mode", "auto"]
        elif permisos == "abierto":
            args += ["--permission-mode", "bypassPermissions"]
        return args
    if tipo == "codex":
        args = []
        if modelo:
            args += ["-m", modelo]
        if esfuerzo:
            args += ["-c", f"model_reasoning_effort={esfuerzo}"]
        if permisos == "auto":
            args += ["-s", "workspace-write", "-a", "never"]
        elif permisos == "abierto":
            args += ["-s", "danger-full-access", "-a", "never"]
        else:
            args += ["-s", "workspace-write", "-a", "on-request"]
        return args
    raise ValueError(f"tipo de agente no soportado: {tipo}")


def modelo_por_defecto(tipo: str) -> str | None:
    if tipo == "claude":
        return os.environ.get("FLOTA_MODELO_CLAUDE", "claude-opus-5-5")
    return os.environ.get("FLOTA_MODELO_CODEX") or None


def aceptar_dialogos(sesion: str, nombre: str, espera: float = 45) -> str:
    """Responde los diálogos de arranque conocidos y espera a que el agente quede listo.

    Devuelve "listo" o un texto que explica por qué no (diálogo que decide la persona, tiempo agotado).
    No se fía solo del estado de herdr: Codex en su diálogo de confianza aparece como idle.
    """
    fin = time.time() + espera
    while time.time() < fin:
        try:
            texto = pantalla(sesion, nombre)
        except HerdrError as e:
            return f"no se pudo leer la pantalla: {e}"
        if HOOKS_CODEX in texto and "hook" in texto.lower():
            return "Codex pide revisar hooks nuevos: que la persona los revise y confíe en ellos en una sesión de Codex"
        if CONFIANZA_CLAUDE in texto and "Yes, I trust" in texto:
            herdr(sesion, "agent", "send-keys", nombre, "down")
            herdr(sesion, "agent", "send-keys", nombre, "enter")
        elif CONFIANZA_CODEX in texto:
            herdr(sesion, "agent", "send-keys", nombre, "enter")
        elif BYPASS_CLAUDE in texto:
            return "Claude pide confirmar el modo sin permisos: eso lo confirma la persona en herdr, no el script"
        else:
            estado = herdr(sesion, "agent", "get", nombre).get("result", {}).get("agent", {}).get("agent_status")
            if estado in ("idle", "done"):
                return "listo"
        time.sleep(1.5)
    return f"el agente no quedó listo en {espera:.0f} s: léelo con `herdr --session {sesion} agent read {nombre}`"


def resolver_base(repo: str, base: str | None) -> tuple[str, str]:
    """SHA de la base y una nota de frescura. Sin --base: origin/HEAD tras un fetch; si falla, HEAD local."""
    if base:
        return git(repo, "rev-parse", "--verify", f"{base}^{{commit}}"), f"base pedida {base}"
    try:
        git(repo, "fetch", "--quiet", "origin", timeout=45)
        ref = git(repo, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
        return git(repo, "rev-parse", ref), f"{ref} recién traída"
    except (RuntimeError, subprocess.TimeoutExpired):
        return git(repo, "rev-parse", "HEAD"), "HEAD local (frescura sin verificar: el fetch falló)"


def mensaje_inicio(run: Path, nombre: str, tipo: str, permisos: str, brief: str) -> str:
    entrega = run / f"handover-{nombre}.md"
    partes = [
        f"Coordinador: eres el carril {nombre}. Tu tarea está en {brief}; las reglas comunes en {run / 'common.md'}.",
        f"Al terminar escribe la entrega en {entrega} y como última línea, sola: {nombre.upper()}-READY <rama> <head>.",
    ]
    if tipo == "codex" and permisos == "auto":
        partes.append(
            "Tu sandbox no deja escribir en .git: no hagas commit; deja los cambios en el worktree y pon 'sin commit' "
            "en lugar del head. El coordinador hace el commit."
        )
    return " ".join(partes)


def cmd_preparar(a: argparse.Namespace) -> int:
    run = Path(a.run).expanduser().resolve()
    repo = str(Path(a.repo).expanduser().resolve())
    scripts = Path(__file__).resolve().parent
    (run / "gate").mkdir(parents=True, exist_ok=True)
    (run / "briefs").mkdir(exist_ok=True)
    (run / "wt").mkdir(exist_ok=True)
    plantillas = {
        run / "STATE.md": ESTADO_INICIAL.format(repo=repo, run=run),
        run / "common.md": COMUN_INICIAL.format(repo=repo, run=run, scripts=scripts),
        run / "gate" / "queue.md": PUERTA_INICIAL,
    }
    for ruta, texto in plantillas.items():
        if not ruta.exists():
            ruta.write_text(texto, encoding="utf-8")
    if not (run / "carriles.json").exists():
        guardar_carriles(run, {})
    print(f"corrida lista en {run}")
    return 0


def cmd_iniciar(a: argparse.Namespace) -> int:
    run = Path(a.run).expanduser().resolve()
    repo = str(Path(a.repo).expanduser().resolve())
    if not NOMBRE.match(a.nombre):
        print(
            f"nombre inválido: {a.nombre!r} (minúsculas, dígitos, - o _, hasta 32, empieza con letra)", file=sys.stderr
        )
        return 2
    if a.permisos == "abierto" and os.environ.get("FLOTA_PERMITIR_ABIERTO") != "1":
        print(
            "--permisos abierto quita sandbox y preguntas: lo decide la persona exportando FLOTA_PERMITIR_ABIERTO=1 en "
            "la terminal donde corre el coordinador (y confirmando el diálogo de Claude en herdr)",
            file=sys.stderr,
        )
        return 2
    if not (run / "STATE.md").exists():
        print(f"{run} no está preparada: corre primero `carril.py preparar --run {run} --repo {repo}`", file=sys.stderr)
        return 2
    vivos = {ag.get("name") for ag in agentes(a.sesion)}
    if a.nombre in vivos:
        print(
            f"ya hay un agente vivo llamado {a.nombre}: reúsalo (carril.py enviar) o usa otro nombre", file=sys.stderr
        )
        return 1
    carriles = cargar_carriles(run)
    modelo = a.modelo or modelo_por_defecto(a.tipo)
    registro = {
        "nombre": a.nombre,
        "tipo": a.tipo,
        "modelo": modelo,
        "esfuerzo": a.esfuerzo,
        "permisos": a.permisos,
        "sesion": a.sesion,
        "iniciado": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "estado": "activo",
        "brief": str(Path(a.brief).expanduser().resolve()) if a.brief else None,
    }
    try:
        if a.sin_worktree:
            r = herdr(a.sesion, "workspace", "create", "--cwd", repo, "--label", a.nombre, "--no-focus")
            registro.update(
                worktree=repo, rama=git(repo, "branch", "--show-current"), base=git(repo, "rev-parse", "HEAD")
            )
            registro["nota_base"] = "sin worktree: trabaja en el checkout del repo"
        else:
            base, nota = resolver_base(repo, a.base)
            rama = a.rama or f"flota/{a.nombre}"
            ruta = run / "wt" / a.nombre
            r = herdr(
                a.sesion,
                "worktree",
                "create",
                "--cwd",
                repo,
                "--base",
                base,
                "--branch",
                rama,
                "--path",
                str(ruta),
                "--label",
                a.nombre,
            )
            registro.update(worktree=str(ruta), rama=rama, base=base, nota_base=nota)
        res = r.get("result", {})
        registro["pane"] = res.get("root_pane", {}).get("pane_id")
        registro["workspace"] = res.get("workspace", {}).get("workspace_id")
        sesion_id = str(uuid.uuid4()) if a.tipo == "claude" else None
        registro["sesion_agente"] = sesion_id
        nativos = argumentos_agente(a.tipo, modelo, a.esfuerzo, a.permisos, sesion_id)
        try:
            herdr(
                a.sesion,
                "agent",
                "start",
                a.nombre,
                "--kind",
                a.tipo,
                "--pane",
                registro["pane"],
                "--timeout",
                "60000",
                "--",
                *nativos,
                timeout=90,
            )
        except HerdrError as e:
            if e.codigo != "agent_not_ready":  # bloqueado al arrancar: casi siempre el diálogo de confianza
                raise
        estado = aceptar_dialogos(a.sesion, a.nombre)
    except (HerdrError, RuntimeError) as e:
        print(f"no se pudo iniciar {a.nombre}: {e}", file=sys.stderr)
        return 1
    carriles[a.nombre] = registro
    guardar_carriles(run, carriles)
    anotar(
        run,
        f"carril {a.nombre} iniciado: {a.tipo} {modelo or '(modelo de su config)'} {a.esfuerzo or ''} "
        f"permisos={a.permisos} rama={registro.get('rama')} base={str(registro.get('base'))[:9]}",
    )
    if estado != "listo":
        print(f"{a.nombre}: arrancó pero {estado}", file=sys.stderr)
        return 3
    if a.brief:
        texto = mensaje_inicio(run, a.nombre, a.tipo, a.permisos, registro["brief"])
        herdr(
            a.sesion,
            "agent",
            "prompt",
            a.nombre,
            texto,
            "--wait",
            "--until",
            "working",
            "--timeout",
            "30000",
            timeout=45,
        )
    print(f"{a.nombre} listo en {registro['worktree']} (pane {registro['pane']}, rama {registro.get('rama')})")
    return 0


def cmd_enviar(a: argparse.Namespace) -> int:
    texto = a.texto if a.texto.startswith("Coordinador:") else f"Coordinador: {a.texto}"
    try:
        herdr(
            a.sesion,
            "agent",
            "prompt",
            a.nombre,
            texto,
            "--wait",
            "--until",
            "working",
            "--timeout",
            "30000",
            timeout=45,
        )
    except HerdrError as e:
        print(f"{a.nombre}: {e} (lee su pantalla antes de reenviar: el texto pudo haber llegado)", file=sys.stderr)
        return 1
    if a.run:
        anotar(Path(a.run).expanduser().resolve(), f"a {a.nombre}: {texto[:140]}")
    return 0


def cmd_teclas(a: argparse.Namespace) -> int:
    malas = [t for t in a.teclas if t not in TECLAS]
    if malas:
        print(f"teclas no permitidas: {malas}; válidas: {', '.join(TECLAS)}", file=sys.stderr)
        return 2
    for tecla in a.teclas:
        herdr(a.sesion, "agent", "send-keys", a.nombre, tecla)
    return 0


def cmd_commit(a: argparse.Namespace) -> int:
    run = Path(a.run).expanduser().resolve()
    carriles = cargar_carriles(run)
    c = carriles.get(a.nombre)
    if not c:
        print(f"no hay carril {a.nombre} en {run}", file=sys.stderr)
        return 1
    wt = c["worktree"]
    estado = git(wt, "status", "--porcelain", "--untracked-files=all")
    if not estado:
        print(f"{a.nombre}: no hay cambios que commitear en {wt}")
        return 0
    nuevos = [linea[3:] for linea in estado.splitlines() if linea.startswith("??")]
    if nuevos and not a.incluir_nuevos:
        print(
            f"{a.nombre}: hay archivos nuevos sin seguimiento; revísalos y vuelve con --incluir-nuevos, o agrégalos a "
            ".gitignore:\n  " + "\n  ".join(nuevos),
            file=sys.stderr,
        )
        return 1
    git(wt, "add", "-A" if a.incluir_nuevos else "-u")
    git(wt, "commit", "-q", "-m", a.mensaje)
    print(git(wt, "show", "--stat", "--format=", "HEAD"))
    head = git(wt, "rev-parse", "--short", "HEAD")
    c["head"] = head
    guardar_carriles(run, carriles)
    anotar(run, f"commit del coordinador en {a.nombre}: {head} {a.mensaje[:80]}")
    print(head)
    return 0


def cmd_marcar(a: argparse.Namespace) -> int:
    run = Path(a.run).expanduser().resolve()
    carriles = cargar_carriles(run)
    if a.nombre not in carriles:
        print(f"no hay carril {a.nombre} en {run}", file=sys.stderr)
        return 1
    carriles[a.nombre]["estado"] = a.estado
    guardar_carriles(run, carriles)
    anotar(run, f"{a.nombre} → {a.estado}")
    return 0


def cmd_cerrar(a: argparse.Namespace) -> int:
    run = Path(a.run).expanduser().resolve()
    carriles = cargar_carriles(run)
    c = carriles.get(a.nombre)
    if not c:
        print(f"no hay carril {a.nombre} en {run}", file=sys.stderr)
        return 1
    if c.get("workspace"):
        try:
            herdr(a.sesion, "workspace", "close", c["workspace"])
        except HerdrError as e:
            print(f"aviso: {e}", file=sys.stderr)
    c["estado"] = "cerrado"
    guardar_carriles(run, carriles)
    anotar(run, f"{a.nombre} cerrado (el worktree queda en {c.get('worktree')})")
    return 0


def cmd_lista(a: argparse.Namespace) -> int:
    run = Path(a.run).expanduser().resolve()
    estados = {ag.get("name"): ag.get("agent_status") for ag in agentes(a.sesion)}
    listos = {x["carril"]: x["resto"] for x in lineas_listo(run) if x["tipo"] == "listo"}
    for nombre, c in cargar_carriles(run).items():
        vivo = estados.get(nombre, "—")
        print(
            f"{nombre:<16} {c['tipo']:<6} {c.get('modelo') or '-'!s:<18} {c.get('estado', ''):<8} {vivo:<8} "
            f"{c.get('rama') or '':<22} {listos.get(nombre, '')}"
        )
    return 0


def cmd_coordinador(a: argparse.Namespace) -> int:
    """Deja un agente `coordinador` (Claude con la skill flota cargada) en su propio espacio de la sesión."""
    repo = str(Path(a.repo).expanduser().resolve())
    fin = time.time() + a.espera
    while True:
        try:
            herdr(a.sesion, "workspace", "list", timeout=5)
            break
        except HerdrError:
            if time.time() > fin:
                print(f"el servidor de herdr de la sesión {a.sesion} no respondió en {a.espera:.0f} s", file=sys.stderr)
                return 1
            time.sleep(1)
    if any(ag.get("name") == "coordinador" for ag in agentes(a.sesion)):
        print("coordinador ya está corriendo")
        return 0
    r = herdr(a.sesion, "workspace", "create", "--cwd", repo, "--label", "coordinador", "--focus")
    pane = r.get("result", {}).get("root_pane", {}).get("pane_id")
    nativos = ["--model", a.modelo, "--plugin-dir", str(PLUGIN)]
    if a.permisos == "auto":
        nativos += ["--permission-mode", "auto"]
    try:
        herdr(
            a.sesion,
            "agent",
            "start",
            "coordinador",
            "--kind",
            "claude",
            "--pane",
            pane,
            "--timeout",
            "60000",
            "--",
            *nativos,
            timeout=90,
        )
    except HerdrError as e:
        if e.codigo != "agent_not_ready":
            print(f"no se pudo iniciar el coordinador: {e}", file=sys.stderr)
            return 1
    print(f"coordinador: {aceptar_dialogos(a.sesion, 'coordinador')} (pane {pane})")
    if a.run:
        anotar(Path(a.run).expanduser().resolve(), f"coordinador iniciado en la sesión {a.sesion}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("preparar")
    s.add_argument("--run", required=True)
    s.add_argument("--repo", required=True)

    s = sub.add_parser("iniciar")
    s.add_argument("--run", required=True)
    s.add_argument("--sesion", required=True)
    s.add_argument("--nombre", required=True)
    s.add_argument("--tipo", required=True, choices=("claude", "codex"))
    s.add_argument("--repo", required=True)
    s.add_argument("--modelo")
    s.add_argument("--esfuerzo", choices=("low", "medium", "high", "xhigh", "max"))
    s.add_argument("--permisos", default="auto", choices=("auto", "abierto", "preguntar"))
    s.add_argument("--base")
    s.add_argument("--rama")
    s.add_argument("--brief")
    s.add_argument("--sin-worktree", action="store_true")

    s = sub.add_parser("enviar")
    s.add_argument("--run")
    s.add_argument("--sesion", required=True)
    s.add_argument("--nombre", required=True)
    s.add_argument("--texto", required=True)

    s = sub.add_parser("teclas")
    s.add_argument("--sesion", required=True)
    s.add_argument("--nombre", required=True)
    s.add_argument("teclas", nargs="+")

    s = sub.add_parser("commit")
    s.add_argument("--run", required=True)
    s.add_argument("--nombre", required=True)
    s.add_argument("-m", "--mensaje", required=True)
    s.add_argument("--incluir-nuevos", action="store_true", help="incluir archivos sin seguimiento (revisados)")

    s = sub.add_parser("marcar")
    s.add_argument("--run", required=True)
    s.add_argument("--nombre", required=True)
    s.add_argument("--estado", required=True, choices=("activo", "gate", "enviado", "cerrado"))

    s = sub.add_parser("cerrar")
    s.add_argument("--run", required=True)
    s.add_argument("--sesion", required=True)
    s.add_argument("--nombre", required=True)

    s = sub.add_parser("lista")
    s.add_argument("--run", required=True)
    s.add_argument("--sesion", required=True)

    s = sub.add_parser("coordinador")
    s.add_argument("--run")
    s.add_argument("--sesion", required=True)
    s.add_argument("--repo", required=True)
    s.add_argument("--modelo", default="claude-opus-5-5")
    s.add_argument("--permisos", default="auto", choices=("auto", "preguntar"))
    s.add_argument("--espera", type=float, default=20)

    a = p.parse_args(argv)
    return {
        "preparar": cmd_preparar,
        "iniciar": cmd_iniciar,
        "enviar": cmd_enviar,
        "teclas": cmd_teclas,
        "commit": cmd_commit,
        "marcar": cmd_marcar,
        "cerrar": cmd_cerrar,
        "lista": cmd_lista,
        "coordinador": cmd_coordinador,
    }[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
