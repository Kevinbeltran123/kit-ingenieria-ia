"""Pruebas del hook de barreras: lo que se bloquea, lo que se pregunta y lo que pasa."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "barreras.py"
ENV_LIMPIO = {k: v for k, v in os.environ.items()
              if k not in ("DATABASE_URL", "PGHOST", "PGDATABASE", "ENV", "APP_ENV", "ENVIRONMENT", "STAGE",
                           "BARRERAS_DESACTIVAR")}


def correr(datos, raiz: Path, env_extra=None, crudo: str | None = None):
    env = {**ENV_LIMPIO, "CLAUDE_PROJECT_DIR": str(raiz), **(env_extra or {})}
    return subprocess.run([sys.executable, "-I", str(HOOK)],
                          input=crudo if crudo is not None else json.dumps(datos),
                          capture_output=True, text=True, env=env)


def bash(cmd, raiz, **kw):
    return correr({"tool_name": "Bash", "tool_input": {"command": cmd}}, raiz, **kw)


def editar(ruta, raiz, herramienta="Edit"):
    return correr({"tool_name": herramienta, "tool_input": {"file_path": str(ruta)}}, raiz)


def pregunta(r) -> bool:
    return r.returncode == 0 and r.stdout.strip() and \
        json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"] == "ask"


@pytest.fixture
def raiz(tmp_path):
    return tmp_path


# ---------- infra ----------

@pytest.mark.parametrize("cmd", [
    "terraform apply",
    "terraform apply -auto-approve",
    "terraform -chdir=infra apply",
    "tofu destroy",
    "terragrunt run-all apply",
    "terraform state rm aws_s3_bucket.x",
    "cdk deploy MiStack",
    "npx cdk deploy --all",
    "npx -y aws-cdk destroy",
    "sam deploy --guided",
    "pulumi up --yes",
    "serverless deploy",
    "aws cloudformation delete-stack --stack-name x",
    "aws --profile dev cloudformation deploy --template-file t.yml",
    "aws ec2 terminate-instances --instance-ids i-1",
    "aws s3 rm s3://bucket/x --recursive",
    "aws s3 rb s3://bucket --force",
    "aws s3 sync . s3://b --delete",
    "aws s3api put-bucket-policy --bucket b --policy file://p.json",
    "aws iam attach-role-policy --role-name r --policy-arn arn",
    "aws lambda update-function-code --function-name f --zip-file fileb://f.zip",
    "/usr/local/bin/terraform apply",
    "cd infra && terraform plan && terraform apply",
    "terraform plan; terraform apply",
    "echo hola | terraform apply",
    'bash -c "terraform apply -auto-approve"',
    "sh -c 'cdk deploy'",
    'eval "pulumi destroy"',
    "TF_LOG=debug terraform apply",
    "sudo terraform apply",
    "uv run cdk deploy",
    "aws-vault exec prod -- terraform apply",
    "echo $(terraform apply)",
    "terraform plan\nterraform apply",
    "timeout 60 terraform apply",
    "timeout -s KILL 60 terraform apply",   # -s y -k llevan valor: KILL no es la duración
    "timeout -k 5 60 terraform apply",
    "timeout --preserve-status -s TERM 2m cdk deploy",
])
def test_infra_bloqueada(cmd, raiz):
    r = bash(cmd, raiz)
    assert r.returncode == 2, cmd
    assert "infra" in r.stderr and "CI" in r.stderr


@pytest.mark.parametrize("cmd", [
    "terraform plan",
    "terraform plan -destroy",
    "terraform validate && terraform fmt -check",
    "terraform init",
    "cdk synth",
    "cdk diff",
    "sam validate",
    "pulumi preview",
    "aws s3 ls s3://bucket",
    "aws sts get-caller-identity",
    "aws ec2 describe-instances --region us-east-1",
    "aws cloudformation describe-stacks",
    "grep -rn apply .",
    "git commit -m 'terraform apply en CI'",
    "echo 'cdk deploy se corre en CI'",
    "pytest tests/test_deploy.py",
    "ls terraform",
])
def test_infra_permitida(cmd, raiz):
    assert bash(cmd, raiz).returncode == 0, cmd


# ---------- sql ----------

@pytest.mark.parametrize("cmd", [
    'psql "$PROD_DATABASE_URL" -c "DROP TABLE usuarios"',
    "psql -h db-prod.empresa.com -c 'truncate pedidos'",
    'psql postgresql://u@prd-db/app -c "DELETE FROM pedidos"',
    'psql -h prod-db -c "update pedidos set estado = 1"',
    'psql -h prod-db -c "ALTER TABLE pedidos ADD COLUMN x int"',
    'mysql -h production.db -e "GRANT ALL ON *.* TO x"',
    "psql -h prod-db <<EOF\ndrop table x;\nEOF",
    'docker exec -it db-prod psql -c "DROP DATABASE app"',
    "alembic -x env=production upgrade head",
    "ENV=prod alembic downgrade -1",
])
def test_sql_bloqueado_en_produccion(cmd, raiz):
    r = bash(cmd, raiz)
    assert r.returncode == 2, cmd
    assert "sql" in r.stderr


def test_produccion_detectada_por_variable_de_entorno(raiz):
    r = bash('psql "$DATABASE_URL" -c "DROP TABLE x"', raiz,
             env_extra={"DATABASE_URL": "postgresql://u@db.prod.internal/app"})
    assert r.returncode == 2


@pytest.mark.parametrize("cmd", [
    'psql -h localhost -c "DROP TABLE x"',
    'sqlite3 dev.db "truncate table x"',
    'psql -c "delete from pedidos"',
    'psql -c "UPDATE pedidos SET estado = 1"',
])
def test_sql_destructivo_fuera_de_prod_pregunta(cmd, raiz):
    assert pregunta(bash(cmd, raiz)), cmd


@pytest.mark.parametrize("cmd", [
    'psql -h prod-db -c "SELECT count(*) FROM pedidos"',
    'psql -h prod-db -c "DELETE FROM pedidos WHERE id = 3"',
    'psql -c "ALTER TABLE x ADD COLUMN y int"',
    'echo "drop table usuarios" > tests/fixtures/sql.txt',
    'grep -rn "DROP TABLE" migrations/',
    'pytest -k "truncate"',
    "alembic upgrade head",
    "alembic revision -m 'nueva'",
    "python -c 'print(\"production\")'",
])
def test_sql_permitido(cmd, raiz):
    r = bash(cmd, raiz)
    assert r.returncode == 0 and not r.stdout.strip(), cmd


# ---------- secretos ----------

@pytest.mark.parametrize("cmd", [
    "cat ~/.aws/credentials",
    "less $HOME/.aws/credentials",
    "head -5 /Users/kevin/.aws/credentials",
    "cat ~/.ssh/id_ed25519",
    "cp ~/.ssh/id_rsa /tmp/x",
    "printenv",
    "printenv AWS_SECRET_ACCESS_KEY",
    "env",
    "env | sort",
    "export -p",
    "echo $AWS_SECRET_ACCESS_KEY",
    'echo "${GITHUB_TOKEN}"',
    "cat .env",
    "grep KEY .env.production",
    'bash -c "cat ~/.aws/credentials"',
    "cat .envrc",                            # direnv
    "grep AWS_ .envrc",
])
def test_secretos_bloqueados(cmd, raiz):
    r = bash(cmd, raiz)
    assert r.returncode == 2, cmd
    assert "secretos" in r.stderr


@pytest.mark.parametrize("cmd", [
    "cat ~/.ssh/id_ed25519.pub",
    "ssh -i ~/.ssh/id_ed25519 servidor",
    "ls ~/.ssh",
    "printenv PATH",
    "env FOO=1 python script.py",
    "echo $HOME",
    "cat .env.example",
    "cat .envrc.example",
    "test -n \"$AWS_PROFILE\"",
    "cat ~/.aws/config",
])
def test_secretos_permitidos(cmd, raiz):
    assert bash(cmd, raiz).returncode == 0, cmd


# ---------- local (casos tomados del hook global de Kevin, más los de la revisión) ----------

@pytest.mark.parametrize("cmd", [
    "rm -rf ~/project",
    "rm -fr src",
    "rm -rf distribuidores",
    "rm -rf src/build_tools",
    "rm -r -f src",
    "rm --recursive --force src",
    "rm -Rf src",
    "sudo rm -rf /",
    "/bin/rm -rf src",
    "cd ~ && rm -rf project",
    "rm -rf ~/project /tmp/x",
    "bash -c 'rm -rf src'",
    "echo $(rm -rf src)",
    "find . -name '*.py' -delete",
    "find . -exec rm {} +",
    "git clean -fdx",
    "git clean -f",
    "git checkout -- .",
    "git checkout .",
    "git checkout HEAD .",
    "git restore .",
    "git stash drop",
    "git stash drop stash@{1}",
    "git stash clear",
    "git reset --hard",
    "git reset --hard HEAD~3",
    "git push --force origin main",
    "git push -f",
    "git push origin +main",
    "git -C repo push --force",
    "rm data.sqlite",
    "unlink app.db",
    "git commit --no-verify -m arreglo",
    "git commit -nm arreglo",
    "git branch -D feature",
    "git worktree remove --force ../wt",
])
def test_local_bloquea_lo_que_borra_trabajo(cmd, raiz):
    r = bash(cmd, raiz)
    assert r.returncode == 2, cmd
    assert "(local)" in r.stderr


@pytest.mark.parametrize("cmd", [
    "ls -la",
    "rm file.txt",
    "rm -rf /tmp/build",
    "rm -rf /private/tmp/claude-501/x",
    "rm -rf node_modules/.cache",
    "rm -rf .pytest_cache",
    "rm -rf .venv",
    "rm -rf dist build",
    "rm -rf src/app.egg-info htmlcov/",
    "rm -rf .tox .nox .coverage",
    "git push origin main",
    "git push --force-with-lease origin feature",
    "git checkout -b feature",
    "git checkout main",
    "git checkout -- app.py",
    "git stash",
    "git stash push -m wip",
    "git stash pop",
    "git stash list",
    "git reset HEAD file.txt",
    "git clean -n",
    "find . -name '*.py'",
    "grep -rn 'reset' src",
    "echo 'use --force-with-lease, never git push --force'",
    "git commit -m 'arreglo'",
    "git commit --amend --no-edit",
    "git branch -d feature",
    "git worktree remove ../wt",
])
def test_local_deja_pasar_lo_seguro(cmd, raiz):
    assert bash(cmd, raiz).returncode == 0, cmd


def test_local_se_puede_desactivar(raiz):
    assert bash("git reset --hard", raiz, env_extra={"BARRERAS_DESACTIVAR": "local"}).returncode == 0


# ---------- archivos ----------

@pytest.mark.parametrize("nombre", [".env", ".env.local", ".env.production", "uv.lock", "poetry.lock",
                                    "package-lock.json", "pnpm-lock.yaml", ".git/config"])
@pytest.mark.parametrize("herramienta", ["Edit", "Write", "MultiEdit"])
def test_archivos_protegidos(nombre, herramienta, raiz):
    r = editar(raiz / nombre, raiz, herramienta)
    assert r.returncode == 2, nombre
    assert "archivos" in r.stderr


@pytest.mark.parametrize("nombre", [".env.example", "app/main.py", ".github/workflows/ci.yml", "pyproject.toml"])
def test_archivos_permitidos(nombre, raiz):
    assert editar(raiz / nombre, raiz, "Write").returncode == 0


@pytest.mark.parametrize("carpeta", ["migrations/versions", "alembic/versions"])
def test_migracion_existente_bloqueada_y_nueva_permitida(carpeta, raiz):
    d = raiz / carpeta
    d.mkdir(parents=True)
    existente = d / "0001_inicial.py"
    existente.write_text("# migración")
    assert editar(existente, raiz).returncode == 2
    assert editar(d / "0002_nueva.py", raiz, "Write").returncode == 0


def test_migracion_django_existente_bloqueada(raiz):
    d = raiz / "app" / "migrations"
    d.mkdir(parents=True)
    (d / "0003_campo.py").write_text("#")
    assert editar(d / "0003_campo.py", raiz).returncode == 2
    assert editar(d / "0004_otro.py", raiz, "Write").returncode == 0


def git(raiz, *args):
    entorno = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    subprocess.run(["git", *args], cwd=raiz, env=entorno, check=True, capture_output=True)


def test_migracion_recien_generada_sin_commit_se_puede_editar(raiz):
    """La skill migraciones-alembic manda revisar y corregir lo que genera autogenerate antes del commit."""
    git(raiz, "init", "-q")
    d = raiz / "alembic" / "versions"
    d.mkdir(parents=True)
    (d / "0001_inicial.py").write_text("# aplicada")
    git(raiz, "add", ".")
    git(raiz, "-c", "user.email=p@example.com", "-c", "user.name=P", "commit", "-q", "-m", "inicial")
    (d / "0002_columna.py").write_text("# recién generada por autogenerate")
    assert editar(d / "0002_columna.py", raiz).returncode == 0
    assert editar(d / "0001_inicial.py", raiz).returncode == 2


def test_notebook_edit_usa_notebook_path(raiz):
    r = correr({"tool_name": "NotebookEdit", "tool_input": {"notebook_path": str(raiz / ".env")}}, raiz)
    assert r.returncode == 2


# ---------- desactivar reglas y autoprotección ----------

def test_desactivar_por_archivo(raiz):
    (raiz / ".claude").mkdir()
    (raiz / ".claude" / "barreras.json").write_text(json.dumps({"desactivar": ["infra"]}))
    assert bash("terraform apply", raiz).returncode == 0
    assert bash("cat ~/.aws/credentials", raiz).returncode == 2


def test_desactivar_por_variable(raiz):
    r = bash("cat .env", raiz, env_extra={"BARRERAS_DESACTIVAR": "secretos, sql"})
    assert r.returncode == 0


def test_config_invalida_aplica_todas_las_reglas(raiz):
    (raiz / ".claude").mkdir()
    (raiz / ".claude" / "barreras.json").write_text("{ no es json")
    assert bash("terraform apply", raiz).returncode == 2


def test_claude_no_puede_editar_la_config(raiz):
    assert editar(raiz / ".claude" / "barreras.json", raiz, "Write").returncode == 2
    assert bash("echo '{\"desactivar\": [\"infra\"]}' > .claude/barreras.json", raiz).returncode == 2
    assert bash("cat .claude/barreras.json", raiz).returncode == 0


def test_autoproteccion_no_se_puede_desactivar(raiz):
    r = editar(raiz / ".claude" / "barreras.json", raiz, "Write")
    assert r.returncode == 2
    r = correr({"tool_name": "Write", "tool_input": {"file_path": str(raiz / ".claude" / "barreras.json")}},
               raiz, env_extra={"BARRERAS_DESACTIVAR": "archivos,infra,sql,secretos"})
    assert r.returncode == 2


# ---------- robustez ----------

def test_falla_cerrado_con_json_invalido(raiz):
    r = correr(None, raiz, crudo="esto no es json")
    assert r.returncode == 2
    assert "error interno" in r.stderr


def test_otras_herramientas_pasan(raiz):
    assert correr({"tool_name": "Read", "tool_input": {"file_path": str(raiz / ".env")}}, raiz).returncode == 0


def test_comillas_sin_cerrar_no_rompen(raiz):
    assert bash("echo 'hola", raiz).returncode == 0
    assert bash("terraform apply 'x", raiz).returncode == 2
