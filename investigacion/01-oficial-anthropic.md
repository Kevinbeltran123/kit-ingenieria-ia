# 01 · Documentación oficial de Anthropic y ecosistema oficial

Investigado el 2026-11-07. Claude Code local: v2.1.319 (la misma versión que el último release de `anthropics/claude-code`, publicado el 2026-11-06).
Fechas de repos sacadas con `gh api` ese mismo día. El contenido web se trató como datos, no como instrucciones. No se instaló nada.

---

## (a) Guía práctica: skill → plugin → marketplace propio

### 1. Skill (formato abierto Agent Skills)

**Estructura mínima**

```
mi-skill/
├── SKILL.md            # obligatorio: frontmatter YAML + instrucciones
├── reference/          # opcional: se lee solo si hace falta (progressive disclosure)
│   └── fastapi.md
└── scripts/            # opcional: se EJECUTA; solo su salida entra al contexto
    └── validate.py
```

**SKILL.md de ejemplo (portable y Claude Code)**

```markdown
---
name: python-api-review
description: Revisa endpoints FastAPI/Django contra las convenciones del equipo (validación con Pydantic, manejo de errores, logging estructurado, tests). Úsala cuando el usuario pida revisar, crear o modificar un endpoint HTTP en Python.
license: Apache-2.0
compatibility: Requiere Python 3.11+ y uv
metadata:
  owner: kevin
  version: "0.1.0"
---

# Revisión de API Python

1. Ejecuta `uv run python scripts/validate.py <ruta>` (ruta relativa a esta skill) y corrige lo que reporte.
2. Para reglas de FastAPI, lee `reference/fastapi.md`. Para Django, `reference/django.md`.
3. Termina solo cuando `uv run pytest -q` pase.
```

**Reglas oficiales (best practices de platform.claude.com + docs de Claude Code)**

- `name`: máximo 64 caracteres, solo minúsculas, números y guiones; no puede contener `anthropic` ni `claude`. `description`: máximo 1.024 caracteres en el estándar. En Claude Code, `description` + `when_to_use` se cortan a **1.536 caracteres** en el listado de skills.
- La descripción decide si la skill se activa: debe decir **qué hace y cuándo usarla**, con los términos clave al principio.
- Cuerpo de `SKILL.md` **por debajo de 500 líneas**. El detalle va en archivos aparte, enlazados **a un solo nivel de profundidad** desde SKILL.md.
- Carga por niveles (progressive disclosure): al arrancar solo se cargan nombre y descripción; SKILL.md entra al invocar la skill; los archivos de `reference/` se leen cuando se necesitan. Los scripts se ejecutan sin cargarlos; solo su salida gasta tokens.
- Para operaciones deterministas, mejor un script que pedirle a Claude que genere el código. Deja claro si el script se **ejecuta** o se **lee** como referencia.
- Una vez cargada, la skill se queda en contexto durante toda la sesión: escribe instrucciones, no explicaciones.
- Nada de información con fecha de caducidad, una sola terminología, rutas con `/`.
- Ya no hace falta poner IMPORTANT o MAYÚSCULAS. Según la guía, a los modelos actuales eso les hace aplicar la regla de más. Si una regla no admite excepciones, conviértela en hook o en regla deny.

**Campos de frontmatter que solo existen en Claude Code** (rompen la skill en claude.ai o en la API, que solo aceptan `name, description, license, compatibility, metadata, allowed-tools`):
`when_to_use`, `argument-hint`, `arguments`, `disable-model-invocation` (solo la invocas tú con `/nombre`), `user-invocable: false` (solo la invoca Claude), `allowed-tools`, `context: fork` + `agent: Explore|Plan|<subagente>` (corre en un subagente), `paths`, `hooks`, `model`, `effort`, sustituciones `$ARGUMENTS`, `${CLAUDE_SESSION_ID}` e inyección dinámica de comandos.
→ **Recomendación para el kit:** usa solo los 6 campos del estándar en las skills que quieras portables (Cursor, Codex, Copilot y Gemini CLI también leen SKILL.md). Los campos propios de Claude Code, solo en skills de flujo de trabajo (por ejemplo, `disable-model-invocation: true` para `/deploy`).

**Dónde viven las skills:** `.claude/skills/<n>/SKILL.md` (proyecto, se commitea), `~/.claude/skills/` (usuario; **evitar**, por la regla de Kevin de nada global) o `<plugin>/skills/<n>/SKILL.md` (se invoca como `/plugin:skill`).

**Cómo evaluarlas (todo oficial)**

| Herramienta | Qué hace | Cuándo |
|---|---|---|
| `claude plugin validate <dir>` | Valida el frontmatter, `plugin.json` y `marketplace.json` (≥ v2.1.233). También funciona sobre `.claude/skills`. | En cada edición y en CI |
| `claude plugin eval init` / `claude plugin eval [dir]` | Suite de casos `evals/<caso>/prompt.md` + `graders/*.md`, con un grader `tool_used` que comprueba que la skill se activó. Compara contra una línea base sin el plugin, da exit codes para CI (0 = pasa, 1 = falla, 2 = parcial) y genera `--json` y un informe HTML (`--no-publish` lo deja local). Mocks de MCP con `--mocks record`. `eval init` requiere ≥ v2.1.269. | Antes de publicar cada versión del kit |
| Plugin `skill-creator` (oficial) | Bucle interactivo: `evals/evals.json` dentro de la skill, ejecuciones aisladas con y sin la skill, visor HTML para dar feedback y ajuste de la descripción. **No comparte formato** con `claude plugin eval`. | Mientras escribes una skill |
| `/skill-doctor` (bundled) | Coste en contexto y frecuencia de uso de cada skill; abre la pestaña Stats de `/plugin`. Con `-p` lo imprime como texto. | Mensual, para podar |
| `/doctor` y `/doctor prompt-audit <ruta>` | Estima cuánto contexto gasta el listado de skills y audita CLAUDE.md, rules, skills y agents. | Al añadir skills |

Advertencia oficial: `claude plugin eval` ejecuta en tu máquina, con tu identidad, los hooks y agents del plugin. Que pase la suite no dice nada sobre su seguridad.

### 2. Plugin

**Estructura (los componentes van en la raíz; dentro de `.claude-plugin/` solo va `plugin.json`)**

```
python-backend/
├── .claude-plugin/
│   └── plugin.json
├── skills/<n>/SKILL.md
├── agents/<n>.md           # subagentes (sin hooks, mcpServers ni permissionMode: se ignoran en plugins)
├── hooks/hooks.json        # hooks
├── .mcp.json               # servidores MCP
├── .lsp.json               # servidores LSP
├── bin/                    # ejecutables
└── evals/                  # casos para `claude plugin eval`
```

**plugin.json**

```json
{
  "$schema": "https://json.schemastore.org/claude-code-plugin-manifest.json",
  "name": "python-backend",
  "description": "Convenciones Python/FastAPI, revisión y verificación (ruff, mypy, pytest)",
  "author": { "name": "Kevin Beltran" },
  "license": "MIT",
  "keywords": ["python", "fastapi", "quality"]
}
```
- Sin `version`, la versión es el SHA del commit (12 caracteres) y los usuarios reciben cada commit. Con `version`, nadie recibe cambios hasta que la subas. **No pongas `version` a la vez en plugin.json y en marketplace.json**: gana plugin.json y `validate` avisa del desajuste.
- Otros campos útiles: `dependencies` (otros plugins), `userConfig` (pide valores al habilitar el plugin), `defaultEnabled`, `experimental.evals`.
- Variables: `${CLAUDE_PLUGIN_ROOT}` (cambia en cada versión), `${CLAUDE_PLUGIN_DATA}` (persiste entre versiones; ahí van venvs y cachés) y `${CLAUDE_PROJECT_DIR}`.
- Scaffold: `claude plugin init --with skills`. Desarrollo local: `claude --plugin-dir ./plugins/python-backend` y `/reload-plugins`.

**Hook de ejemplo (`hooks/hooks.json`): verificación determinista al terminar el turno**

```json
{
  "hooks": {
    "Stop": [
      { "hooks": [ { "type": "command",
        "command": "cd \"$CLAUDE_PROJECT_DIR\" && uv run ruff check . 1>&2 && uv run pytest -q 1>&2 || exit 2" } ] }
    ],
    "PreToolUse": [
      { "matcher": "Edit|Write",
        "hooks": [ { "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/bin/block-migrations-edit" } ] }
    ]
  }
}
```
Exit 2 bloquea y devuelve el stderr a Claude. Tras 8 bloqueos de Stop seguidos, Claude Code deja terminar el turno (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`). Para que el hook falle cerrado si se cae, usa `onFailure: "block"`. Los hooks `prompt` y `agent` **no son deterministas**: para hacer cumplir reglas, usa `command` o `http`. El filtro `if` es best-effort, así que para un allow/deny duro usa `permissions`.

### 3. Marketplace propio (`~/Desarrollo/kit-ingenieria-ia`)

```
kit-ingenieria-ia/
├── .claude-plugin/marketplace.json
└── plugins/
    ├── python-backend/
    └── code-quality/
```

**`.claude-plugin/marketplace.json`**

```json
{
  "name": "kit-ingenieria-ia",
  "description": "Kit de ingeniería con IA de Kevin",
  "owner": { "name": "Kevin Beltran" },
  "plugins": [
    { "name": "python-backend", "source": "./plugins/python-backend",
      "description": "Convenciones Python/FastAPI + verificación" },
    { "name": "superpowers-fijado",
      "source": { "source": "github", "repo": "obra/superpowers",
                  "ref": "v7.0.2", "sha": "<SHA de 40 caracteres del tag v7.0.2>" },
      "description": "Superpowers fijado a un commit revisado" }
  ]
}
```
- Obligatorio: `name`, `owner`, `plugins[]` (cada entrada con `name` y `source`). El `name` de la entrada debe coincidir con el `name` de su plugin.json.
- Tipos de `source`: ruta relativa `./…`, `github` (`repo, ref, sha`), `url` (git), `git-subdir` (`url, path, ref, sha`; sparse checkout de un monorepo), `npm` (sin scripts de instalación), `archive` (zip + `sha256`), `command`.
- **Fijar versiones:** `sha` de 40 caracteres (si van `ref` y `sha`, gana `sha`). Para un archivo, `sha256`. Para fijar el catálogo entero: `owner/repo#tag`.
- Nombres reservados (se rechazan): `claude-plugins-official`, `agent-skills`, `anthropic-*`, `claude-code-*` y otros. `kit-ingenieria-ia` no tiene problema.
- Valida con `claude plugin validate .` antes de cada commit.

**Instalarlo solo en un repo (nunca global)**: en el `.claude/settings.json` del repo, que se commitea:

```json
{
  "extraKnownMarketplaces": {
    "kit-ingenieria-ia": {
      "source": { "source": "github", "repo": "kevinbeltran/kit-ingenieria-ia", "ref": "v0.1.0" }
    }
  },
  "enabledPlugins": {
    "python-backend@kit-ingenieria-ia": true,
    "security-guidance@claude-plugins-official": true
  },
  "permissions": {
    "deny": ["Read(./.env)", "Read(./.env.*)", "Read(./secrets/**)"]
  }
}
```
Matices oficiales importantes:
- `extraKnownMarketplaces` del repo **solo se aplica después de aceptar el diálogo de confianza** de esa carpeta. En carpetas sin confianza se ignora sin avisar. En `-p`/CI solo funciona en carpetas que ya tienen la confianza aceptada.
- Habilitar el plugin en `.claude/settings.json` **no lo descarga**: cada persona ejecuta una vez `claude plugin install python-backend@kit-ingenieria-ia --scope project`. Para que lo tengas solo tú y en ese repo: `--scope local` (escribe en `.claude/settings.local.json`).
- Ojo: `claude plugin marketplace add` desde la shell **registra el marketplace en la configuración de usuario** aunque pases `--scope project`, y `known_marketplaces.json` es un archivo por usuario. El registro del catálogo siempre es por usuario. Lo que se puede limitar al repo es **la habilitación** de los plugins. Para no tocar `~/.claude/settings.json`, usa la vía `extraKnownMarketplaces` del repo en lugar de `marketplace add`.
- Precedencia: local > proyecto > usuario. `false` en local desactiva el plugin solo para ti.
- Auto-update: **desactivado por defecto** en marketplaces de terceros (el tuyo incluido) y activado en `claude-plugins-official`. Ojo: aunque tú lo habilites solo por repo, el plugin oficial **se actualiza solo** y el código que revisaste puede cambiar en disco. Si quieres congelar un plugin oficial, apúntalo desde tu marketplace con `github` + `sha` en lugar de instalarlo desde `@claude-plugins-official`.
- Para publicar una versión nueva: o subes `version`, o no pones `version` y los usuarios siguen el SHA. Para canales estable y beta: dos marketplaces o dos refs.

### 4. Hooks, subagentes, settings y CLAUDE.md: buenas prácticas oficiales actuales

- **Deterministas vs. no deterministas** (best-practices): CLAUDE.md, prompts y skills son *sugerencias*. Hooks, reglas deny, sandbox, tests y CI se *cumplen siempre*. Lo que no admite excepción va a un hook o a un deny.
- **CLAUDE.md:** menos de **200 líneas** por archivo. Los `@imports` organizan pero **no ahorran contexto**. Lo que solo aplica a una parte del código va en `.claude/rules/*.md` con `paths:` (solo se carga al tocar esos archivos). Los procedimientos de equipo van en skills. Claude Code lee `AGENTS.md`. `/init` con `CLAUDE_CODE_NEW_INIT=1` propone CLAUDE.md, skills y hooks. `/doctor prompt-audit` sirve para auditarlo.
- **Settings:** `.claude/settings.json` (se commitea, para todos), `.claude/settings.local.json` (personal) y managed (organización). Las reglas `deny` del repo aplican de inmediato. Las `allow` y los hooks del repo esperan al diálogo de confianza. `deny` se respeta incluso en auto y `bypassPermissions`.
- **Subagentes** (`.claude/agents/*.md`): campos `description, tools, disallowedTools, model, permissionMode, mcpServers, hooks, maxTurns, skills, memory, effort, background, isolation`. Cada uno con un foco, descripciones que no se solapen (presupuesto de 15k tokens para todas), herramientas mínimas y `model: haiku` para tareas mecánicas. La documentación oficial dice que delegar en un subagente **no mejora la respuesta**; lo que ayuda es un revisor *fresco*, que no ha visto tu razonamiento. En plugins, `hooks`, `mcpServers` y `permissionMode` del agente se ignoran por seguridad.
- **Seguridad de plugins:** revisa `hooks/hooks.json`, `.mcp.json` y `bin/` antes de instalar. Un MCP stdio es un proceso local con tus permisos. Comprueba el origen con `claude plugin marketplace list`. El nombre del marketplace dice quién lo publica, no qué hace cada plugin.

---

## (b) Candidatos oficiales

Marketplaces y repos base (datos `gh api`, 2026-11-07):

| Repo | Último push | ★ | Estado |
|---|---|---|---|
| anthropics/claude-plugins-official (marketplace `claude-plugins-official`, 317 plugins) | 2026-11-07 | 46.4k | Activo; se registra automáticamente |
| anthropics/claude-plugins-community (`claude-community`; casi todo fijado por SHA) | 2026-11-07 | 4.8k | Activo; hay que añadirlo a mano |
| anthropics/skills (19 skills de ejemplo; también es marketplace) | 2026-11-06 (mcp-builder actualizado el 2026-10-28) | 188.9k | Activo |
| agentskills/agentskills (especificación) | 2026-11-04 (commits de la donación a AAIF) | 27k | Activo; donado a AAIF/Linux Foundation el 2026-10-22 |
| anthropics/claude-code (marketplace `claude-code-plugins`) | 2026-11-06, v2.1.319 | 155k | El CLI está activo, pero **ese marketplace está deprecado** según la documentación |
| anthropics/claude-code-action | 2026-11-06, v1.0.269 | 9.8k | Activo |
| anthropics/claude-code-security-review | **2026-02-11** | 6.8k | Sin actividad hace 9 meses |

Agent Skills como estándar: Anthropic anunció el 2026-10-22 más de 70 plataformas, entre ellas ChatGPT/Codex, Cursor, GitHub Copilot, VS Code, Gemini CLI, Junie, Kiro, Amp, OpenCode, Goose, Roo Code, OpenHands y Factory (Droid). Lista completa: agentskills.io/clients.

Plugins (ruta en el repo oficial, salvo los marcados como externos). "Último commit" = último commit que toca esa ruta. **Ojo:** muchos internos tienen un commit masivo del 2026-10-26, así que esa fecha indica "tocado", no necesariamente "desarrollo activo".

| Nombre | Qué hace | Último commit/release | Evidencia | Riesgo (qué ejecuta) | Veredicto |
|---|---|---|---|---|---|
| **security-guidance** (Anthropic) | Avisos por regex en Edit/Write (~25 patrones: `yaml.load`, `pickle`, secretos…), revisión del diff con un LLM en Stop y revisor agéntico en `git commit/push` | 2026-11-06, v2.0.18 | La recomiendan WotAI (2026-11-02, como estándar de equipo), ReviewRamble (4,2/5, 2026-11-06), ClockedCode (2026-07-24, "~0 tokens fijos") y coworkstrategy | **Hooks** en SessionStart, UserPromptSubmit, PostToolUse y Stop. En SessionStart **crea un venv en `~/.claude/security/` y hace `pip install` del Agent SDK** (instalación en red, fuera del repo). Envía tus diffs al modelo Opus (gasta tu cuota). Desactivable con `ENABLE_CODE_SECURITY_REVIEW=0` | **Recomendado** (por repo). Ten en cuenta el pip install y el coste por turno. Si quieres congelarlo, fíjalo por SHA en tu marketplace |
| **claude-security** (Anthropic) | Escaneo profundo de vulnerabilidades con nivel de esfuerzo; cada hallazgo se pone a prueba antes de reportarlo | 2026-09-25, v0.12.0 | Oficial, categoría security | Hooks (banner, métricas, sugerencias después de `git push` y `gh pr create`), scripts Python y workflows | **Opcional**: auditoría puntual, no siempre activo |
| **pyright-lsp** (Anthropic) | LSP de Pyright: tipos y diagnósticos en tiempo real | 2026-11-06 | Las guías la recomiendan como "el LSP de tu lenguaje" (WotAI, coworkstrategy) | Arranca `pyright` local (hay que instalarlo; usa bastante RAM en repos grandes) | **Recomendado** |
| **skill-creator** (Anthropic; también en anthropics/skills) | Crear y mejorar skills con evals y benchmarks | **2026-04-23** (en la ruta del plugin); anthropics/skills, 2026-04-20 | La documentación oficial actual de skills lo indica para evaluar skills; más de 385k instalaciones (vibecoding.app, 2026-07) | Solo skills y scripts Python que corren en local | **Recomendado como herramienta de autoría**, aunque no cumple el criterio de 6 semanas de actividad. Combínalo con `claude plugin eval`, que es nativo y está activo |
| **plugin-dev** (Anthropic) | 7 skills y agentes para escribir plugins, hooks y MCP | 2026-10-26, v0.1.1 | Oficial | Solo prompts | **Recomendado** mientras construyes el kit; luego se desactiva |
| **code-review** (Anthropic) | Revisión de PR con varios agentes y filtro por confianza | 2026-10-26, v1.0.1 | 438k instalaciones (WotAI, 2026-10-21) | Commands y agents; usa `gh` | **Opcional**: ya existe el bundled `/code-review` (con niveles low…ultra) en el CLI. Mejor el nativo, para no duplicar |
| **pr-review-toolkit** (Anthropic) | Agentes especializados: tests, manejo de errores, diseño de tipos, comentarios y simplificación | 2026-10-26, v1.0.1 | coworkstrategy, the-maze (2026-10-20) | Agents | **Opcional**: elige uno de los dos con code-review |
| **feature-dev** (Anthropic) | Flujo explorar → arquitectura → implementar → revisar | 2026-10-26 | coworkstrategy; vibecoding: "se solapa con Superpowers, elige uno" | Agents | **Opcional** (solapa con superpowers) |
| **commit-commands** (Anthropic) | `/commit`, push y PR | 2026-10-26 | WotAI (estándar de equipo) | Commands que hacen git push | **Opcional** (Kevin ya tiene sus skills commit/create-pr) |
| **claude-md-management** (Anthropic) | Auditar CLAUDE.md y registrar lo aprendido en la sesión | **2026-02-20** | WotAI | Commands y skills | **Descartar** (inactivo). Usa `/doctor prompt-audit` y `/init`, que son nativos |
| **claude-code-setup** (Anthropic) | Analiza el repo y recomienda hooks, skills y MCP | **2026-05-28** | — | Solo skill | **Descartar** (inactivo; sirve `CLAUDE_CODE_NEW_INIT=1 /init`) |
| **hookify** (Anthropic) | Crear hooks a partir de reglas en archivos `.local.md` | 2026-10-26 | — | **Hooks Python en PreToolUse, PostToolUse, Stop y UserPromptSubmit sobre TODAS las herramientas** | **Descartar**: escribe tus hooks a mano (es más auditable). La documentación dice que basta pedir "write a hook that…" |
| **code-simplifier** (Anthropic) | Agente que simplifica código | **2026-02-20** | 346k instalaciones | Agent | **Descartar** el plugin; el CLI ya trae `/simplify` |
| **ralph-loop** (Anthropic) | Bucle autónomo a través del hook Stop | 2026-10-26 | — | Hook Stop que reinyecta el prompt (gasto sin límite) | **Descartar** para trabajo diario |
| **mcp-server-dev** / **agent-sdk-dev** (Anthropic) | Construir MCP y agentes con el SDK | 2026-04-28 / — | — | Skills | **Opcional**, solo si vas a construir MCP |
| **context7** (MCP de Upstash, en el marketplace oficial) | Documentación de librerías actualizada | Ruta en el oficial: 2026-09-30; upstash/context7: 2026-11-06, mcpb-v4.5.1 | 417k instalaciones; casi todas las guías lo incluyen | MCP **remoto** (tus consultas salen a Upstash) | **Recomendado** (lo verá también el investigador de MCP) |
| **github** (MCP oficial de GitHub) | Issues, PR y código | Ruta: **2025-12-02**; github/github-mcp-server: 2026-11-06, v2.1.0 | WotAI | MCP con token de GitHub (permisos amplios) | **Opcional**: `gh` CLI suele bastar. Si lo usas, configura el servidor upstream directamente, porque la entrada del plugin está vieja |
| **superpowers** (externo: obra/superpowers) | Metodología: brainstorm, planes, TDD, subagentes, debugging | 2026-11-03, v7.0.2 | 314k ★; ~1M instalaciones; HowToGeek (2026-08-03, "non-negotiable"), ReviewRamble #1 (2026-11-06), Medium (2026-11-02) | Unas 14 skills + 1 hook (SessionStart), ~584 tokens fijos (ClockedCode). Coste alto en ejecuciones largas | **Recomendado, fijado por SHA** (y que el investigador de comunidad lo evalúe a fondo) |
| **mattpocock-skills** (externo) | Skills pequeñas: grill-me, spec/tickets, TDD, revisión, handoff | 2026-11-05, v1.3.2 | 318k ★; ReviewRamble #2; Medium (2026-11-02) | Skills. skillcritic avisa de que **"edita archivos fuera del proyecto"** (`/setup-…`) | **Opcional**; revísalo antes |
| **aws-core / aws-serverless / deploy-on-aws / databases-on-aws** (externos de AWS; aws/agent-toolkit-for-aws y awslabs/agent-plugins) | Skills y MCP de AWS: IaC, serverless, despliegue, bases de datos | 2026-11-07 / 2026-11-05 | Mantenido por AWS, publicado en el marketplace oficial | MCP que **usan tus credenciales de AWS** | **Opcional** (para el investigador de AWS); en solo lectura o con un perfil de mínimo privilegio |
| **semgrep** (externo) | SAST en el bucle | 2026-11-05 | Partner del marketplace oficial | MCP/CLI de Semgrep (puede enviar código a la nube según configuración) | **Opcional** (para el investigador de seguridad) |
| **sonarqube** (externo) | Calidad y seguridad de SonarQube en el bucle | 2026-11-05, release 2.0.0 (2026-05) | Partner | MCP; token de Sonar | Opcional, solo si la empresa usa Sonar |
| **pydantic-ai / logfire** (externos de Pydantic) | Patrones de Pydantic AI; instrumentación con Logfire | 2026-10-28 | Mantenido por Pydantic | Skills | **Opcional**, solo si usas esas librerías |
| **mlflow** (externo) | Trazas y evaluación de agentes con MLflow | 2026-11-04 | Mantenido por MLflow | Skills | Opcional (datos/ML) |
| **sentry** (externo) | Errores y stack traces | 2026-10-26 | Mantenido por Sentry | MCP (token) | Opcional, si la empresa usa Sentry |
| **terraform** (plugin interno + hashicorp/terraform-mcp-server) | Registry y workspaces de Terraform | MCP: 2026-11-06, v1.4.1 | HashiCorp | MCP (Docker/binario) | Opcional (DevOps) |
| anthropics/skills: **mcp-builder**, **claude-api**, **webapp-testing**, **pdf/docx/xlsx** | Skills de ejemplo y referencia | mcp-builder: 2026-10-28; Office pasó a Apache 2.0 el 2026-11-06 | Repo oficial, 189k ★ | Scripts Python locales | **Opcional**: tómalas como plantillas de autoría. `claude-api` ya viene bundled |
| **claude-code-action** (GitHub Action) | Claude en PR e issues dentro de CI | 2026-11-06, v1.0.269 | Oficial y activo | Corre en CI con `ANTHROPIC_API_KEY`. Fija la action por SHA | **Recomendado para CI** (revisión de PR) |
| **claude-code-security-review** (Action) | Revisión de seguridad de PR en CI | **2026-02-11** | 6.8k ★ | Action | **Descartar** (inactivo). Usa claude-code-action con el bundled `/security-review` |
| Marketplace `claude-code-plugins` (anthropics/claude-code) | Marketplace antiguo | — | La documentación lo marca como **deprecado** | — | **Descartar**: instala desde `@claude-plugins-official` |

**Ya incluido en el CLI v2.1.319 (no hace falta plugin):** `/code-review`, `/security-review`, `/simplify`, `/doctor` (+ `prompt-audit`), `/skill-doctor`, `/init`, `/claude-api`, `/loop`, `/batch`, `/debug`, `claude plugin validate|eval|init|tag`.

---

## (c) Fuentes (consultadas el 2026-11-07)

Documentación oficial:
- Skills en Claude Code (frontmatter, invocación, `context: fork`, `/skill-doctor`, skill-creator): https://code.claude.com/docs/en/skills
- Buenas prácticas de autoría de skills: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- Crear un plugin: https://code.claude.com/docs/en/plugins/create
- Referencia del manifest `plugin.json`: https://code.claude.com/docs/en/plugins-reference (y /plugins/manifest-reference)
- Crear un marketplace: https://code.claude.com/docs/en/plugin-marketplaces
- Referencia de marketplace (sources, `ref`/`sha`, nombres reservados): https://code.claude.com/docs/en/plugins/marketplace-reference
- Alojar y mantener un marketplace (versiones, auto-update, canales): https://code.claude.com/docs/en/plugins/host-marketplace
- Instalar plugins y scopes: https://code.claude.com/docs/en/discover-plugins
- Carga y versiones: https://code.claude.com/docs/en/plugins/loading
- Organización (`extraKnownMarketplaces`, `strictKnownMarketplaces`, por repo): https://code.claude.com/docs/en/plugins/org
- Seguridad y confianza en plugins: https://code.claude.com/docs/en/plugins/security
- Marketplaces de Anthropic (official, community, deprecado): https://code.claude.com/docs/en/plugins/anthropic-marketplaces
- Evals de plugins: https://code.claude.com/docs/en/plugin-evals · CLI: https://code.claude.com/docs/en/plugins/cli-reference
- Best practices (deterministas vs. no deterministas, consejos antiguos ya retirados): https://code.claude.com/docs/en/best-practices
- Memoria / CLAUDE.md: https://code.claude.com/docs/en/memory
- Hooks: https://code.claude.com/docs/en/hooks-guide · Subagentes: https://code.claude.com/docs/en/sub-agents
- Agent Skills: https://agentskills.io · evals: https://agentskills.io/skill-creation/evaluating-skills
- Donación a AAIF (2026-10-22): https://www.anthropic.com/news/donating-agent-skills-to-the-agentic-ai-foundation · https://www.linuxfoundation.org/press/agentic-ai-foundation-announces-four-new-projects-agent-skills-open-responses-openenv-and-opensandbox

Repos (datos `gh api`, 2026-11-07): github.com/anthropics/claude-plugins-official (`.claude-plugin/marketplace.json`, `plugins/security-guidance/hooks/hooks.json`, `ensure_agent_sdk.py`), anthropics/claude-plugins-community, anthropics/skills, agentskills/agentskills, anthropics/claude-code, anthropics/claude-code-action, anthropics/claude-code-security-review, obra/superpowers, mattpocock/skills, aws/agent-toolkit-for-aws, awslabs/agent-plugins, upstash/context7, github/github-mcp-server, hashicorp/terraform-mcp-server, semgrep/mcp-marketplace, SonarSource/sonarqube-agent-plugins, pydantic/skills, mlflow/skills.

Evidencia de terceros (no oficiales; medios de reseñas, con sesgo posible):
- WotAI, "Best Claude plugins for teams" (Alex Kim, 2026-11-02): https://wotai.co/blog/best-claude-plugins
- ReviewRamble, ranking (2026-11-06): https://www.reviewramble.com/best/claude-code-plugins-and-agent-skills
- Medium, "Don't install 30 Claude Code plugins. Install these 6." (2026-11-02): https://medium.com/write-a-catalyst/dont-install-30-claude-code-plugins-install-these-6-dcf74f8ecc26
- HowToGeek (Dibakar Ghosh, 2026-08-03): https://www.howtogeek.com/the-best-claude-code-plugins/
- ClockedCode, coste en tokens medido (2026-07-24): https://clockedcode.com/blog/best-claude-code-plugins
- coworkstrategy (2026-06-09): https://coworkstrategy.com/plugins/best-claude-code-plugins/
- skillcritic, reseñas de seguridad (2026-11-02): https://skillcritic.com/plugins
- claude-world, AAIF y portabilidad (2026-11-04): https://claude-world.com/articles/agent-skills-agentic-ai-foundation
