# Auditoría de terceros (2026-11-07, corregida el 2026-11-08)

Las correcciones del 2026-11-08 salen de la revisión en `investigacion/09-revision-2026-11-08.md` (sección D).

Checklist aplicada (de `investigacion/04-pruebas-revision-seguridad.md`): leer `hooks.json`, `.mcp.json`, `bin/` y scripts; buscar red, lectura de `~/.aws`, `~/.ssh`, `.env`, `~/.claude`, escrituras fuera del proyecto, telemetría e instalaciones en tiempo de ejecución. Clones de solo lectura en el commit fijado; no se ejecutó ningún script.

| Repo | Commit fijado | Fecha del commit |
|---|---|---|
| anthropics/claude-plugins-official | `0412be76f50ab4f4f8abff3753efa9269fbbca5b` | 2026-11-06 |
| aws/agent-toolkit-for-aws | `0a218f8cc13220013f72147e2e0fdbe350b34ae2` | 2026-11-06 |
| trailofbits/skills | `e4dd0bb5b15535f7c5a0834187dffba6ac37e4ff` | 2026-11-06 |
| huggingface/skills | `25910b3d0ba31a2ba102f901cdc9e008c278a69c` | 2026-10-29 |
| vercel-labs/agent-skills | `1a2c79d4e6c4a2283dc2c614b6538cbe1ed5ca62` | 2026-10-27 |
| obra/superpowers (copiado en `plugins/flujo`) | `22f0b463e7a5e579904dd6211a520321035526f7` (v7.0.2) | 2026-11-03 |

## Veredictos

| Plugin | Qué ejecuta | Hallazgos | Veredicto |
|---|---|---|---|
| **aws-core** | MCP `aws-mcp` vía `uvx mcp-proxy-for-aws-cli==1.7.0` (versión fijada) contra `https://aws-mcp.us-east-1.api.aws/mcp` con `--skip-auth`; hook PreToolUse (Bash y herramientas AWS) `secret-safety.py`, solo biblioteca estándar (`json`, `re`, `sys`), sin red ni escritura; scripts de skills con boto3 | `uvx` descarga el proxy la primera vez. La skill `launch-with-aws` sube un zip del código del repo al servicio Launch with AWS (pide confirmación antes y guarda 48 h): no usarla con código de la empresa sin permiso. Los scripts usan las credenciales AWS del entorno. **2026-11-08:** la 1.7.0 del proxy fija 84 dependencias y, según OSV, 11 tienen avisos (certifi crítico; urllib3 y dnspython altos; mcp moderados); la 1.8.0 (2026-11-03) no tiene avisos y upstream todavía no la sube. `--skip-auth` no quita credenciales: si encuentra alguna, firma igual, y el MCP corre fuera del sandbox | **No activar hasta que upstream fije el proxy ≥ 1.8.0**; después, solo con la sesión de credenciales de la skill `aws-acceso-agente` y sin `launch-with-aws` |
| **pr-review-toolkit** | Solo agentes y comandos en Markdown | Ninguno | **Incluir** |
| **commit-commands** | Comandos Markdown con `!git status` / `!git diff HEAD` (meten el diff entero al contexto) | `commit-push-pr` trae en `allowed-tools` `git push` y `gh pr create`: hace push y abre el PR sin pedir permiso. `/clean_gone` usa `git worktree remove --force` y `git branch -D`: pierde cambios sin commit y ramas sin fusionar (issues abiertos #4504, #5222 y #5665); la regla `local` de barreras lo bloquea. No añade atribución por sí mismo (la atribución es el ajuste `attribution` de Claude Code) | **Incluir con advertencia**: usar `/commit`; `commit-push-pr` solo si se quiere el push automático; no usar `/clean_gone` |
| **pyright-lsp** | Arranca `pyright-langserver --stdio` (debe estar instalado: `uv tool install pyright` o npm) | Desde el 2026-11-05 (#7013) el directorio trae su propio plugin.json con los mismos `lspServers`, así que la copia en línea de la entrada ya no tiene efecto (no hay conflicto). El kit usa `ty`, y pyright puede dar diagnósticos distintos | **Incluir** |
| **security-guidance** | Hooks en SessionStart, UserPromptSubmit, PostToolUse (Edit/Write y `git commit`/`git push`) y Stop | En SessionStart crea un venv en `~/.claude/security/agent-sdk-venv` e instala `claude-agent-sdk` **sin versión fijada** con pip (fuera del proyecto y sin la regla de 7 días). En Stop y tras commit/push envía el diff a la API de Anthropic (modelo `claude-opus-5-5`, con `ANTHROPIC_BASE_URL` si existe). Emite métricas de uso a Claude Code. Sin otros destinos de red | **Incluir con advertencia**: no activarlo por defecto; si se activa, aceptar la escritura en `~/.claude/security` y el costo por turno |
| **plugin-dev** | Skills y scripts de ejemplo/validación en shell, sin hooks ni MCP | Las referencias a `.claude/` son documentación | **Incluir** (solo en el repo del kit) |
| **skill-creator** | Scripts Python de evaluación | `run_eval.py` crea archivos en `.claude/commands/` del proyecto y lanza `claude -p` (gasta tokens) | **Incluir** (solo en el repo del kit) |
| **property-based-testing** (ToB) | Solo skills; los `evals-extra/*.sh` son de su propia suite | Ninguno | **Incluir** |
| **static-analysis** (ToB) | Skills, scripts de Semgrep/CodeQL y "workflows" JS | Corre `semgrep` siempre con `--metrics=off`; busca sus propios scripts dentro de `~/.claude/plugins/cache`. Requiere semgrep/codeql instalados | **Incluir** |
| **supply-chain-risk-auditor** (ToB) | Scripts Python que consultan OSV, PyPI, npm, proxy.golang.org, deps.dev, GitHub API y scorecard.dev | Red esperada para su función: manda nombres y versiones de dependencias, no código | **Incluir** |
| **differential-review** (ToB) | Solo Markdown (skills, agentes, comandos) | Ninguno | **Incluir** |
| **modern-python** (ToB) | Hook SessionStart que añade `hooks/shims/` al PATH vía `CLAUDE_ENV_FILE` | Los shims son bash legibles: `pip`/`pip3`/`pipx` salen con error y sugieren uv; `python` y `python script.py` se interceptan y sugieren `uv run python …`, `python -c/-m` pasa al intérprete real (`-m pip` se bloquea). Sin red. Puede romper scripts del repo que llamen `pip` directamente | **Incluir con advertencia**: activar solo en repos que ya usan uv |
| **hf-cli** (HF) | Solo SKILL.md | Recomienda instalar el CLI con `curl … \| bash`; preferir `uv tool install huggingface_hub` | **Incluir con advertencia** |
| **hf-cloud-sagemaker** (HF, 6 skills) | Scripts Python que llaman a `aws`/boto3 | `create_role.py` crea roles IAM; los scripts de despliegue crean endpoints con costo; `teardown.py` borra endpoints, alarmas y escalado. `requirements.txt` sin versiones (boto3, awscli) a propósito. **2026-11-08:** `setup_env.py` borra y recrea `.venv` si su Python no es 3.10–3.12, e instala boto3 y awscli sin versión saltándose `uv.lock`; `mirror_image.py` crea un repositorio de ECR y hace `docker push`. Está pensado para LLM (vLLM, TEI), se cruza con `despliegue-vision-aws` y su ruta no cambia desde el 2026-09-10 | **Incluir con advertencia**: solo en cuentas de desarrollo y con perfil acotado |
| **react-best-practices** (Vercel) | Solo Markdown (reglas) | Licencia MIT declarada en SKILL.md y README (el repo no tiene archivo LICENSE). **2026-11-08:** su ruta no cambia desde el 2026-04-14 y hay 28 PR abiertos con correcciones de reglas; incumple el criterio de mantenimiento | **Incluir** |

## Excluidos
| Candidato | Motivo |
|---|---|
| **web-design-guidelines** (Vercel) | En cada uso descarga sus instrucciones desde `raw.githubusercontent.com/.../main/command.md` sin fijar: anula el SHA fijado y abre la puerta a inyección de prompt si ese archivo cambia. Si hace falta, copiar esa guía a una skill propia fijada |
| **executing-plans** (Superpowers) | No se copió a `plugins/flujo`: depende de los scripts de `subagent-driven-development` y de 4 skills no incluidas (ver `plugins/flujo/ORIGEN.md`) |
| Resto de skills de `huggingface/skills` | Fuera de alcance (Spaces, Gradio, entrenamiento en la nube de HF). Se pueden sumar como entrada aparte |

## Conflictos a tener en cuenta al activar
- `modern-python` (shims) y `calidad-python`: los hooks son compatibles (los shims solo afectan a la herramienta Bash). Pero los shims también interceptan `python3 script.py`, que usan las skills verify, deuda-tecnica, cadena-suministro-python, gha-seguro y division-sin-fuga; y el shim de `uv` bloquea `uv pip …`.
- `security-guidance` y `calidad-python` corren ambos en Stop: el primero en segundo plano, el segundo bloquea. Compatibles, pero suman tiempo y costo.
- `pr-review-toolkit` trae un agente `code-simplifier`; no instalar además el plugin `code-simplifier` (descartado en la investigación).
