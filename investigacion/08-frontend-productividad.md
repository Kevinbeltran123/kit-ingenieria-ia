# 08 — Frontend/full stack, docs vivas y productividad con agentes

Investigación del 2026-11-07. Criterio de vigencia: actividad desde ~2026-09-25 (commits o releases), verificada con `gh api` el mismo día. El contenido web se trató como datos no confiables. No se instaló nada.

Costo de contexto, en tokens aproximados (1 token ≈ 4 caracteres):
- **Skill**: en reposo solo carga la descripción (~50–150 tokens); al activarse carga el SKILL.md entero.
- **MCP**: carga los esquemas de sus herramientas (Claude Code los difiere con *tool search*, pero cada respuesta entra al contexto).
- **CLI**: casi cero en reposo; paga solo la salida que el agente lee.

---

## 1. Tabla de candidatos

### 1.1 Frontend (React/Next.js/TypeScript, navegador, a11y, rendimiento)

| Nombre | Tipo | Qué hace | Último commit / release | Evidencia | Costo de contexto | Riesgo | Veredicto |
|---|---|---|---|---|---|---|---|
| **Playwright CLI** (`microsoft/playwright-cli`) + sus skills | CLI + skill | Maneja el navegador con comandos de shell; las capturas de página se guardan en archivos y el agente solo lee las que necesita | commit 2026-11-05; v0.1.23 2026-10-31; skills 2026-11-05 | La guía oficial de Playwright la recomienda para agentes de código frente al MCP ([playwright.dev/docs/getting-started-cli](https://playwright.dev/docs/getting-started-cli)). Medición de Better Stack: ~68 tokens de descripción frente a ~3,6k del esquema MCP ([betterstack, 2026-02-22](https://betterstack.com/community/guides/ai/playwright-cli-vs-mcp-browser)). Mediciones de oct-2026 en [webcrawlerapi](http://webcrawlerapi.com/blog/playwright-cli) y [casely](https://casely.digital/blog/playwright-cli-vs-mcp) | Muy bajo | Bajo (Microsoft). Instalar el skill con `install --skills` a nivel de proyecto, nunca con `-g` | **ADOPTAR** como navegador principal |
| **Playwright MCP** (`microsoft/playwright-mcp`) | MCP | Más de 70 herramientas de navegador; devuelve el árbol de accesibilidad después de cada acción | commit 2026-11-06; v0.0.84 2026-10-31 | La tabla oficial lo marca como "Token cost: Higher" ([playwright.dev/mcp](https://playwright.dev/mcp/introduction)). Se reportan ~4,2k tokens de esquemas y 3,8k–12k por cada captura de página ([egolite, act. 2026-10-31](https://lite.ego.app/article/playwright-mcp-vs-cli)) | Alto | Bajo | **NO por defecto**; solo para exploración larga sin shell |
| **Chrome DevTools MCP / CLI** (`ChromeDevTools/chrome-devtools-mcp`) | MCP + CLI + skills (plugin) | Trazas de rendimiento (LCP/INP/CLS con datos de campo de CrUX), red, consola con source maps | commit 2026-11-06; v1.12.0 2026-10-22; skills 2026-11-04 | Guía oficial de Google ([developer.chrome.com](https://developer.chrome.com/docs/devtools/agents/get-started)). Plugin oficial de Claude con ~102k instalaciones ([claude.com/plugins](https://claude.com/plugins/chrome-devtools-mcp)) | Alto en modo completo (se reportan ~17k tokens de esquemas y el issue #726 con un clic que infló el contexto, citado en [webfuse](https://www.webfuse.com/blog/playwright-mcp-vs-playwright-cli)). Bajo con la CLI o con `--slim` | Medio: por defecto envía las URL de las trazas a la API de CrUX (`--performance-crux=false` lo apaga). `--autoConnect` hereda tu sesión de Chrome | **ADOPTAR solo para rendimiento/Core Web Vitals**, en modo CLI o `--slim`, activado por proyecto |
| **agent-browser** (`vercel-labs/agent-browser`) | CLI + skill | Navegador para agentes, con inspección del árbol de React y Web Vitals | commit 2026-11-08; v0.41.2 2026-11-03 | Next.js 16.3 lo exige para su skill `next-dev-loop` ([nextjs.org/blog/next-16-3-ai-improvements](https://nextjs.org/blog/next-16-3-ai-improvements)) | Bajo | Bajo/medio (laboratorio de Vercel) | **OPCIONAL**: solo en repos con Next.js 16.3+ |
| **Docs empaquetadas de Next.js + skills de `vercel/next.js`** | docs locales + skills | `next dev` genera AGENTS.md/CLAUDE.md que apuntan a las docs de la versión instalada (`node_modules/next/dist/docs`). Skills de flujo: `next-dev-loop` y `next-cache-components-*` | skills/ 2026-11-04 | Anuncio oficial de 16.3 (enlace anterior). `vercel-labs/next-skills` quedó obsoleto y migró aquí ([README](https://github.com/vercel-labs/next-skills/blob/main/README.md)) | Bajo | Bajo | **ADOPTAR** si el repo usa Next.js 16.3+ (no hace falta Context7 para Next) |
| `next-devtools-mcp` (`vercel/next-devtools-mcp`) | MCP | Conector delgado al endpoint `/_next/mcp` (rutas, errores, logs) | último commit 2026-09-15; v0.4.0 2026-06-24 | Docs de Next.js ([nextjs.org/docs/app/guides/mcp](https://nextjs.org/docs/app/guides/mcp)) | Bajo (4 herramientas) | Bajo | **NO**: fuera de la ventana de 6 semanas, y `next-dev-loop` ya llama a `/_next/mcp` directamente |
| **vercel-react-best-practices** (`vercel-labs/agent-skills`) | skill | Más de 40 reglas de rendimiento de React/Next (cascadas de peticiones, tamaño del bundle, RSC) | repo 2026-10-27; esta skill 2026-04-14 (contenido estable) | Blog de Vercel, 2026-01-14 ([vercel.com/blog](https://vercel.com/blog/introducing-react-best-practices)); listada en las docs oficiales de Vercel ([vercel.com/docs/agent-resources/skills](https://vercel.com/docs/agent-resources/skills)) | Medio-alto al cargar (AGENTS.md de 3.810 líneas; el SKILL.md carga reglas por archivo) | Bajo | **ADOPTAR** (proyectos React) |
| **web-design-guidelines** (misma repo) | skill | Auditoría de más de 100 reglas de UI, a11y y UX; descarga las reglas de `vercel-labs/web-interface-guidelines` | fuente de las reglas 2026-10-05 | Docs de Vercel; recomendado en las guías de [ruoqijin (jun-2026)](https://ruoqijin.com/blog/frontend-design-skills-ai-agents) y [duply (ago-2026)](https://duply.ai/blog/claude-code-design-skills) | Bajo-medio | Bajo (descarga reglas en tiempo de ejecución) | **ADOPTAR** como puerta de revisión |
| **shadcn MCP / skills** (`shadcn-ui/ui`) | MCP + skills | Busca e instala componentes de registros (incluidos privados) | commit 2026-11-06; shadcn@4.23.0 2026-10-27 | Docs oficiales: `shadcn mcp init --client claude` ([ui.shadcn.com/docs/mcp](https://ui.shadcn.com/docs/mcp)) | Bajo-medio | Bajo; un registro de terceros es código no confiable | **OPCIONAL**: solo en repos que ya usan shadcn, a nivel de proyecto |
| **frontend-design** (Anthropic, `claude-plugins-official`) | plugin/skill | Dirección estética antes de escribir código; prohíbe los defaults genéricos | 2026-10-26 | Lo citan como base en casi todas las comparativas: [subframe](https://www.subframe.com/tips/best-claude-code-skills-for-ui-design), [composio](https://composio.dev/content/top-design-skills), [dev.to/skillgild, 2026-10-06](https://dev.to/skillgild/claude-code-frontend-design-skills-taste-skill-and-logo-design-295b) | ~2,3k al cargar (9,4 KB) | Bajo | **CONSERVAR** |
| **impeccable** (`pbakaus/impeccable`) | plugin/skill + CLI `detect` | 24 comandos (shape, critique, audit, polish…), modos de marca y de producto, detector determinista apto para CI | commit 2026-11-08; skill-v4.8.1 2026-11-08 | En la prueba de Subframe (oct-2026) fue la única skill que cambió el diseño; recomendada en [claude-codex.fr (jun-2026)](https://claude-codex.fr/en/content/stack-design-claude-code) y [Medium/Xermio (2026-10-31)](https://medium.com/@xermiolabs/7-claude-skills-for-ui-design-i-use-every-week-ef0ba5b292c4) | ~3k al cargar (12 KB) más referencias bajo demanda | Bajo (Apache-2.0) | **CONSERVAR** como skill de diseño principal (actualizar: tiene instalada la 4.4.0) |
| ui-ux-pro-max (`nextlevelbuilder/…`) | plugin/skill + script Python | Base de datos de estilos, paletas y tipografías | commit 2026-11-07; último release v2.15.0 2026-08-13 | Comparativas: "da la respuesta segura, no una distinta" ([Xermio](https://medium.com/@xermiolabs/7-claude-skills-for-ui-design-i-use-every-week-ef0ba5b292c4)); en la prueba de skillgild dio "el look SaaS más convencional" | **~11k al cargar** (44,7 KB) más 3 skills extra (banner, design, ui-styling) | Bajo/medio (ejecuta un script local) | **QUITAR del kit por defecto**: se solapa con impeccable |
| antislop (`miqdadbadjuber/anti-slop`) | 6 skills | Filtro contra UI, copy y comentarios genéricos | commit 2026-11-05; v3.2.26 2026-11-05 | Activo, pero no encontré recomendación de expertos con nombre; casi todo son listados de directorios. Hay varios **forks clonados** (Mardak0, adicahyadir, muris11, nota-america) | **Muy alto**: el núcleo pesa 51,7 KB (~13k), su descripción dice "Load always" y su instalador añade un bloque al CLAUDE.md. Las 6 skills suman ~140 KB | Medio: suplantación por forks y edición del CLAUDE.md | **QUITAR del kit**. Si acaso, conservar `antislop-copywriting` en un proyecto de landing |
| playwright-skill (`lackeyjb/playwright-skill`) | skill | Scripts de Playwright en /tmp | último commit 2026-08-14 (el push de 2026-11-01 no está en main) | — | ~3,5k al cargar | Ejecuta JS arbitrario desde /tmp | **QUITAR**: inactivo; lo reemplaza Playwright CLI |
| webapp-testing (Anthropic, `anthropics/skills`) | skill + `with_server.py` | Pruebas con Playwright **en Python** que levantan los servidores | skill 2026-04-20 (repo activo 2026-11-06) | Skill oficial; sigue en listas de oct-2026 ([Xermio](https://medium.com/@xermiolabs/7-claude-skills-for-ui-design-i-use-every-week-ef0ba5b292c4)) | ~1k (3,9 KB) | Bajo | **CONSERVAR (opcional)** para equipos Python con pytest-playwright |
| web-quality-skills (`addyosmani/web-quality-skills`, en caché) | skills | Core Web Vitals, SEO y a11y | último commit 2026-08-24 | — | ~3k por skill | Bajo | **QUITAR**: inactivo; para CWV usar Chrome DevTools y Lighthouse 13.6 (2026-10-27) |
| **axe Accessibility plugin** (`dequelabs/axe-accessibility`) | plugin + MCP | Bucle de analizar → remediar → verificar con axe | push 2026-10-06 | Docs de Deque ([docs.deque.com](https://docs.deque.com/devtools-server/4.0.0/en/claude-code-plugin/)) | Bajo | Requiere licencia de pago de Axe DevTools; consume créditos de IA; `mcp-audit` edita el código fuente | **OPCIONAL**: solo si la empresa ya paga Axe. Alternativa gratuita: `@axe-core/playwright` (axe-core v4.14.0, 2026-10-05) en la suite de pruebas |

### 1.2 Documentación de librerías al día

| Nombre | Tipo | Qué hace | Último commit / release | Evidencia | Costo de contexto | Riesgo | Veredicto |
|---|---|---|---|---|---|---|---|
| **Context7** (`upstash/context7`) | MCP **o** CLI + skill (`ctx7`) | Fragmentos de docs por versión | commit 2026-11-06; mcpb-v4.5.1 2026-11-06 | Plugin oficial de Claude con ~418k instalaciones ([claude.com/plugins](https://claude.com/plugins/chrome-devtools-mcp)). `ctx7 setup --cli` instala la skill `find-docs` sin MCP ([context7.com/docs/clients/cli](https://context7.com/docs/clients/cli)) | ~3k por consulta ([comparativa de Ref](https://docs.ref.tools/context/comparison/context7)); en modo CLI no paga esquemas | **CVE-2026-75130** (inyección de prompt mediante "Custom AI Instructions", ≤2.1.2, CVSS 9.0; [cve.org](https://www.cve.org/CVERecord?id=2026-75130)), corregido en versiones nuevas. Las docs son contribución de la comunidad. Plan gratuito: 1.000 llamadas al mes | **CONSERVAR**, pasando al modo **CLI + skill a nivel de proyecto** (`ctx7 setup --cli --project`) y fijando la versión |
| Ref (`ref-tools/ref-tools-mcp`) | MCP (remoto) | Búsqueda y lectura iterativa de docs, PDFs y repos privados | commit 2026-11-06 | Sale como alternativa en las comparativas de [repowise (oct-2026)](https://repowise.dev/blog/mcp/context7-alternatives-give-agents-your-own-docs) y [agentic-ai-wiki (sep-2026)](https://agentic-ai-wiki.vercel.app/blogs/context7-vs-deepwiki-vs-gitmcp-vs-ref) | 500–5k por consulta | Requiere API key; de pago (USD 9/mes por 1.000 consultas) | **NO por ahora**: solo si la empresa necesita indexar docs privadas |
| DeepWiki MCP (Cognition, `mcp.deepwiki.com/mcp`) | MCP remoto, sin auth | Wiki generada y preguntas sobre repos **públicos** | servicio vivo; docs de Devin vigentes | [docs.devin.ai/work-with-devin/deepwiki-mcp](https://docs.devin.ai/es/work-with-devin/deepwiki-mcp) | Bajo (3 herramientas) | La prosa la escribe un modelo y puede equivocarse; **nunca le pases código privado**. Para privados existe Devin MCP (de pago) | **OPCIONAL** para entender dependencias open source |
| GitMCP (`idosal/git-mcp`) | MCP | llms.txt/README de cualquier repo | último commit 2026-05-08 | — | Bajo | — | **NO** (inactivo) |
| **llms.txt / docs en Markdown del proveedor** | convención | Linear, Context7, Ref, Reflex y Next.js publican `llms.txt` o `.md` | — | Se ve en los propios sitios (p. ej. [linear.app/docs/mcp](https://linear.app/docs/mcp)) | Lo que se lea con WebFetch | Contenido web no confiable | **USAR** sin instalar nada (WebFetch) |

### 1.3 Productividad (commits, PRs, changelog, tareas, avisos, paralelo, CLAUDE.md)

| Nombre | Tipo | Qué hace | Último commit / release | Evidencia | Costo de contexto | Riesgo | Veredicto |
|---|---|---|---|---|---|---|---|
| **commit-commands** (Anthropic) | plugin (3 comandos) | `/commit` imita el estilo de commits del repo; también `/commit-push-pr` y `/clean_gone` | 2026-10-26 | Es el ejemplo de las docs oficiales de plugins ([code.claude.com/docs/en/plugins/install](https://code.claude.com/docs/en/plugins/install)) | Muy bajo (solo se carga al invocarlo) | Añade atribución de Claude Code al commit: **va contra tu regla de no poner co-autor** → desactivarla con el ajuste `attribution` de settings (antes `includeCoAuthoredBy`) | **ADOPTAR**, reemplazando tus `commit` y `create-pr` |
| commitlint (`conventional-changelog/commitlint`) o **commitizen** (Python) | hook de git / CI | Valida Conventional Commits | commitlint v21.2.4 2026-10-18; commitizen v4.19.3 2026-10-24 | Herramientas estándar | 0 (corren fuera del modelo) | Bajo | **ADOPTAR uno** como `commit-msg`/pre-commit: commitizen encaja mejor en Python |
| **release-please** (Google) / **git-cliff** | CI / CLI | Changelog y versión desde los commits | release-please commit 2026-11-03; git-cliff commit 2026-11-02, v2.14.2 2026-09-18 | Estándar del sector | 0 | Bajo | **ADOPTAR** el que use el equipo; si no hay ninguno, release-please con GitHub Actions |
| python-semantic-release | CI | Lo mismo, nativo de Python | commit en main 2026-09-22; v10.7.0 2026-09-22 | — | 0 | Bajo | Al límite de la ventana: preferir release-please o commitizen |
| **Linear MCP** (oficial, `mcp.linear.app/mcp`) | MCP remoto, OAuth | Issues, proyectos, comentarios; permite pedir alcance de **solo lectura** | servicio vivo (docs actuales) | [linear.app/docs/mcp](https://linear.app/docs/mcp). Comparativa de [Radial, 2026-11-02](https://www.radial.build/blog/jira-vs-linear-for-agents): 60 herramientas, 12/16 frente a 8/16 de Jira | **Alto** (60 herramientas) | Escritura en el tracker → empezar con alcance `read` | **ADOPTAR solo si la empresa usa Linear**, a nivel de proyecto |
| **Atlassian Rovo MCP** (oficial, `mcp.atlassian.com/v2/mcp`) | MCP remoto + plugin | Jira, Confluence, Bitbucket | commit 2026-11-07 | [github.com/atlassian/atlassian-mcp-server](https://github.com/atlassian/atlassian-mcp-server). GA con ~25% menos tokens ([blog de Atlassian, 2026-10-06](https://www.atlassian.com/blog/company-news/team26-europe-atlassian-mcp)) | Medio | Las llamadas "enriquecidas" **consumen créditos de Rovo** ([atlassian.com/licensing/rovo](https://www.atlassian.com/licensing/rovo)). Hay CLI oficial (`acli`) | **ADOPTAR solo si la empresa usa Jira**; valorar `acli` antes que el MCP |
| GitHub: `gh` CLI frente a `github-mcp-server` | CLI / MCP | PRs, issues, Actions | github-mcp-server v2.1.0 2026-11-03 | (lo cubre otro investigador) | `gh` ≈ 0 en reposo | — | Preferir `gh` |
| **Worktrees nativos** (`claude -w <nombre>`, `isolation: worktree`) | función nativa | Sesiones paralelas aisladas en `.claude/worktrees/`, que se limpian solas | Claude Code v2.1.319 2026-11-06 | [code.claude.com/docs/en/worktrees](https://code.claude.com/docs/en/worktrees) y [Ben Rogers, 2026-10-20](https://www.benrogers.dev/blog/git-worktrees-claude-code) | 0 | Los `.env` no se copian (usar `.worktreeinclude`) | **ADOPTAR**; no hace falta herramienta externa |
| workmux (`raine/workmux`) | CLI (tmux) | Orquesta worktrees con tmux | v0.1.280 2026-11-07 | Activo; sin reseñas de expertos | 0 | Bajo | Opcional; claude-squad (2026-08-20) y crystal (2026-02) quedan **descartados** por inactivos |
| **Hook `Notification`/`Stop` nativo** | hook | Aviso del sistema cuando Claude espera o termina (`osascript` en macOS) | docs actuales | [code.claude.com/docs/en/hooks-guide](https://code.claude.com/docs/en/hooks-guide) | 0 | Ninguno | **ADOPTAR** dentro del plugin del kit (hooks/hooks.json). `777genius/agent-notifications` (v1.51.2, 2026-11-05) solo si se quieren avisos a Telegram/Slack |
| **claude-md-management** (Anthropic) | plugin | Skill `claude-md-improver` (audita el CLAUDE.md contra el código) y `/revise-claude-md` (guarda lo aprendido en la sesión) | 2026-10-26 (repo) | README oficial en `claude-plugins-official/plugins/claude-md-management` | Bajo | Bajo; revisar cada diff | **ADOPTAR** como plantilla viva de CLAUDE.md para equipos |
| Code intelligence (`pyright-lsp`, `typescript-lsp`, Anthropic) | plugin LSP | Ir a la definición y buscar referencias de forma precisa | repo oficial activo | Lo recomiendan las best practices oficiales ([code.claude.com/docs/en/best-practices](https://code.claude.com/docs/en/best-practices)) | Bajo | Bajo | **ADOPTAR** `pyright-lsp` (+ `typescript-lsp` si hay frontend) |

### 1.4 Python full stack y dashboards internos

| Nombre | Tipo | Qué hace | Último commit / release | Evidencia | Costo de contexto | Riesgo | Veredicto |
|---|---|---|---|---|---|---|---|
| **Streamlit skills integradas** (`streamlit skills`) | CLI que enlaza skills | Desde la 1.57, Streamlit trae sus skills en el paquete y crea symlinks en `.claude/skills/`; siguen la versión instalada | streamlit 1.67.0 2026-11-05 | [docs.streamlit.io/develop/api-reference/cli/skills](https://docs.streamlit.io/develop/api-reference/cli/skills). El repo `streamlit/agent-skills` está **archivado** y apunta a esto | Bajo | Bajo (oficial) | **ADOPTAR** para dashboards de datos/ML (`streamlit skills`, sin `-g`) |
| FastAPI + Jinja2 + **htmx** | stack | Apps internas renderizadas en el servidor | htmx **v4.0.1 2026-11-01** | — | — | Las skills de htmx de la comunidad son 2.x (`mintarasss/htmx-skill`, último commit 2026-03) o no tienen tracción (`4fuu/build-with-htmx-4-skill`, 0★) | **Stack recomendado; sin skill**: usar Context7 o los llms.txt oficiales y fijar htmx 2.x o 4.x en el CLAUDE.md |
| FastHTML (`AnswerDotAI/fasthtml`) | framework | Python + htmx | 0.14.19 2026-11-05 | Activo | — | Ecosistema pequeño | Opcional |
| Reflex (`reflex-dev/reflex` + `agent-skills`) | framework + skills/MCP | App full stack en Python | reflex 2026-11-06; **agent-skills 2026-06-10** | [reflex.dev/docs/ai/integrations/skills](https://reflex.dev/docs/ai/integrations/skills). Su MCP es **solo para Enterprise** | — | — | **NO**: skills inactivas y MCP de pago |
| NiceGUI (`zauberzeug/nicegui`) | framework | UI en Python | v4.0.0 2026-11-04 | Sin skill oficial | — | Versión mayor recién salida | Opcional, con Context7 |

---

## 2. Entender rápido un codebase nuevo

Kevin acaba de entrar a la empresa, así que esto es lo más útil a corto plazo. El orden va de menor a mayor costo y riesgo.

1. **Lo nativo primero (costo 0).**
   - `/init` para generar el CLAUDE.md y luego curarlo a mano.
   - Plugin `pyright-lsp` (y `typescript-lsp` si hay frontend) para navegar por símbolos.
   - Subagente `Explore` para preguntas amplias.
   - Mientras no lo conozcas bien, trabaja en plan mode y en `claude -w` sobre un worktree aparte.
   - Fuente: [code.claude.com/docs/en/common-workflows](https://code.claude.com/docs/en/common-workflows).
2. **CodeGraph** (`colbymchenry/codegraph`).
   - Estado: MIT, commit 2026-11-01, v1.6.2 2026-10-03, ya en uso.
   - Qué hace: grafo local de símbolos y llamadas; una sola llamada a `codegraph_explore` reemplaza el bucle grep → Read.
   - Evidencia: en el benchmark de repowise (que es competidor y lo reconoce) tiene el mayor recall en cobra y es "la herramienta más llamada" en sus corridas ([repowise, 2026-10-29](https://repowise.dev/blog/comparisons/best-code-graph-mcp-servers)). Todo corre local.
   - **CONSERVAR**, instalándolo por repo con `codegraph init`.
3. **Serena** (`oraios/serena`).
   - Estado: v2.1.0 2026-10-19.
   - Qué hace: herramientas de símbolos basadas en LSP, incluida la edición o el renombrado.
   - Ojo: **desde 2026-09-14 la licencia es GPL-3.0** (SolidLSP sigue en MIT). Para uso interno no hay problema, pero conviene avisar a legal.
   - Se solapa con los plugins LSP más CodeGraph. **Opcional**: solo para refactors grandes en código muy tipado.
4. **Repomix** (`yamadashy/repomix`).
   - Estado: MIT, v1.19.0 2026-11-08.
   - Qué hace: empaqueta el repo (o una carpeta con `--include` y `--compress`) en un solo archivo; trae secretlint.
   - Úsalo para pasarle un **subsistema** a otro modelo o para documentarlo.
   - Ojo: el repo privado de la empresa **no se sube a servicios externos** sin autorización. **Opcional, bajo demanda** (`npx repomix`, sin MCP).
5. **DeepWiki MCP**: solo para las **dependencias open source** del repo (repos públicos). **Descartados** para el código de la empresa:
   - gitingest: último commit 2025-08.
   - GitNexus: licencia **PolyForm Noncommercial**, no se puede usar en una empresa.
   - repowise: AGPL y servicio alojado.
6. **Git como fuente de verdad**, sin herramientas extra.
   - `git log --since=90.days --name-only` para ver qué se toca más.
   - `git shortlog -sn` para saber quién mantiene qué.
   - `gh pr list --state merged -L 30` para entender cómo trabaja el equipo.

Plan para la primera semana, a partir de la metodología de [theroadtoenterprise, 2026-05](https://theroadtoenterprise.com/blog/onboarding-to-new-codebase-with-ai-tools):
- **Día 1**: `/init`, `codegraph init` y pyright-lsp. Pedir "traza el flujo de una petición de la API a la BD".
- **Días 2–3**: un flujo por sesión; las notas propias van a CLAUDE.md con `/revise-claude-md`.
- **Días 4–5**: primer PR pequeño con `/commit` y `gh`; el estilo de los commits sale del `git log` del repo.

---

## 3. Lo ya instalado: qué conservar y qué quitar

| Instalado | Decisión | Por qué |
|---|---|---|
| frontend-design (plugin oficial) | **Conservar** | Base oficial y liviana; actualizado el 2026-10-26 |
| impeccable (4.4.0) | **Conservar y actualizar a 4.8.1** | Lo más recomendado y activo hoy; tiene un detector apto para CI |
| ui-ux-pro-max (2.5.0) | **Quitar** (dejar opcional) | ~11k tokens al cargar; se solapa con impeccable; tiende a resultados convencionales |
| antislop (6 skills, v3.2.14) | **Quitar** | ~140 KB de reglas, se marca a sí mismo como "Load always" y modifica el CLAUDE.md; se solapa con impeccable; hay forks que lo suplantan |
| playwright-skill (lackeyjb) | **Quitar** | Inactivo desde 2026-08-14; reemplazo: Playwright CLI con sus skills oficiales |
| webapp-testing (Anthropic) | **Conservar (opcional)** | Python + Playwright; útil si las pruebas e2e del equipo son en Python |
| commit (local) | **Quitar** | Origen sin rastrear (copia de feb-2026); usa emojis y `model: haiku`, que pueden chocar con la convención del equipo |
| create-pr (local) | **Quitar** | Tiene un bug: llama a `Skill(git:commit)`, que no existe en tu instalación, y obliga a escribir en inglés. Reemplazo: `commit-commands` oficial con la atribución desactivada |
| Context7 (MCP) | **Conservar, en modo CLI + skill** | Menos contexto; fijar una versión posterior al CVE-2026-75130 |
| web-quality-skills (Addy, en caché) | **Quitar** | Inactivo desde 2026-08-24 |
| frontend-mobile-development@claude-code-workflows (global desde 2025-10) | **Quitar** | Copia vieja a nivel de usuario; se solapa con lo anterior |
| CodeGraph | **Conservar** | Ver la sección 2 |

**Núcleo frontend propuesto para el kit** (todo a nivel de proyecto, activable por repo):
- frontend-design
- impeccable
- web-design-guidelines
- vercel-react-best-practices (solo en repos React)
- Playwright CLI con sus skills
- Chrome DevTools en modo CLI/slim, solo al medir rendimiento

**Núcleo de productividad:**
- commit-commands, con la atribución desactivada
- commitizen o commitlint como hook
- release-please
- claude-md-management
- pyright-lsp
- hook de notificación nativo
- `claude -w`
- Linear MCP o Rovo MCP según lo que use la empresa, empezando con solo lectura

---

## Fuentes

- Playwright CLI para agentes: https://playwright.dev/docs/getting-started-cli
- Playwright MCP (tabla de costos): https://playwright.dev/mcp/introduction
- Better Stack, CLI vs MCP: https://betterstack.com/community/guides/ai/playwright-cli-vs-mcp-browser
- Mediciones de tokens: https://lite.ego.app/article/playwright-mcp-vs-cli · http://webcrawlerapi.com/blog/playwright-cli · https://casely.digital/blog/playwright-cli-vs-mcp · https://www.webfuse.com/blog/playwright-mcp-vs-playwright-cli
- Chrome DevTools para agentes: https://developer.chrome.com/docs/devtools/agents/get-started · https://developer.chrome.com/docs/devtools/agents/get-started/configuration · https://github.com/ChromeDevTools/chrome-devtools-mcp
- Next.js 16.3 (IA): https://nextjs.org/blog/next-16-3-ai-improvements · https://nextjs.org/docs/app/guides/mcp · https://github.com/vercel-labs/next-skills/blob/main/README.md
- Skills de Vercel: https://vercel.com/docs/agent-resources/skills · https://vercel.com/blog/introducing-react-best-practices
- shadcn MCP: https://ui.shadcn.com/docs/mcp
- Comparativas de skills de diseño: https://www.subframe.com/tips/best-claude-code-skills-for-ui-design · https://claude-codex.fr/en/content/stack-design-claude-code · https://dev.to/skillgild/claude-code-frontend-design-skills-taste-skill-and-logo-design-295b · https://medium.com/@xermiolabs/7-claude-skills-for-ui-design-i-use-every-week-ef0ba5b292c4 · https://composio.dev/content/top-design-skills · https://duply.ai/blog/claude-code-design-skills · https://ruoqijin.com/blog/frontend-design-skills-ai-agents
- antislop (repo de origen): https://github.com/miqdadbadjuber/anti-slop
- Deque axe: https://docs.deque.com/devtools-server/4.0.0/en/claude-code-plugin/ · https://docs.deque.com/devtools-server/4.0.0/en/axe-mcp-server/
- Context7: https://context7.com/docs/clients/cli · https://context7.com/docs/plans-pricing · https://www.cve.org/CVERecord?id=2026-75130
- Ref vs Context7: https://docs.ref.tools/context/comparison/context7
- Alternativas a Context7: https://repowise.dev/blog/mcp/context7-alternatives-give-agents-your-own-docs · https://agentic-ai-wiki.vercel.app/blogs/context7-vs-deepwiki-vs-gitmcp-vs-ref
- DeepWiki/Devin MCP: https://docs.devin.ai/es/work-with-devin/deepwiki-mcp · https://docs.devin.ai/work-with-devin/devin-mcp
- Linear MCP: https://linear.app/docs/mcp · Comparativa de Radial: https://www.radial.build/blog/jira-vs-linear-for-agents
- Atlassian: https://github.com/atlassian/atlassian-mcp-server · https://www.atlassian.com/blog/company-news/team26-europe-atlassian-mcp · https://www.atlassian.com/licensing/rovo
- Claude Code (worktrees, hooks, plugins, best practices): https://code.claude.com/docs/en/worktrees · https://code.claude.com/docs/en/hooks-guide · https://code.claude.com/docs/en/plugins/install · https://code.claude.com/docs/en/best-practices · https://code.claude.com/docs/en/common-workflows · https://www.benrogers.dev/blog/git-worktrees-claude-code
- Grafos de código: https://repowise.dev/blog/comparisons/best-code-graph-mcp-servers · https://repowise.dev/blog/comparisons/serena-vs-graphify-vs-codegraph-vs-repowise (competidor, lo declara) · https://rywalker.com/research/serena
- Repomix: https://repomix.com/guide/faq
- Onboarding: https://theroadtoenterprise.com/blog/onboarding-to-new-codebase-with-ai-tools
- Streamlit skills: https://docs.streamlit.io/develop/api-reference/cli/skills · https://github.com/streamlit/agent-skills
- Reflex: https://reflex.dev/docs/ai/integrations/skills · https://reflex.dev/docs/ai/features/agent-toolkit
- htmx skills: https://github.com/mintarasss/htmx-skill · https://github.com/4fuu/build-with-htmx-4-skill
- Datos de GitHub (pushed_at, commits, releases, licencias): `gh api repos/OWNER/REPO`, consultados el 2026-11-07.
