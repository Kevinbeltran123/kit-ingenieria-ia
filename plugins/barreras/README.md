# barreras

Hook `PreToolUse` que frena acciones peligrosas antes de que Claude las ejecute. Python 3 de biblioteca estándar.
Si el hook falla por un error interno, **bloquea** (falla cerrado). Si ni siquiera arranca (por ejemplo, no hay
`python3`), Claude Code también bloquea gracias a `"onFailure": "block"`. Funciona con Python 3.9 o más nuevo.

| Regla | Bloquea | Permite |
|---|---|---|
| `infra` | `terraform/tofu/terragrunt apply·destroy·import·state rm`, `cdk deploy·destroy`, `sam deploy·delete·sync`, `pulumi up·destroy`, `serverless deploy·remove`, `aws cloudformation deploy·create/update/delete-stack`, `aws s3 rm·rb·mv·sync --delete`, `aws * delete-*·terminate-*·remove-*·revoke-*·detach-*`, políticas IAM/S3, `update-function-code` | `plan`, `diff`, `synth`, `validate`, `init`, `aws ... describe/list/get` |
| `sql` | Con un cliente (`psql`, `mysql`, `sqlite3`, `duckdb`…) y señal de producción (`prod`/`production`/`prd` en el comando o en `DATABASE_URL`, `PGHOST`, `ENV`…): `DROP`, `TRUNCATE`, `DELETE`/`UPDATE` sin `WHERE`, `ALTER`, `GRANT`, `REVOKE`; `alembic upgrade·downgrade·stamp` en producción. **Fuera de producción** `DROP`/`TRUNCATE`/sin `WHERE` no se bloquea: Claude Code **te pide confirmación** | `SELECT`, `DELETE ... WHERE` |
| `archivos` | Editar `.env*` (salvo `.env.example/.sample/.template`), lockfiles (`uv.lock`, `poetry.lock`, `package-lock.json`, `pnpm-lock.yaml`…), migraciones que ya están en git (`migrations/versions/`, `alembic/versions/`, Django `migrations/0001_*.py`) y `.git/` | Crear migraciones nuevas y corregirlas antes del commit |
| `secretos` | Leer `~/.aws/credentials`, llaves `~/.ssh/id_*`, `.env`; `printenv`/`env`/`export -p` completos; `echo $..._SECRET/_TOKEN/_PASSWORD` | Llaves `.pub`, `ssh -i llave`, `printenv PATH`, `.env.example` |
| `local` | Borrar trabajo: `rm -rf` fuera de `/tmp` y cachés, `find -delete`, `git reset --hard`, `git push --force`, `git clean -f`, `git checkout -- .`, `git restore .`, `git branch -D`, `git worktree remove --force`, `git commit --no-verify`, borrar `.db`/`.sqlite` | `rm` de un archivo, `rm -rf /tmp/...`, `--force-with-lease`, `git clean -n`, `git branch -d` |
| autoprotección | Que Claude edite `.claude/barreras.json` (no se puede desactivar) | Leerlo |

Detecta evasiones simples: `&&`, `;`, `|`, `$(...)`, saltos de línea, `bash -c "..."`, `eval`, prefijos (`sudo`, `VAR=x`, `uv run`, `npx`, `aws-vault exec ... --`) y mayúsculas/minúsculas en SQL.

## Desactivar una regla en un repo
Solo tú (Claude no puede editarlo):

```json
// .claude/barreras.json
{ "desactivar": ["sql"] }
```
o la variable `BARRERAS_DESACTIVAR=sql,infra` al lanzar Claude Code.

## Límites: esto no es la seguridad real
Un hook que lee texto se puede esquivar (scripts, `make deploy`, `npm run deploy`, SQL dentro de un archivo `-f x.sql`, alias, Python que llama a boto3). Tampoco ve los cambios que hace Bash sobre archivos protegidos (`sed -i .env`). La protección de verdad es:

1. **Permisos IAM de solo lectura** para el perfil de AWS del agente y un rol de base de datos con solo `SELECT` (ver `investigacion/05-devops-aws-github.md`).
2. **Reglas `deny` y sandbox** en el `.claude/settings.json` del repo:

```json
{
  "permissions": {
    "deny": [
      "Read(**/.env)", "Read(**/.env.*)", "Read(**/.envrc)", "Read(~/.aws/**)", "Read(~/.ssh/**)",
      "Edit(**/.env)", "Edit(**/.env.*)", "Edit(**/uv.lock)",
      "Bash(terraform apply *)", "Bash(terraform destroy *)",
      "Bash(cdk deploy *)", "Bash(cdk destroy *)", "Bash(pulumi up *)", "Bash(pulumi destroy *)"
    ]
  },
  "sandbox": { "enabled": true }
}
```
3. Los cambios de infraestructura y de base de datos de producción **solo desde CI**, con revisión en PR.

## Probar
    python3 -m pytest tests -q        # 139 pruebas
    claude --plugin-dir ./plugins/barreras
