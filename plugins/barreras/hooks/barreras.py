"""PreToolUse: barreras contra acciones peligrosas del agente.

Reglas (se pueden desactivar por repo, salvo la autoprotección: ni .claude/barreras.json ni los
settings de Claude Code del repo, donde viven los plugins y las reglas deny, los edita el agente):
  infra     apply/deploy/destroy de Terraform, CDK, SAM, Pulumi, Serverless y AWS CLI destructivo
  sql       SQL destructivo con un cliente de base de datos (bloquea en producción, pregunta fuera)
  archivos  editar .env, lockfiles, migraciones existentes o .git/
  secretos  leer credenciales de AWS, llaves SSH, .env, .envrc o volcar variables de entorno
  local     borrar trabajo: rm -rf fuera de /tmp y cachés, find -delete, git reset --hard,
            push --force, clean -f, checkout/restore de todo, stash drop/clear, branch -D,
            worktree remove --force, commit --no-verify y borrar archivos de base de datos

Falla cerrado: ante un error interno bloquea (exit 2).
No es una barrera completa: la seguridad real son reglas deny, sandbox y permisos de solo lectura.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

REGLAS = {"infra", "sql", "archivos", "secretos", "local"}

OPERADORES = {";", "&&", "||", "|", "&", "(", ")", "|&", ";;"}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "fish"}
PREFIJOS_SIMPLES = {"sudo", "time", "nohup", "exec", "command", "nice", "env", "builtin", "npx", "bunx", "doas"}
EJECUTORES = {"uv": "run", "poetry": "run", "pipenv": "run", "pnpm": "exec", "pdm": "run", "hatch": "run"}
FLAGS_CON_VALOR = {"--with", "--python", "-p", "--from", "--project", "--directory", "-u", "--user", "-g"}
TIMEOUT_CON_VALOR = {"-s", "--signal", "-k", "--kill-after"}  # aparte: en sudo, -s y -k no llevan valor

PROD = re.compile(r"(?i)(?<![a-z])(prod|production|prd)(?![a-z])")
VARIABLES_ENTORNO_DB = ("DATABASE_URL", "PGHOST", "PGDATABASE", "ENV", "APP_ENV", "ENVIRONMENT", "STAGE")


# ---------- utilidades ----------


def tokens_de(cmd: str) -> list[str]:
    texto = cmd.replace("`", " ; ").replace("\n", " ; ")
    try:
        lex = shlex.shlex(texto, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        return list(lex)
    except ValueError:  # comillas sin cerrar: separación cruda
        return re.findall(r"&&|\|\||[;|&()]|[^\s;|&()\"']+", texto)


def segmentos(cmd: str, profundidad: int = 0) -> list[list[str]]:
    """Divide un comando en subcomandos y desenvuelve bash -c / eval."""
    resultado, actual = [], []
    for tok in tokens_de(cmd) + [";"]:
        if tok in OPERADORES or set(tok) <= set(";&|()<>"):
            if actual:
                resultado.append(actual)
            actual = []
        elif tok != "$":
            actual.append(tok.lstrip("$") if tok.startswith("$(") else tok)
    final = []
    for seg in resultado:
        seg = quitar_prefijos(seg)
        if not seg:
            continue
        nombre = Path(seg[0]).name
        if profundidad < 3 and nombre in SHELLS and "-c" in seg:
            i = seg.index("-c")
            final += segmentos(" ".join(seg[i + 1 :]), profundidad + 1)
        elif profundidad < 3 and nombre == "eval":
            final += segmentos(" ".join(seg[1:]), profundidad + 1)
        else:
            final.append(seg)
    return final


def quitar_prefijos(seg: list[str]) -> list[str]:
    seg = list(seg)
    for _ in range(10):
        if not seg:
            break
        primero = Path(seg[0]).name
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", seg[0]):
            seg = seg[1:]
        elif primero in PREFIJOS_SIMPLES and len(seg) > 1:
            seg = saltar_flags(seg[1:])
        elif primero == "timeout":
            seg = saltar_flags(seg[1:], TIMEOUT_CON_VALOR)[1:]  # [1:] quita la duración
        elif primero in EJECUTORES and len(seg) > 1 and seg[1] in (EJECUTORES[primero], "dlx"):
            seg = saltar_flags(seg[2:])
        elif primero == "aws-vault" and "--" in seg:
            seg = seg[seg.index("--") + 1 :]
        else:
            break
    return seg


def saltar_flags(seg: list[str], con_valor: set[str] = FLAGS_CON_VALOR) -> list[str]:
    i = 0
    while i < len(seg) and seg[i].startswith("-"):
        i += 2 if seg[i] in con_valor else 1
    return seg[i:]


def argumentos(seg: list[str]) -> list[str]:
    """Argumentos que no son flags (aprox.; salta el valor de --opcion valor de AWS)."""
    salida, saltar = [], False
    for tok in seg[1:]:
        if saltar:
            saltar = False
            continue
        if tok.startswith("-"):
            saltar = tok.startswith("--") and "=" not in tok and tok in AWS_FLAGS_CON_VALOR
            continue
        salida.append(tok)
    return salida


AWS_FLAGS_CON_VALOR = {
    "--profile",
    "--region",
    "--output",
    "--endpoint-url",
    "--query",
    "--color",
    "--cli-read-timeout",
    "--cli-connect-timeout",
    "--ca-bundle",
}


# ---------- reglas de Bash ----------


def regla_infra(seg: list[str]) -> str | None:
    nombre, args = Path(seg[0]).name, argumentos(seg)
    primero = args[0] if args else ""
    if nombre in ("terraform", "tofu", "terragrunt"):
        if primero in ("run-all", "run") and len(args) > 1:
            primero = args[1]
        if primero in ("apply", "destroy", "import") or args[:2] in (["state", "rm"], ["state", "push"]):
            return f"{nombre} {primero}"
    if nombre in ("cdk", "aws-cdk") and primero in ("deploy", "destroy"):
        return f"cdk {primero}"
    if nombre == "sam" and primero in ("deploy", "delete", "sync"):
        return f"sam {primero}"
    if nombre == "pulumi" and primero in ("up", "update", "destroy"):
        return f"pulumi {primero}"
    if nombre in ("serverless", "sls") and primero in ("deploy", "remove"):
        return f"{nombre} {primero}"
    if nombre == "aws" and len(args) >= 2:
        servicio, op = args[0], args[1]
        if servicio == "cloudformation" and op in (
            "deploy",
            "create-stack",
            "update-stack",
            "delete-stack",
            "execute-change-set",
        ):
            return f"aws cloudformation {op}"
        if servicio == "s3" and (op in ("rm", "rb", "mv") or (op == "sync" and "--delete" in seg)):
            return f"aws s3 {op}"
        if re.match(r"^(delete|terminate|remove|deregister|revoke|detach|disable)-", op):
            return f"aws {servicio} {op}"
        if re.match(
            r"^(put-bucket-(policy|acl)|put-.*-policy|attach-.*-policy|create-access-key|"
            r"update-assume-role-policy|update-function-code|stop-instances)$",
            op,
        ):
            return f"aws {servicio} {op}"
    return None


CLIENTES_DB = {"psql", "mysql", "mariadb", "sqlite3", "sqlcmd", "clickhouse-client", "duckdb", "pgcli", "mycli"}

DESTRUCTIVO_SIEMPRE = re.compile(
    r"\b(DROP\s+(TABLE|DATABASE|SCHEMA|VIEW|INDEX|COLUMN|USER|ROLE|FUNCTION|TYPE|EXTENSION|MATERIALIZED|SEQUENCE|TRIGGER)"
    r"|TRUNCATE)\b"
)
DESTRUCTIVO_PROD = re.compile(r"\b(ALTER\s+(TABLE|DATABASE|SCHEMA|ROLE|USER)|GRANT|REVOKE)\b")


def sentencias_sin_where(sql: str) -> bool:
    for sentencia in sql.split(";"):
        if re.search(r"\bDELETE\s+FROM\b", sentencia) and not re.search(r"\bWHERE\b", sentencia):
            return True
        if re.search(r"\bUPDATE\s+\S+\s+SET\b", sentencia) and not re.search(r"\bWHERE\b", sentencia):
            return True
    return False


def senal_de_produccion(cmd: str) -> bool:
    if PROD.search(cmd):
        return True
    return any(PROD.search(os.environ.get(v, "")) for v in VARIABLES_ENTORNO_DB)


def regla_sql(cmd: str, segs: list[list[str]]) -> tuple[str, str] | None:
    """Devuelve (decisión, motivo) con decisión 'bloquear' o 'preguntar'."""
    usa_cliente = any(Path(t).name in CLIENTES_DB for seg in segs for t in seg)
    usa_alembic = [seg for seg in segs if Path(seg[0]).name == "alembic"]
    prod = senal_de_produccion(cmd)

    for seg in usa_alembic:
        accion = next((a for a in seg[1:] if a in ("upgrade", "downgrade", "stamp")), None)
        if prod and accion:
            return "bloquear", f"alembic {accion} contra producción"
    if not usa_cliente:
        return None

    sql = cmd.upper()
    siempre = DESTRUCTIVO_SIEMPRE.search(sql)
    sin_where = sentencias_sin_where(sql)
    en_prod = DESTRUCTIVO_PROD.search(sql)
    if prod and (siempre or sin_where or en_prod):
        motivo = siempre.group(0) if siempre else (en_prod.group(0) if en_prod else "DELETE/UPDATE sin WHERE")
        return "bloquear", f"{motivo} contra producción"
    if siempre:
        return "preguntar", siempre.group(0)
    if sin_where:
        return "preguntar", "DELETE/UPDATE sin WHERE"
    return None


LECTORES = {
    "cat",
    "less",
    "more",
    "head",
    "tail",
    "bat",
    "strings",
    "xxd",
    "od",
    "base64",
    "cp",
    "mv",
    "grep",
    "rg",
    "awk",
    "sed",
    "nl",
    "tac",
    "curl",
    "nc",
    "openssl",
    "vim",
    "nano",
}
CREDENCIALES = re.compile(r"\.aws/(credentials|sso/cache)|\.ssh/id_[^/\s]*(?<!\.pub)$|\.config/gcloud/.*credentials")
VAR_SECRETA = re.compile(r"\$\{?[A-Z0-9_]*(SECRET|TOKEN|PASSWORD|PASSWD|API_KEY|ACCESS_KEY|PRIVATE_KEY)[A-Z0-9_]*")
ENV_REAL = re.compile(r"(^|/)\.env(rc)?(\.[\w.-]+)?$")  # .envrc es el de direnv
ENV_EJEMPLO = re.compile(r"\.env(rc)?\.(example|sample|template|dist)$")


def regla_secretos(seg: list[str]) -> str | None:
    nombre = Path(seg[0]).name
    args = seg[1:]
    if nombre == "printenv" and (not argumentos(seg) or any(VAR_SECRETA.search("$" + a) for a in argumentos(seg))):
        return "printenv"
    if nombre == "env" and not args:
        return "env"
    if nombre in ("export", "declare", "typeset") and args in (["-p"], ["-x"], []):
        return f"{nombre} {' '.join(args)}".strip()
    if nombre in ("echo", "printf") and any(VAR_SECRETA.search(a) for a in args):
        return "imprimir una variable secreta"
    for i, tok in enumerate(args):
        if CREDENCIALES.search(tok):
            if nombre in ("ssh", "scp", "sftp", "rsync", "git") and i > 0 and args[i - 1] == "-i":
                continue
            if nombre in ("ssh-add", "ssh-keygen", "chmod", "ls", "test", "stat"):
                continue
            return f"acceso a credenciales ({tok})"
        if nombre in LECTORES and ENV_REAL.search(tok) and not ENV_EJEMPLO.search(tok):
            return f"leer {tok}"
    return None


RM_SEGURO = ("/tmp/", "/private/tmp/", "/private/var/folders/")
RM_PARTES_SEGURAS = ("__pycache__", "node_modules/.cache", ".pytest_cache", ".ruff_cache", ".mypy_cache")
# Se regeneran con un comando (uv sync, uv build, pytest --cov, tox): borrarlas no pierde trabajo.
RM_REGENERABLES = {".venv", "dist", "build", "htmlcov", ".tox", ".nox", ".coverage"}
ARCHIVO_DB = re.compile(r"\.(sqlite3?|db)$")


def rm_seguro(objetivo: str) -> bool:
    nombre = Path(objetivo).name
    return (
        os.path.expanduser(objetivo).startswith(RM_SEGURO)
        or any(p in objetivo for p in RM_PARTES_SEGURAS)
        or nombre in RM_REGENERABLES
        or nombre.endswith(".egg-info")
    )


def banderas_cortas(args: list[str]) -> str:
    return "".join(a[1:] for a in args if a.startswith("-") and not a.startswith("--"))


def regla_local(seg: list[str]) -> str | None:
    """Comandos que borran trabajo que puede no estar en git (reglas del hook global de Kevin)."""
    nombre, args = Path(seg[0]).name, seg[1:]
    if nombre in ("rm", "unlink"):
        objetivos = [a for a in args if not a.startswith("-")]
        if any(ARCHIVO_DB.search(o) for o in objetivos):
            return "borrar un archivo de base de datos"
        banderas = banderas_cortas(args)
        recursivo = "r" in banderas or "R" in banderas or "--recursive" in args
        forzado = "f" in banderas or "--force" in args
        if nombre == "rm" and recursivo and forzado:
            inseguros = [o for o in objetivos if not rm_seguro(o)]
            if inseguros or not objetivos:
                return f"rm -rf sobre {', '.join(inseguros) or 'nada explícito'}"
    elif nombre == "find":
        if "-delete" in args:
            return "find -delete"
        if any(a in ("-exec", "-execdir") and Path(b).name == "rm" for a, b in zip(args, args[1:])):
            return "find -exec rm"
    elif nombre == "git":
        return regla_git(args)
    return None


def regla_git(args: list[str]) -> str | None:
    i = 0
    while i < len(args) and args[i].startswith("-"):
        i += 2 if args[i] in ("-C", "-c") else 1
    if i >= len(args):
        return None
    sub, resto = args[i], args[i + 1 :]
    banderas = banderas_cortas(resto)
    if sub == "push" and ("--force" in resto or "f" in banderas or any(a.startswith("+") for a in resto)):
        return "git push --force"
    if sub == "reset" and "--hard" in resto:
        return "git reset --hard"
    if sub == "clean" and ("f" in banderas or "--force" in resto) and "n" not in banderas and "--dry-run" not in resto:
        return "git clean -f"
    if sub in ("checkout", "restore") and {".", ":/"} & set(resto) and "--staged" not in resto:
        return f"git {sub} de todo el árbol"
    if sub == "stash" and resto[:1] in (["drop"], ["clear"]):
        return f"git stash {resto[0]}"
    if sub == "commit" and ("--no-verify" in resto or "n" in banderas):
        return "git commit --no-verify"
    if sub == "branch" and ("-D" in resto or ("--delete" in resto and "--force" in resto)):
        return "git branch -D"
    if sub == "worktree" and resto[:1] == ["remove"] and ("--force" in resto or "-f" in resto):
        return "git worktree remove --force"
    return None


CONFIG_PROTEGIDA = {
    "barreras.json": "la configuración de barreras",
    "settings.json": "la configuración de Claude Code del repo (plugins, reglas deny, sandbox)",
    "settings.local.json": "la configuración local de Claude Code (plugins, reglas deny, sandbox)",
}
RUTA_SETTINGS = re.compile(r"(^|/)\.claude/settings(\.local)?\.json$")
SOLO_LEEN_CONFIG = {"cat", "less", "head", "tail", "jq", "grep", "diff", "wc", "stat", "ls", "test"}
GIT_ESCRIBE = {"rm", "mv", "checkout", "restore"}


def config_protegida(ruta: str) -> str | None:
    p = Path(ruta)
    return CONFIG_PROTEGIDA.get(p.name) if p.parent.name == ".claude" else None


def toca_config_protegida(segs: list[list[str]]) -> str | None:
    """Comando que puede modificar barreras.json o los settings de Claude Code; leerlos está permitido."""
    for seg in segs:
        tocadas = [t for t in seg if "barreras.json" in t or RUTA_SETTINGS.search(t)]
        if not tocadas:
            continue
        nombre = Path(seg[0]).name
        if nombre in SOLO_LEEN_CONFIG:
            continue
        if nombre == "git" and not any(a in GIT_ESCRIBE for a in seg[1:]):
            continue
        return CONFIG_PROTEGIDA.get(Path(tocadas[0]).name, "la configuración de barreras")
    return None


# ---------- regla de archivos ----------

LOCKFILES = {
    "uv.lock",
    "poetry.lock",
    "Pipfile.lock",
    "pdm.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lockb",
    "Cargo.lock",
}


def sin_commit(p: Path) -> bool:
    """True solo si git dice que el archivo no está rastreado (recién creado). Sin git, False: se protege."""
    try:
        r = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", p.name],
            cwd=p.parent,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 1  # 1 = git no lo conoce; 128 = no es un repo de git


def regla_archivos(ruta: str) -> str | None:
    p = Path(ruta)
    partes = p.parts
    if ".git" in partes[:-1] or p.name == ".git":
        return "los archivos internos de .git/ no se editan a mano"
    if p.name.startswith(".env") and not ENV_EJEMPLO.search(p.name):
        return f"{p.name} contiene secretos; edita .env.example y pide al usuario que actualice su .env"
    if p.name in LOCKFILES:
        return f"{p.name} se cambia con el gestor de paquetes (p. ej. `uv add`, `uv lock`), no a mano"
    alembic = any(
        partes[i] in ("migrations", "alembic") and partes[i + 1] == "versions" for i in range(len(partes) - 2)
    )
    django = p.parent.name == "migrations" and re.match(r"^\d{4}_.*\.py$", p.name)
    if (alembic or django) and p.exists() and not sin_commit(p):
        return (
            "esa migración ya está en git y puede estar aplicada; crea una nueva en lugar de editarla "
            "(una recién generada y sin commit sí se puede corregir)"
        )
    return None


# ---------- principal ----------


def reglas_desactivadas(raiz: Path) -> set[str]:
    desactivadas = {r.strip() for r in os.environ.get("BARRERAS_DESACTIVAR", "").split(",") if r.strip()}
    config = raiz / ".claude" / "barreras.json"
    if config.exists():
        try:
            desactivadas |= set(json.loads(config.read_text()).get("desactivar", []))
        except (ValueError, AttributeError, TypeError):
            pass  # config inválida: se aplican todas las reglas
    return desactivadas & REGLAS


def bloquear(regla: str, motivo: str, consejo: str) -> int:
    print(f"Bloqueado por barreras ({regla}): {motivo}.\n{consejo}", file=sys.stderr)
    return 2


def preguntar(motivo: str) -> int:
    salida = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": f"barreras (sql): {motivo}. Confirma solo si sabes a qué base de datos apunta.",
        }
    }
    print(json.dumps(salida))
    return 0


CONSEJO_INFRA = (
    "Los cambios de infraestructura van por PR y se aplican desde CI. Para revisar usa plan, diff, synth o validate."
)
CONSEJO_SQL = (
    "En producción solo se consulta con un rol de solo lectura; los cambios van como migración "
    "revisada en un PR. Explícale al usuario qué querías hacer."
)
CONSEJO_SECRETOS = 'No leas ni imprimas credenciales. Si necesitas saber si existe una variable, usa `test -n "$VAR"`.'
CONSEJO_LOCAL = (
    "Puede borrar trabajo que no está en git. Si de verdad hace falta, pídele a la persona que lo "
    "corra ella. Alternativas: git stash, git push --force-with-lease, git clean -n para ver qué se "
    "borraría, git branch -d. Si fallan los hooks de pre-commit, corrige lo que reportan en vez de saltarlos."
)


def evaluar(datos: dict) -> int:
    herramienta = datos.get("tool_name", "")
    entrada = datos.get("tool_input") or {}
    raiz = Path(os.environ.get("CLAUDE_PROJECT_DIR") or datos.get("cwd") or ".")
    apagadas = reglas_desactivadas(raiz)

    if herramienta in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        ruta = entrada.get("file_path") or entrada.get("notebook_path") or ""
        if que := config_protegida(ruta):
            return bloquear("autoprotección", f"{que} solo la cambia el usuario", "")
        if "archivos" not in apagadas and (motivo := regla_archivos(ruta)):
            return bloquear("archivos", motivo, "")
        return 0

    if herramienta != "Bash":
        return 0
    cmd = entrada.get("command", "")
    segs = segmentos(cmd)

    if que := toca_config_protegida(segs):
        return bloquear("autoprotección", f"{que} solo la cambia el usuario", "")
    for seg in segs:
        if "infra" not in apagadas and (motivo := regla_infra(seg)):
            return bloquear("infra", f"`{motivo}`", CONSEJO_INFRA)
        if "secretos" not in apagadas and (motivo := regla_secretos(seg)):
            return bloquear("secretos", motivo, CONSEJO_SECRETOS)
        if "local" not in apagadas and (motivo := regla_local(seg)):
            return bloquear("local", motivo, CONSEJO_LOCAL)
    if "sql" not in apagadas and (resultado := regla_sql(cmd, segs)):
        decision, motivo = resultado
        if decision == "bloquear":
            return bloquear("sql", motivo, CONSEJO_SQL)
        return preguntar(motivo)
    return 0


def main() -> int:
    try:
        return evaluar(json.load(sys.stdin))
    except Exception as error:  # falla cerrado
        print(f"barreras: error interno ({error!r}); se bloquea por precaución.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
