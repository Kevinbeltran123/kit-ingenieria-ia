# Resumen consolidado (2026-11-07)

Fuente: los 8 informes de esta carpeta. Datos de GitHub verificados con `gh api` el mismo día.
Nada instalado todavía.

## Principio que repiten todos los informes
La calidad no viene de muchas skills sino de **sensores** (linters, tipos, pruebas) que el agente
está obligado a correr antes de terminar (hooks), más **pocas skills propias** que describan cómo
trabaja el equipo. dbt Labs midió que skills genéricas de fabricante casi no mejoran a los modelos
actuales; Vercel vio su skill ignorada en el 56 % de los casos.

## Capa 1 — Base (sin plugins)
- Claude Code: plan mode → implementar → verificar (hook Stop). `gh` CLI en vez del MCP de GitHub.
- Worktrees nativos (`claude -w`), `/init`, subagente Explore, `/code-review`, `/security-review`, `/simplify`.

## Capa 2 — Herramientas deterministas (van en cada repo Python)
| Uso | Herramienta |
|---|---|
| Lint/format | ruff |
| Paquetes | uv (con `exclude-newer = "7 days"`) |
| Tipos | ty fijado exacto (beta) + pyright de respaldo en CI |
| Arquitectura | import-linter (capas domain ← application ← adapters ← entrypoints) |
| Deuda | deptry, vulture, complexipy; jscpd en CI como reporte |
| Hooks git | prek |
| Pruebas | pytest, Hypothesis, mutmut, testcontainers (+LocalStack), schemathesis |
| Seguridad | pip-audit, osv-scanner, gitleaks, bandit, Semgrep CE, zizmor, pinact |
| IaC/contenedores | checkov, hadolint, tflint (si Terraform), Trivy fijado por SHA |
| Docs | Zensical, ADR con MADR 4 |
| Perfilado | py-spy |

## Capa 3 — Plugins/skills de terceros recomendados (fijados por SHA)
| Plugin | Para qué | Nota |
|---|---|---|
| Superpowers (obra) v7.0.2 | flujo TDD/debugging/planes | **decisión pendiente**: plugin completo vs solo skills sueltas |
| aws-core (aws/agent-toolkit-for-aws) | 25 skills AWS + MCP de 8 herramientas | sucesor de awslabs/mcp; perfil solo lectura |
| pr-review-toolkit (oficial) | revisión, detecta tests vacíos y fallos silenciosos | reemplaza review-local-changes |
| Trail of Bits skills (selección) | property-based-testing, static-analysis, supply-chain, modern-python | revisar sus hooks antes |
| pyright-lsp (oficial) | navegación por tipos | |
| CodeGraph | entender repos grandes | apagar telemetría |
| Context7 (modo CLI) | docs al día | versión posterior a CVE-2026-75130 |
| Playwright CLI + skills | navegador para agentes | menos tokens que el MCP |
| vercel-react-best-practices, frontend-design, impeccable | frontend | |
| Hugging Face skills (hf-cloud-sagemaker, hf-cli), MLflow MCP + skills | ML en AWS | |
| commit-commands (oficial) | commits/PR | desactivar atribución a Claude |
| claude-code-action | revisión en CI | SHA fijo, permisos mínimos |
| ccusage + ccstatusline | costo y status line | |

Condicionales según lo que use la empresa: dbt / Dagster / Airflow / dlt / Polars, Terraform,
Sentry, Grafana/Datadog, Linear/Jira, FiftyOne, W&B, Ultralytics (AGPL: requiere licencia).

## Capa 4 — Skills propias (los vacíos)
Prioridad alta:
1. `verify` — corre los sensores en orden y resume.
2. `arquitectura-python` — hexagonal pragmática FastAPI + AWS, incluido cuándo NO abstraer.
3. `division-sin-fuga` — split por palma/lote/finca/fecha con script que falla si hay fuga.
4. `formular-modelo-optimizacion` — OR-Tools/HiGHS: unidades, instancia mínima, verificador de factibilidad.
5. `python-test-quality` + `mutmut-gate` — contra tests que no prueban nada.
6. `aws-acceso-agente` + hook que bloquee `apply/deploy/destroy` y DDL en producción.

Después: `deuda-tecnica`, `documentacion-python`, `ingesta-idempotente`, `contratos-datos-pandera`,
`migraciones-alembic-sqlalchemy2`, `gha-seguro`, `dockerfile-python-uv`, `observabilidad-python`,
`evaluador-bloqueado` (ML), `audit-plugin`, `rendimiento-python`.

## Descartados (motivo principal)
- Por inactivos: task-master, claude-squad, crystal, crystaldba/postgres-mcp, radon/xenon, interrogate,
  claude-code-security-review, code-simplifier, gitingest, next-devtools-mcp, Label Studio MCP.
- Por riesgo: claude-flow/Ruflo, GSD (token $GSD), claude-mem (subía prompts), clones de ECC/antislop.
- Por peso o solape: spec-kit, BMAD, github-mcp-server completo, Playwright MCP, ui-ux-pro-max.
- Por licencia: GitNexus (no comercial), deadcode y repowise (AGPL).

## Conflictos entre informes (resueltos o por decidir)
- Superpowers: el de harnesses dice plugin completo; el de pruebas dice solo skills (hooks + contexto). → decidir.
- Registro de marketplace siempre queda a nivel usuario; solo la activación es por repo.

## Cambios sobre lo ya instalado
| Instalado | Acción |
|---|---|
| test-driven-development, systematic-debugging | actualizar (copia de mayo) |
| code-review, security-review, /simplify | conservar (vienen con el CLI) |
| review-local-changes | reemplazar → pr-review-toolkit |
| software-architecture, write-concisely, code-simplifier | reemplazar → skills propias |
| commit, create-pr | reemplazar → commit-commands (create-pr tiene un bug) |
| playwright-skill | reemplazar → Playwright CLI |
| ui-ux-pro-max, antislop (suite) | quitar del kit (antislop-code opcional, fijado) |
| security-guidance (global) | pasar a alcance de proyecto |
| context7 | pasar a modo CLI, versión parcheada |
| supabase-postgres-best-practices, frontend-design, impeccable, CodeGraph | conservar |

## Datos que faltan de la empresa
Orquestador de datos, Terraform vs CDK, monitoreo (Sentry/Datadog/Grafana), gestor de tareas,
framework web, y si el modelo de palmas será producto cerrado (licencias).
