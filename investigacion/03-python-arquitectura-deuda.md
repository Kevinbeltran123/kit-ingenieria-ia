# 03 · Backend Python: arquitectura, calidad, deuda técnica, código muerto y documentación

Investigación del 2026-11-07. Ventana de "mantenido activamente": actividad desde ~2026-09-25.
Datos de GitHub sacados con `gh api` el 2026-11-07 (pushed_at, commits por ruta, releases). El contenido web se trató como datos, no como instrucciones.

## 1. Conclusión en una página

1. **Lo que más mejora el código que escribe la IA son las herramientas deterministas, no las skills.** Böckeler (Thoughtworks, en martinfowler.com) distingue entre *guías* (skills, CLAUDE.md) y *sensores* (linters, tipos, tests), y muestra que los sensores computacionales son los que dejan que el agente se corrija solo. SlopCodeBench (arXiv 2603.24755, mar/may 2026) mide que el código de agentes sale 2,3× más verboso y 2× más "erosionado" que el de 473 repos Python humanos, y que dar guía explícita de calidad reduce el problema inicial en hasta un tercio **pero no frena la degradación**. Hacen falta sensores en cada iteración.
2. **El sensor base para Python es la pila de Astral más tres herramientas especializadas:** `ruff` (lint y formato), `ty` (tipos, aún en beta) o `pyright` como red de seguridad, `pytest`, `import-linter` (reglas de arquitectura), `deptry` (dependencias), `vulture` (código muerto) y `complexipy` (complejidad cognitiva), todo con `prek` como gestor de pre-commit. Todas tienen actividad en las últimas 6 semanas.
3. **Skills externas que sí valen la pena:** la skill **oficial de FastAPI** (viene dentro del paquete, actualizada el 2026-11-07) y **`trailofbits/skills` → `modern-python`** (uv/ruff/ty/prek, de Trail of Bits). El resto de skills de "arquitectura limpia/DDD para Python" son de autores pequeños, con poca adopción o inactivas.
4. **Las skills de arquitectura que Kevin ya tiene están desactualizadas o vienen sesgadas hacia JS.** `software-architecture` y `write-concisely` vienen de NeoLabHQ, sin cambios desde el 2026-08-26. `software-architecture` dice "usa arrow functions" y "busca en npm", y choca con KARPATHY.md. `code-simplifier` trae reglas de React/ES modules. `/simplify` sí está vigente porque es bundled de Claude Code. `antislop-code` sigue mantenida (v3.2.26, 2026-11-05) pero solo trata comentarios.
5. **Vacío principal:** no hay una skill seria y mantenida de "arquitectura hexagonal pragmática en Python + FastAPI + AWS". Conviene **crear una propia**, corta, que se apoye en `import-linter` como sensor en vez de en reglas en prosa.

## 2. Tabla de evaluación

Leyenda de veredicto: **ADOPTAR** · **ADOPTAR CON CONDICIONES** · **OPCIONAL** · **REEMPLAZAR** · **DESCARTAR**.

### 2.1 Herramientas deterministas (CLI)

| Nombre | Tipo | Qué hace | Último commit / release | Evidencia | Riesgo | Veredicto |
|---|---|---|---|---|---|---|
| **ruff** (astral-sh/ruff) | CLI | Linter y formateador. Sustituye flake8, black, isort, pyupgrade, pydocstyle, mccabe, eradicate y bandit (en parte) | push 2026-11-08 · rel 0.17.4 (2026-11-05) · ★51k | Recomendado por Trail of Bits (`modern-python`), por la skill oficial de FastAPI ("use uv, Ruff, ty") y por pydevtools (guía para Claude Code). Böckeler lo usó como sensor en su app Python (mayo 2026) | Bajo. Binario Rust, sin red. `--fix` reescribe archivos: usar solo arreglos "safe" | **ADOPTAR** (núcleo) |
| **ty** (astral-sh/ty) | CLI y LSP | Type checker y servidor de lenguaje, 10–100× más rápido que mypy/pyright | push 2026-11-06 · rel 0.0.99 (2026-11-06), casi un release diario | **Sigue en BETA.** El README dice "ty is currently in beta… breaking changes, including changes to diagnostics, may occur between any two versions", con un milestone "Stable" abierto. Novedades recientes: inferencia de tipo de retorno (0.0.89, opt-in), soporte de Django (0.0.92) y baselines de diagnósticos (0.0.93, preview) | Medio. Los diagnósticos cambian entre versiones: fijar la versión exacta | **ADOPTAR CON CONDICIONES**: fijar versión. En repos de la empresa con mypy/pyright existente, no reemplazar todavía |
| **pyright** (microsoft/pyright) | CLI y LSP | Type checker maduro | push 2026-11-07 · rel 1.1.414 (2026-09-09) | Estándar de facto. Anthropic publica `pyright-lsp` en el marketplace oficial | Bajo. Necesita Node (vía `pyright` de PyPI o npm) | **OPCIONAL**: red de seguridad en CI si ty da falsos negativos |
| **mypy** (python/mypy) | CLI | Type checker de referencia | push 2026-11-07 · tag v2.4.1 | Maduro, lento | Bajo | **OPCIONAL**: solo si el repo de la empresa ya lo usa |
| **pyrefly** (meta/pyrefly) | CLI y LSP | Type checker de Meta en Rust | push 2026-11-08 · rel 1.4.1 (2026-11-05) | Ya es 1.x (estable). pydevtools lo usa en su ejemplo de hook Stop | Bajo | **OPCIONAL**: alternativa estable a ty si la beta molesta |
| **import-linter** (seddonym/import-linter) | CLI | Hace cumplir la arquitectura con contratos de capas, prohibiciones e independencia entre módulos | push 2026-11-06 · **2.16 (2026-11-06)** | Release notes recientes (2.14 añadió `broken_contract_guidance`, útil para que el agente entienda cómo arreglar). Es el equivalente Python de ArchUnit, que Böckeler cita como "structural tests" en hooks | Bajo. Solo análisis estático | **ADOPTAR**: es el sensor de arquitectura hexagonal |
| **tach** (tach-org/tach) | CLI | Límites de módulos e interfaces, en Rust | push 2026-10-29 · v0.35.3 (2026-10-06) | Activo. Más opinado que import-linter | Bajo | **OPCIONAL**: solo en monorepos grandes |
| **deptry** (osprey-oss/deptry) | CLI | Dependencias declaradas y no usadas, usadas sin declarar, transitivas | push 2026-11-07 · rel 0.25.1 (2026-03-18) | Activo en commits. Lo citan repowise (nov 2026) y skylos.dev como la herramienta para dependencias | Bajo | **ADOPTAR** |
| **vulture** (jendrikseipp/vulture) | CLI | Código muerto (funciones, clases y variables sin uso) con nivel de confianza | push 2026-10-12 · v2.16 (2026-03-25) | "Standard Python dead code finder" según repowise (2026-11-01). Falsos positivos en rutas FastAPI/fixtures, que se manejan con whitelist | Bajo | **ADOPTAR** como chequeo semanal o de PR, no por edición |
| **skylos** (duriantaco/skylos) | CLI, MCP y GitHub Action | Código muerto "framework-aware" (FastAPI, Django, pytest), SAST y secretos | push 2026-11-08 · v5.4.0 (2026-11-02) · ★887 | Muy activo. Ojo: las comparativas favorables a skylos las publica el propio skylos.dev | Medio. Tiene extras con LLM (`skylos[llm]`) que mandan código a APIs externas, y un servidor MCP. Mucha superficie | **OPCIONAL**: probar en un repo antes de adoptarlo. Sin extras LLM |
| **deadcode** (albertas/deadcode) | CLI | Código muerto con `--fix` | push 2026-11-08, sin releases recientes | skylos.dev reporta último release en ago 2024 y que el hook de pre-commit sale con 0 aunque encuentre algo (#35) | Medio. AGPL-3.0 | **DESCARTAR** |
| **complexipy** (rohaquinlop/complexipy) | CLI | Complejidad *cognitiva* (Sonar) en Rust | push 2026-11-08 · 8.3.0 (2026-10-27) · hook pre-commit v8.3.0 | Activo y rápido. La complejidad cognitiva se alinea mejor con "legible para humanos" que la ciclomática | Bajo | **ADOPTAR** (umbral 15) |
| **radon / xenon** (rubik/*) | CLI | Ciclomática e índice de mantenibilidad | **push 2024-10-20 / 2024-10-21** | Sin actividad en 2 años | Bajo, pero abandonado | **DESCARTAR**: usar `ruff C901` + `PLR09xx` + complexipy |
| **pyupgrade** (asottile/pyupgrade) | CLI | Moderniza sintaxis | push 2026-11-04 | Activo, pero ruff ya implementa sus reglas (`UP`) | Bajo | **DESCARTAR** como herramienta aparte (ruff `UP`) |
| **interrogate** (econchick/interrogate) | CLI | Cobertura de docstrings | último commit real **2024-05-20**, rel 1.7.0 (2024-04) | El pushed_at de 2026 son ramas/bots, no desarrollo | Bajo | **DESCARTAR**: usar ruff `D` (pydocstyle) y, si hace falta, **pydoclint** (0.12.0, 2026-10-28) |
| **pylint** (pylint-dev/pylint) | CLI | Lint profundo, incluye `duplicate-code` (R0801) | push 2026-11-03 · v4.1.3 (2026-10-11) | Activo. Solo interesa por `R0801` | Bajo. Lento | **OPCIONAL**: `pylint --disable=all --enable=R0801` en CI |
| **jscpd** (kucherenko/jscpd) | CLI (Node) | Detección de copy-paste en más de 200 lenguajes | push 2026-11-06 · v5.4.2 (2026-10-20) | Activo. Lo usan agent-sweep y la skill `anti-slop-code` de quegenx | Medio. Paquete npm (Kevin tiene `ignore-scripts=true`) | **OPCIONAL**: reporte en CI, no bloqueante |
| **pre-commit** (pre-commit/pre-commit) | CLI | Gestor de hooks git | push 2026-11-04 · v4.7.0 (2026-10-13) | Estándar | Bajo | Compatible. Ver prek |
| **prek** (j178/prek) | CLI | Reimplementación de pre-commit en Rust, compatible con `.pre-commit-config.yaml`, integra uv | push 2026-11-07 · v0.5.10 (2026-11-04) · ★8,7k | Lo usan **CPython, Apache Airflow y FastAPI** (README). Trail of Bits lo recomienda en `modern-python` | Bajo. Versión 0.x | **ADOPTAR** (con fallback a pre-commit: misma config) |
| **uv** (astral-sh/uv) | CLI | Paquetes, entornos, lockfile y Python | push 2026-11-08 · 0.13.7 (2026-11-03) | Willison: "by far the most convincing solution" (2026-03-19). Hynek: serie "uv-based Project Layout" | Bajo. Nota: **Astral pertenece a OpenAI desde mar-2026**; las herramientas siguen MIT/Apache y activas (Talk Python #552, jun-2026) | **ADOPTAR** |
| **py-spy** (benfred/py-spy) | CLI | Profiler por muestreo, se engancha a procesos vivos | push 2026-11-06 · v0.4.3 (2026-11-02) | Activo, estándar | Medio. Requiere `sudo`/ptrace para adjuntarse a procesos: no dar permiso automático al agente | **ADOPTAR** bajo demanda (skill de rendimiento) |
| **scalene** (plasma-umass/scalene) | CLI | Profiler de CPU, memoria y GPU línea a línea, con sugerencias de IA opcionales | push 2026-11-01 · v2.4.0 (2026-10-23) | Activo | Medio. Las "AI optimizations" envían código a un proveedor si se configuran | **OPCIONAL** (sin la función IA) |
| **Zensical** (zensical/zensical) | CLI | Sucesor de Material for MkDocs: lee `mkdocs.yml`, soporta mkdocstrings | push 2026-11-06 · **v0.1.0 (2026-11-05)** | Material for MkDocs está en mantenimiento, con EOL extendido al **2027-05-05** (zensical.org). mkdocstrings en modo mantenimiento hasta al menos fin de 2026 (issue mkdocstrings/python#323) | Bajo. Es 0.x y tiene parte comercial (Studio), pero el núcleo es MIT | **ADOPTAR** para docs nuevas. Material solo en repos existentes |
| **MADR** (adr/madr) | Plantilla | Plantilla Markdown de ADR | 4.0.0 (sin cambios recientes; es un formato estable) | Formato de referencia, usado en repos de 2026 (p. ej. agoranomos ADR-0009, 2026-10) | Ninguno | **ADOPTAR** como plantilla dentro de una skill propia |
| **adr-tools / log4brains** | CLI | Gestión de ADRs | push 2024-04 / 2024-12 | Inactivos | — | **DESCARTAR** |

### 2.2 Skills / plugins para Claude Code (y Agent Skills)

| Nombre | Tipo | Qué hace | Último commit / release | Evidencia | Riesgo | Veredicto |
|---|---|---|---|---|---|---|
| **FastAPI skill oficial** (`fastapi/.agents/skills/fastapi`) | Skill (viene dentro del paquete `fastapi`) | Buenas prácticas de la versión instalada: `Annotated` + `Depends`, return types vs `response_model`, SSE, parameter models, routers, tooling uv/ruff/ty | **commits 2026-11-07** (3 ese día) · FastAPI 0.162.2 | Oficial (tiangolo). Docs "Develop with AI" (fastapi.tiangolo.com/ai-development). Se versiona con la librería, así que no queda desactualizada | Bajo. Solo Markdown. **Riesgo del instalador `uvx library-skills`**: copia SKILL.md de *cualquier* paquete instalado. Una dependencia comprometida podría inyectar instrucciones. Elegir solo la skill de FastAPI y revisar el diff | **ADOPTAR** (en repos FastAPI) |
| **library-skills** (tiangolo/library-skills) | CLI | Escanea el venv e instala las skills que traen las librerías en `.claude/skills` | push 2026-11-01 · rel 0.0.19 (2026-06-21) | Recomendado por la doc oficial de FastAPI | Medio (ver fila anterior) | **ADOPTAR CON CONDICIONES**: revisión manual de lo copiado |
| **trailofbits/skills → `modern-python`** | Plugin (skills + hook) | uv, ruff, ty, pytest y prek. Seguridad con detect-secrets, actionlint, zizmor, pip-audit y Dependabot. src layout, PEP 723 | repo push 2026-11-06. Último cambio del plugin **2026-09-16** (al borde de la ventana) · ★8k | Trail of Bits, firma de seguridad reconocida. Basado en su `cookiecutter-python` | Medio. **Hook `SessionStart` que antepone shims en PATH** para `python`, `pip`, `pipx` y `uv pip`, que fallan y sugieren `uv`. Intercepta también subprocesos (ya rompió prek una vez, issue #207, corregido) | **ADOPTAR CON CONDICIONES**: copiar sus skills al kit, decidir aparte si se quiere el hook de shims |
| **trailofbits/skills → `code-improver`** | Plugin (workflow) | Bucle revisar→arreglar con un revisor intercambiable hasta tener 0 hallazgos críticos | 2026-10-27 | Trail of Bits | Medio. Bucle autónomo que edita código y gasta tokens | **OPCIONAL** (para limpieza de deuda en ramas) |
| **astral-sh/claude-code-plugins** (`/astral:uv`, `:ruff`, `:ty`) | Plugin (3 skills) | Uso correcto de uv, ruff y ty | **último commit 2026-02-27** | Oficial de Astral. Recomendado por pydevtools | Bajo (solo skills) | **OPCIONAL / no cumple la ventana**: el contenido de ruff/ty cambia rápido y estas skills no se actualizan. Preferir `modern-python` + skill propia |
| **wshobson/agents → `python-development`** | Plugin (16 skills: async, design patterns, type safety, performance, testing, uv…) | Catálogo grande de patrones Python | **2026-10-30** · ★42k | Muy popular, corrigió 22 ejemplos rotos (#797, oct-2026), lo que también indica que la calidad del contenido varía | Bajo-medio. Mucho texto: riesgo de inflar el contexto y de reglas genéricas | **OPCIONAL**: tomar como fuente de ideas, no instalar entero |
| **wshobson/agents → `code-refactoring`, `code-documentation`, `c4-architecture`** | Plugins | Refactor, documentación, diagramas C4 | 2026-10-30 | Mismo autor | Igual | **OPCIONAL** (C4 puede servir para diagramas) |
| **iktakahiro/python-fastapi-ddd-skill** | Plugin (4 skills: DDD/Onion + FastAPI + testing + tooling) | Arquitectura en capas con entidades, VOs, repos y casos de uso | push 2026-10-24 · ★5 | Basado en su repo de referencia `dddpy`. Sin recomendaciones de expertos | Bajo | **OPCIONAL**: buena *referencia* para la skill propia, adopción mínima. Usa mypy, no ty |
| **MKToronto/python-clean-architecture** | Plugin | Clean Architecture FastAPI, comandos review/scaffold | push 2026-06-19 | Inactivo | — | **DESCARTAR** |
| **dskst/ddd-skills**, **helmedeiros/clean-code-skills**, **manikosto/claude-code-python-stack**, **cjhowe-us/python-plugin**, **kmshihab7878/claude-code-setup** | Plugins | DDD, clean code, stacks Python con hooks | push entre 2026-02 y 2026-06 | Inactivos, ≤54★ | — | **DESCARTAR** |
| **full-stack-skills/ddd-skills** | Skills (16; hexagonal, COLA, CQRS) | DDD genérico (sesgo Java/COLA) | creado 2026-06 | Agregador, sin aval experto | Bajo | **DESCARTAR** |
| **fastapi-practices/skills** | Skill | Guía para el proyecto "FastAPI Best Architecture" (fba) | push 2026-11-05 · ★10 | Solo sirve si se usa ese boilerplate concreto | Bajo | **DESCARTAR** (salvo que la empresa use fba) |

### 2.3 Skills que Kevin ya tiene instaladas

| Nombre | Origen verificado | Último cambio | Diagnóstico | Veredicto |
|---|---|---|---|---|
| **software-architecture** | NeoLabHQ/context-engineering-kit, plugin `ddd` (copiado también por sickn33, enuno y aitmpl) | repo **2026-08-26** (v3.10.0). Plugin `ddd` 2026-06-11 | Fuera de la ventana. **Sesgada hacia JS:** "Use arrow functions", "Check npm", "use cockatiel". Reglas arbitrarias (función de más de 80 líneas → dividir, archivo de más de 200 → dividir). "Avoid duplication through reusable functions" contradice KARPATHY.md ("three similar lines beat a premature abstraction"). Su description se activa "in any case that relates to software development" y carga contexto siempre | **REEMPLAZAR** por skill propia `arquitectura-python` |
| **simplify** | Bundled de Claude Code (`/simplify [target]`: reuso, simplificación, eficiencia y "altitude"; Anthropic) | Se actualiza con Claude Code | Vigente y oficial. Detalle: si un *proyecto* define su propia skill `simplify` o `verify`, Claude Code la ejecuta antes de cada commit (docs de skills). La bundled no cuenta para eso | **ADOPTAR** (ya está). Valorar una skill de proyecto `verify` que corra los sensores |
| **code-simplifier** | anthropics/claude-plugins-official, plugin `code-simplifier` (agente opus) | **2026-02-20** (creado 2026-01-09) | Oficial pero quieto. Su prompt trae estándares de **JS/React** ("ES modules", "prefer function keyword", "React Props types"). Lo cubre `/simplify` bundled | **REEMPLAZAR** por `/simplify`, o reescribir el agente con estándares Python en el kit |
| **antislop-code** | miqdadbadjuber/anti-slop (★8,6k). Hay forks/clones (adicahyadir, muris11): **instalar solo del original** | repo **2026-11-05** (v3.2.26). Skill `antislop-code` 2026-09-11 | Mantenida. Solo cubre **comentarios** ("never touch the code"). Útil pero estrecha. El instalador `npx antislop-ai` escribe un "pointer" en CLAUDE.md/AGENTS.md | **ADOPTAR CON CONDICIONES**: vendorizar la carpeta de la skill fijada a un tag, sin usar el instalador npx |
| **write-concisely** | NeoLabHQ/context-engineering-kit (plugin `docs`), derivada de **obra/the-elements-of-style** (Jesse Vincent) | NeoLab 2026-08-26 · obra **2026-08-12** | Fuera de la ventana. Strunk (1918) en inglés: no sirve para documentación en español | **REEMPLAZAR** por una skill propia de documentación (ES/EN) que incluya reglas de concisión. La de obra puede quedar como referencia |

## 3. Qué dicen los expertos (con fecha)

- **Birgitta Böckeler (Thoughtworks), en martinfowler.com.** "Harness engineering for coding agent users" (2026-04-02): guías vs sensores, computacional vs inferencial, "keep quality left" (linters y tests rápidos antes del commit, detección continua de deriva como `/find-dead-code`). "Maintainability sensors for coding agents" (2026-05-27): usó sensores en una app **Python** ("los tools Rust 'blazingly fast' no dieron ningún problema"). Como lección, señala que hay que asegurarse de que **el agente llame a los sensores antes de terminar**, lo que en Claude Code se resuelve con un hook Stop. "Are Harnesses Worth the Cost?" (2026-10-13): con harness, un modelo barato pasó 10/10 frente a 3/10 sin él.
  - https://martinfowler.com/articles/harness-engineering.html
  - https://martinfowler.com/articles/sensors-for-coding-agents.html
  - https://martinfowler.com/articles/are-harnesses-worth-the-cost.html
- **Simon Willison.** *Agentic Engineering Patterns* (2026): "First run the tests", "Use red/green TDD", "Never assume that code generated by an LLM works until that code has been executed", "Don't file pull requests with code you haven't reviewed yourself", "AI should help us produce better code". En la Pragmatic Summit (2026-03-14): "Having poor quality code from an agent is a choice that you make". Los agentes copian los patrones existentes del repo, así que importa tener una base limpia y plantillas. Sobre la compra de Astral (2026-03-19): darle al agente lint y tipos rápidos mejora la calidad del código generado.
  - https://simonwillison.net/guides/agentic-engineering-patterns/
  - https://simonwillison.net/2026/mar/14/pragmatic-summit/
  - https://simonwillison.net/2026/Jan/26/tests/
  - https://simonwillison.net/2026/mar/19/openai-acquiring-astral/
- **Astral / Charlie Marsh** (The Test Set, resumido por pydevtools el 2026-02-24): en Astral usan más reglas de lint y mejores CLAUDE.md para que los agentes no repitan errores. uv es "la killer app" para que los agentes produzcan scripts ejecutables. https://pydevtools.com/blog/charlie-marsh-test-set-interview/
- **Hynek Schlawack** (Mastodon, 2025-06-18): la calidad del código de LLM depende del rigor de diseño del código de entrada, y quien no tiene criterio de diseño "no notará que la arquitectura es mala". Charla PyCon US 2025 "Design Pressure": la presión de diseño (testabilidad, acoplamiento) como señal. Su layout uv para apps de producción (2025) y su guía de Docker con uv (actualizada el 2026-08-06) sirven de referencia de estructura. No encontré un texto suyo de 2026 específico sobre agentes.
  - https://mastodon.social/@hynek/114703485524249737
  - https://hynek.me/articles/docker-uv/
- **pydevtools (Tim Hopper)**, guías prácticas para Claude Code + Python: hook PostToolUse con ruff, hook Stop con type checker acotado por `stop_hook_active` y pre-commit como red final. https://pydevtools.com/handbook/how-to/how-to-write-claude-code-hooks-for-python-projects
- **Anthropic** (docs de Claude Code): los hooks "are deterministic and guarantee the action happens", a diferencia de CLAUDE.md, que es orientativo. Se recomienda verificar con un hook Stop y pedir evidencia de que las pruebas corrieron. https://code.claude.com/docs/en/best-practices · https://code.claude.com/docs/en/hooks
- **Evidencia empírica**: SlopCodeBench, https://arxiv.org/abs/2603.24755

## 4. Propuesta de configuración base de calidad (repo Python)

Principios: (a) **lo rápido va por edición** (ruff sobre el archivo tocado), (b) **lo de proyecto va al terminar el turno** (ty, pytest, import-linter, con un solo reintento), (c) **todo se repite en pre-commit y CI**, porque los hooks de Claude no ven ediciones hechas por Bash ni por humanos.

### 4.1 `pyproject.toml` (fragmento)

```toml
[project]
requires-python = ">=3.12"

[dependency-groups]
dev = [
  "ruff==0.17.4",
  "ty==0.0.99",            # beta: fijar exacto y subir a propósito
  "pytest>=8",
  "pytest-cov",
  "import-linter>=2.16",
  "deptry>=0.25",
  "vulture>=2.16",
  "complexipy>=8.3",
]

[tool.ruff]
line-length = 100
target-version = "py312"
src = ["src", "tests"]

[tool.ruff.lint]
select = [
  "E", "W", "F",      # pycodestyle + pyflakes (F401/F841: imports/variables sin uso)
  "I",                # isort
  "UP",               # pyupgrade (sustituye la herramienta)
  "B",                # bugbear
  "SIM", "RET", "PIE",# simplificación: justo lo que la IA infla
  "C4", "PERF",       # comprensiones y rendimiento obvio
  "ARG",              # argumentos sin uso
  "ERA",              # código comentado (eradicate)
  "T20",              # print() olvidados
  "S",                # bandit (seguridad básica)
  "PTH",              # pathlib
  "N",                # nombres
  "D",                # pydocstyle (sustituye interrogate)
  "C90",              # complejidad ciclomática (mccabe)
  "PLR09",            # demasiados args/ramas/returns/sentencias
  "TID",              # imports prohibidos (TID251) y relativos
  "FAST",             # reglas FastAPI (Annotated, response_model redundante)
  "RUF",
]
ignore = ["D100", "D104", "D105", "D107"]  # no exigir docstring en módulos/paquetes/dunders

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101", "D", "PLR2004", "ARG"]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.pylint]
max-args = 6

[tool.ruff.lint.flake8-tidy-imports.banned-api]
"requests".msg = "Usa httpx (cliente async ya en el proyecto)."

[tool.ty.environment]
python-version = "3.12"

[tool.ty.rules]
# Empezar en defaults; endurecer regla a regla. Para repos heredados: `ty check --update-baseline` (preview desde 0.0.93).

[tool.complexipy]
paths = ["src"]
max-complexity-allowed = 15   # verificar nombres de clave en la doc de complexipy 8.x antes de copiar

[tool.vulture]
paths = ["src", "vulture_whitelist.py"]
min_confidence = 80

[tool.deptry]
known_first_party = ["app"]

# Arquitectura hexagonal: dominio ← aplicación ← adaptadores/entrypoints
[tool.importlinter]
root_package = "app"

[[tool.importlinter.contracts]]
name = "Capas hexagonales"
type = "layers"
layers = [
  "app.entrypoints",     # FastAPI routers, handlers Lambda
  "app.adapters",        # boto3, SQLAlchemy, httpx
  "app.application",     # casos de uso, puertos (Protocols)
  "app.domain",          # entidades y reglas puras
]

[[tool.importlinter.contracts]]
name = "El dominio no depende de frameworks ni de AWS"
type = "forbidden"
source_modules = ["app.domain", "app.application"]
forbidden_modules = ["fastapi", "sqlalchemy", "boto3", "botocore", "httpx"]
```

### 4.2 `.pre-commit-config.yaml` (se ejecuta con `prek`; también funciona con `pre-commit`)

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.17.4
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/rohaquinlop/complexipy-pre-commit
    rev: v8.3.0
    hooks:
      - id: complexipy
  - repo: local
    hooks:
      - id: ty
        name: ty check
        entry: uv run ty check
        language: system
        types: [python]
        pass_filenames: false
      - id: import-linter
        name: import-linter
        entry: uv run lint-imports
        language: system
        pass_filenames: false
        types: [python]
      - id: deptry
        name: deptry
        entry: uv run deptry .
        language: system
        pass_filenames: false
        files: ^(pyproject\.toml|uv\.lock|src/.*\.py)$
```

Vulture, jscpd y `pylint R0801` van mejor en **CI** (o en un job semanal "janitor"), como reporte y no como bloqueo por commit: tienen falsos positivos y son de alcance global.

### 4.3 Hooks de Claude Code (`.claude/settings.json` del repo, o `hooks/hooks.json` del plugin del kit)

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          { "type": "command",
            "command": "uv run --no-project python \"${CLAUDE_PROJECT_DIR}/.claude/hooks/ruff_after_edit.py\"",
            "timeout": 30 }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          { "type": "command",
            "command": "uv run --no-project python \"${CLAUDE_PROJECT_DIR}/.claude/hooks/sensores_al_terminar.py\"",
            "timeout": 180 }
        ]
      }
    ]
  }
}
```

- `ruff_after_edit.py`: lee el JSON de stdin, toma `tool_input.file_path` y, si es `.py`/`.pyi`, corre `uv run ruff check --fix --force-exclude <archivo>` y `uv run ruff format --force-exclude <archivo>`. Si quedan errores no arreglables, los imprime en stderr y sale con **exit 2**, para que Claude los vea y los corrija.
- `sensores_al_terminar.py`: si `stop_hook_active` es true, sale con 0 (un solo reintento, sin bucles). Si no, corre en orden `ty check`, `lint-imports` y `pytest -x -q --no-header` (solo si hubo cambios en `*.py`, según `git diff --name-only`). Ante un fallo, imprime el resumen en stderr y sale con exit 2. Así se resuelve lo que señaló Böckeler: que el agente llame a los sensores antes de terminar.
- Riesgo y alcance: los hooks ejecutan comandos locales con los permisos del usuario. Los PostToolUse no ven archivos cambiados por Bash. **No** son una frontera de seguridad (eso es tarea de permisos/sandbox, de otro investigador).
- Alternativa: una **skill de proyecto llamada `verify`**. Claude Code la invoca antes de cada commit si existe en `.claude/skills/` del proyecto (docs de skills). Es la forma más simple de "corre los sensores antes de commitear" sin hook Stop.

### 4.4 CLAUDE.md del repo (pocas líneas que pasan la "prueba de poda" de Anthropic)

```
- Ejecuta todo con `uv run` (nunca pip/python sueltos).
- Antes de empezar: `uv run pytest -q` (Willison: "first run the tests"). Cambios con red/green TDD.
- Arquitectura: domain y application no importan fastapi/boto3/sqlalchemy; lo verifica `uv run lint-imports`.
- Termina solo con evidencia: salida de ty, lint-imports y pytest.
```

## 5. Vacíos: skills propias que conviene crear en el kit

1. **`arquitectura-python`** (reemplaza `software-architecture`). Hexagonal *pragmática* para FastAPI + AWS (Lambda/ECS): puertos como `typing.Protocol`, adaptadores boto3, casos de uso como funciones/clases pequeñas, "functional core / imperative shell". Debe incluir **cuándo NO** abstraer (alineado con KARPATHY.md: sin capas para un CRUD trivial). Remite a `import-linter` como verdad ejecutable, no a reglas en prosa. Referencias para redactarla: `iktakahiro/dddpy`, la skill oficial de FastAPI, Hynek "Design Pressure".
2. **`verify`** (skill de proyecto). Lista de sensores y su orden, con salida resumida. Claude Code la invoca antes de commitear.
3. **`deuda-tecnica`** (job "janitor"). Corre vulture (con whitelist), deptry, complexipy (top 10), jscpd/`pylint R0801` y `ruff --select ERA,ARG,F401` sobre todo el repo. Produce un informe priorizado y propone PRs pequeños de borrado con tests en verde (Böckeler: detección continua de deriva).
4. **`documentacion-python`** (reemplaza `write-concisely`). Docstrings estilo Google (que es lo que valida ruff `D`), README mínimo, **ADR con plantilla MADR 4** en `docs/adr/`, diagramas Mermaid/C4 y sitio con Zensical + mkdocstrings. Reglas de concisión en español e inglés.
5. **`rendimiento-python`**. Cuándo perfilar, `py-spy record/top` (con aviso de que necesita permisos), `scalene` sin IA, y `pytest-benchmark` para fijar regresiones. No hay ninguna skill mantenida que cubra esto bien.
6. **Reescribir `code-simplifier`** como agente con estándares Python (o depender solo de `/simplify` bundled).

## 6. Riesgos de seguridad transversales

- **Skills que vienen dentro de paquetes (library-skills):** cualquier dependencia puede traer `.agents/skills/` y el instalador lo copia. Es un vector de prompt injection por la cadena de suministro. Mitigación: instalar solo las skills elegidas y revisar el diff en el PR.
- **Instaladores `npx` (antislop-ai, skills CLI):** escriben en CLAUDE.md/AGENTS.md y bajan código npm. Mitigación: vendorizar carpetas fijadas a un commit en el marketplace propio.
- **Hooks de terceros que tocan el PATH** (Trail of Bits `modern-python`): son benignos pero interceptan subprocesos. Habilitarlos por repo y a propósito.
- **Herramientas con funciones LLM opcionales** (skylos `[llm]`, scalene AI): pueden enviar código fuera. Dejarlas desactivadas en repos de la empresa.
- **Clones de repos populares** (anti-slop tiene forks casi idénticos): instalar siempre desde el owner original y fijar el commit.
- **Astral → OpenAI (2026-03-19):** las licencias siguen MIT/Apache y la actividad es alta. Riesgo bajo, pero fijar versiones.

## 7. Fuentes

- ty README (beta, versionado 0.0.x): https://github.com/astral-sh/ty · releases: https://github.com/astral-sh/ty/releases
- Anuncio de la beta de ty: https://astral.sh/blog/ty
- OpenAI adquiere Astral (2026-03-19): https://openai.com/index/openai-to-acquire-astral · Talk Python #552: https://talkpython.fm/episodes/show/552/astral-joins-openai
- Release notes de import-linter: https://import-linter.readthedocs.io/en/latest/release_notes
- vulture: https://pypi.org/project/vulture · comparativa (autor skylos, sesgo posible): https://skylos.dev/blog/vulture-false-positives
- Herramientas de código muerto 2026: https://repowise.dev/blog/comparisons/best-dead-code-detection-tools
- skylos: https://pypi.org/project/skylos/
- prek (adopción CPython/Airflow/FastAPI): https://github.com/j178/prek
- FastAPI "Develop with AI": https://fastapi.tiangolo.com/ai-development/ · skill: https://github.com/fastapi/fastapi/tree/master/fastapi/.agents/skills/fastapi · Library Skills: https://library-skills.io/create
- Trail of Bits skills: https://github.com/trailofbits/skills (plugins/modern-python, plugins/code-improver)
- Plugins de Astral para Claude Code: https://github.com/astral-sh/claude-code-plugins · guía pydevtools: https://pydevtools.com/handbook/how-to/how-to-configure-ruff-with-claude-code
- wshobson/agents: https://github.com/wshobson/agents
- iktakahiro/python-fastapi-ddd-skill: https://github.com/iktakahiro/python-fastapi-ddd-skill
- Origen de `software-architecture` / `write-concisely`: https://github.com/NeoLabHQ/context-engineering-kit · https://www.skills.sh/neolabhq/context-engineering-kit/software-architecture · https://github.com/obra/the-elements-of-style
- anti-slop: https://github.com/miqdadbadjuber/anti-slop · reseña (2026-11-06): https://www.ssdnodes.com/learn/anti-slop-skill-for-coding-agents
- code-simplifier: https://github.com/anthropics/claude-plugins-official/tree/main/plugins/code-simplifier
- Comandos y skills bundled de Claude Code (`/simplify`, `/verify`): https://code.claude.com/docs/en/commands · https://code.claude.com/docs/en/skills
- Hooks: https://code.claude.com/docs/en/hooks · https://docs.anthropic.com/en/docs/claude-code/hooks-guide
- Zensical (0.1.0, EOL de Material 2027-05-05): https://zensical.org/upcoming-changes/ · mkdocstrings en mantenimiento: https://github.com/mkdocstrings/python/issues/323
- MADR: https://github.com/adr/madr/releases
- Böckeler / Fowler: ver sección 3 · SlopCodeBench: https://arxiv.org/abs/2603.24755
- Willison: ver sección 3 · Hynek: ver sección 3
