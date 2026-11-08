# 02 — Harnesses, frameworks de flujo y context engineering

Investigación del 2026-11-07. Datos de GitHub sacados ese día con `gh api` (pushed_at, estrellas, releases). Umbral de "mantenido": actividad desde ~2026-09-25. Nada instalado ni configurado.

## Resumen en 6 líneas

1. Lo que más rinde, según Anthropic y Boris Cherny (creador de Claude Code), viene de Claude Code tal cual: **plan mode → revisar el plan → implementar → que Claude verifique su trabajo** (tests, linters). "Darle a Claude una forma de verificar su trabajo multiplica 2-3x la calidad."
2. Un solo framework de flujo como base: **Superpowers** (TDD + plan + revisión con subagentes; Thoughtworks Radar lo pone en "Assess"; Simon Willison lo ha citado varias veces).
3. Para specs en código que ya existe (brownfield): **OpenSpec** (trabaja con deltas, es ligero; Thoughtworks lo prefiere a spec-kit y a BMAD para sistemas existentes).
4. Hooks de calidad **propios y pequeños** (ruff/mypy/pytest) en vez de plugins de terceros: es lo que más se recomienda y lo que menos riesgo tiene.
5. Navegación de código: **CodeGraph** (ya lo usas). Ahorro real medido de forma independiente: 15-25 %, no el 60-90 % que se anuncia.
6. Descartar: enjambres (Ruflo, Gas Town), GSD original (repo comprometido), task-master, Crystal, Conductor (cierra), claude-mem por ahora (subió historiales sin consentimiento).

## Tabla comparativa

Las estrellas y fechas son del 2026-11-07. "Costo de contexto" = lo que gasta siempre (al iniciar la sesión) más lo que gasta al usarse.

| Nombre | Qué hace | Último commit / release | ★ | Evidencia / expertos | Costo de contexto | Riesgo (qué ejecuta) | Veredicto |
|---|---|---|---|---|---|---|---|
| **Claude Code nativo** (plan mode, subagentes, hooks, skills, `/code-review`, auto memory, CLAUDE.md) | El harness base | v2.1.319, 2026-11-06 | 155k | Docs oficiales de best practices; Boris Cherny (X, 2026-01-02 y 2026-01-31): plan mode + verificación + hooks Stop | El mínimo | Sin terceros | **Base obligatoria.** Todo lo demás se suma encima solo si mejora algo medible |
| **obra/superpowers** | Skills de flujo: brainstorming → plan → TDD → desarrollo con subagentes → revisión → cerrar rama; debugging sistemático | v7.0.2, 2026-11-03 | 314k | Thoughtworks Radar vol. 34 (abr-2026, "Assess"); Simon Willison (oct-2025 en adelante, etiqueta jesse-vincent); medición de WotAI (ago-2026) | Hook SessionStart ≈ 777 tokens (0,4 % de 200k); por skill 3,8k–8k tokens cuando carga | Un hook SessionStart (script bash) que inyecta texto; scripts de ayuda en SDD. Sin red ni telemetría | **Recomendado** como framework de flujo único. Fijar versión. Ojo: los cambios recientes son grandes (v7 rehízo brainstorming), así que hay que releer las notas de cada versión antes de actualizar |
| **EveryInc/compound-engineering-plugin** | Plan → work → review → `/compound` (guarda lo aprendido como artefactos) | v3.36.1, 2026-11-06 | 26k | Every (Kieran Klaassen), artículos mar-2026 y sep-2026; comparación de WotAI | 33 skills, ~34k palabras, 298 archivos de referencia: más pesado que Superpowers | Hooks y muchos agentes revisores. Las versiones salen casi a diario | **Opcional / alternativa** a Superpowers, nunca junto con él. Vale la pena solo la idea de "compound" (anotar lo aprendido), y eso se replica con auto memory o un skill pequeño |
| **wshobson/agents** | Catálogo enorme de plugins, agentes y skills multi-herramienta | commit 2026-11-05 (sin releases) | 42k | Popular en listas; no encontré respaldo de expertos reconocidos | Variable. Se elige plugin por plugin | Solo markdown, sin ejecutables en general | **Opcional como cantera**: copiar 1-2 agentes concretos (p. ej. revisor de Python) al marketplace propio, revisados. No instalarlo entero (Thoughtworks avisa contra la "agent instruction bloat") |
| **github/spec-kit** | Spec-driven: constitution → specify → plan → tasks → implement | v1.3.2, 2026-11-06 | 148k | Thoughtworks "Assess"; Böckeler (martinfowler.com, oct-2025) lo critica: specs verbosas, el agente ignora o exagera las instrucciones | Alto: genera muchos markdown por feature | CLI Python (`uv tool`) que escribe plantillas y scripts. Sin telemetría conocida | **Descartar como flujo diario** (pesado, pensado para greenfield). Útil solo para una feature grande y nueva |
| **Fission-AI/OpenSpec** | SDD ligero: propose → apply → archive, con deltas de spec | v1.16.1, 2026-11-07 | 74k | Thoughtworks Radar abr-2026: lo prefiere para brownfield frente a spec-kit, BMAD y Kiro | Bajo/medio: una propuesta por cambio | CLI npm que genera comandos/skills | **Opcional (recomendado si la empresa pide specs)**. No mezclar con el brainstorming/plans de Superpowers en la misma feature |
| **BMAD-METHOD** | Agentes de rol (PM, arquitecto, SM, dev, QA) con flujo ágil completo | v6.12.4, 2026-10-14; commit 2026-11-06 | 55k | Thoughtworks lo describe como "rígido/pesado" | Muy alto | Instalador npm, muchos agentes | **Descartar**: demasiada ceremonia para un dev solo |
| **buildermethods/agent-os** | Estándares + specs por proyecto | commit 2026-10-07; v3.0.0 ene-2026 | 5,6k | Poca evidencia reciente | Medio | Scripts de instalación | **Descartar**: actividad baja, cubierto por CLAUDE.md + skills |
| **GSD (get-shit-done)** → **open-gsd/gsd-core** | Meta-prompting + SDD por fases, 71 comandos y 34 agentes | Original **archivado** el 2026-06-26; gsd-core v1.20.1, 2026-11-05 | 64k (archivado) / 11k | Fork comunitario. Según el fork, el original está "comprometido o abandonado" y ligado al rug-pull del token $GSD (discusión #109, may-2026) | Muy alto (71 comandos, 34 agentes, hooks) | Instalador `npx` que escribe hooks en `.claude/`; incidente de cadena de suministro en el original | **Descartar**: historial de seguridad, solapa con Superpowers y es pesadísimo |
| **garrytan/gstack** | 23 "roles" (CEO, eng manager, QA con Playwright, release, CSO) | v1.97.0.0, 2026-11-07 | 141k | Garry Tan (YC); Pulumi blog (abr-2026) lo compara con Superpowers y GSD | Alto | Skills + Playwright + scripts de ship/deploy | **Descartar** para backend Python: está orientado a producto/startup y web, y se pisa con Superpowers |
| **ruvnet/ruflo** (ex claude-flow) | Enjambres multiagente, "314 herramientas MCP", memoria vectorial | v3.72.2, 2026-11-06 | 81k | Thoughtworks: "Caution" (coding agent swarms). Issue #1425 (mar-2026): stubs, validadores de seguridad sin conectar. Auditoría #1375: preinstall ofuscado en versiones antiguas | Enorme (MCP con cientos de tools) | Servidor MCP, hooks, plugin `ruflo-mods` "sin sandbox" según su propio README | **Descartar**: hype, riesgo alto y deuda técnica documentada |
| **Gas Town / beads** (Steve Yegge) | Orquestación de enjambres / tracker de issues para agentes | gastown commit 2026-10-28; beads v1.3.4, 2026-11-04 | 19k / 29k | Thoughtworks "Caution" (enjambres) | Alto | CLI Go, daemons | **Descartar** gastown. beads queda como curiosidad (issues de GitHub ya cumplen ese papel) |
| **eyaltoledano/claude-task-master** | PRD → tareas vía MCP | último commit 2026-04-23 | 28k | — | Alto (MCP) | MCP + API keys | **Descartar**: sin actividad desde abril |
| **Gentleman-Programming/gentle-ai** | Configurador multiagente: memoria (engram), "Organic-Driven Development", skills, MCP, personas | v4.4.0, 2026-11-07 | 8,6k | Comunidad hispana; sin expertos externos | Medio/alto, según lo que se active | Instalador que toca config de varios agentes (riesgo de tocar config global) | **Opcional, con cuidado**: tu `gentle-factory` local (último commit 2026-11-02, sin publicar) es la versión controlada. No meter gentle-ai en el kit corporativo sin revisarlo |
| **thedotmack/claude-mem** | Memoria persistente: captura lo que usan las tools y lo resume con Agent SDK | v15.12.0, 2026-11-07 | 115k | Popular. **Incidente**: v15.2.0–15.8.2 subía 30 días de historiales de prompts a un servicio hospedado antes de pedir consentimiento (Ground Truth, 2026-11-07; corregido en 15.8.3) | Inyecta contexto en SessionStart; cada observación gasta tokens extra (llamadas al SDK) | 5 hooks, worker HTTP local (puerto 37700+uid), SQLite/Chroma, telemetría opt-out, contacto con cmem.ai | **Descartar por ahora** en un entorno de empresa (código propietario). La auto memory nativa + CLAUDE.md cubren lo esencial |
| **oraios/serena** | MCP de navegación semántica vía LSP (símbolos, refactors) | v2.1.0, 2026-10-19; commit 2026-10-28 | 31k | Benchmark independiente (Reddit r/LLMDevs, 2026): −14,8 % de tokens en Codex; en Claude Code apenas se llamó | Esquemas MCP + instrucciones | Servidor Python con lenguaje servers; dashboard web local | **Opcional**: alternativa a CodeGraph. No tener los dos |
| **colbymchenry/codegraph** | Grafo de código SQLite + MCP `codegraph_explore` | v1.6.2, 2026-10-03; commit 2026-11-01 | 77k | Vendedor: −62 % tokens / −44 % costo. Independiente: −24 % tokens (Codex). Su propio README avisa de **+80 % de contexto residente** en sesiones largas | ~1,9k tokens de instrucciones MCP + resultados grandes | Local (SQLite); **telemetría de uso activa por defecto** (`codegraph telemetry off` / `DO_NOT_TRACK=1`); busca actualizaciones | **Recomendado** (ya lo usas), con la telemetría apagada en el repo de la empresa |
| **ccusage/ccusage** | Mide tokens y costo leyendo los JSONL locales de Claude Code | v20.0.48, 2026-11-02; commit 2026-11-07 | 19k | Estándar de facto en la comunidad | Cero (va fuera de la sesión) | Solo lee `~/.claude/projects`. Correr con `npx`/`bunx` fijando versión | **Recomendado** (herramienta externa, no plugin) |
| **sirmalloc/ccstatusline** | Status line configurable (modelo, contexto %, costo, rama) | v2.2.34, 2026-11-06 | 13,5k | Muy usado | Cero (no entra en el contexto) | Comando que corre en cada refresco | **Recomendado** (o claude-powerline, 1,2k ★, activo 2026-11-06, como alternativa). Elegir uno |
| **nizos/tdd-guard** | Hook que bloquea escribir implementación sin un test que falle antes | commit 2026-11-03; v1.7.0 jun-2026 | 2,4k | Cuadra con Kent Beck ("el genio no quiere hacer TDD", jun-2025) | Llamada extra a un modelo por cada edición (costo) | Hook PreToolUse + reporter de pytest | **Opcional**: probar una semana. Si Superpowers ya impone TDD, puede sobrar |
| **Hooks de calidad propios** (PostToolUse: `ruff format`/`ruff check --fix`; Stop: `pytest -q` + `mypy`) | Verificación determinista al editar o terminar | n/a (código tuyo) | — | Boris Cherny (hook Stop para verificar); Geoffrey Huntley (oct-2026: "falla el commit, inyecta el prompt… diez de diez"); docs: "enforce the rules that can't have exceptions" | Solo la salida de los errores | Tus scripts, revisables | **Recomendado**: el núcleo del kit |
| **anthropics/claude-plugins-official** | Marketplace oficial (code-review, feature-dev, hookify, security-guidance, etc.) | commit 2026-11-07 | 46k | Anthropic | Por plugin | Revisar cada plugin; los de terceros listados ahí no los audita Anthropic en detalle | **Recomendado como fuente** para copiar/fijar plugins concretos en tu marketplace |
| **humanlayer** (y su "advanced context engineering": research → plan → implement) | Comandos/agentes de investigación-plan-implementación + app | commit 2026-11-02 | 13k | Dex Horthy, charla y artículo "12-factor agents"/ACE | Medio | App de escritorio y daemon | **Opcional (idea, no herramienta)**: el patrón "research → plan → implement con compactación intencional" ya lo cubren plan mode + Superpowers |
| **affaan-m/ECC** (everything-claude-code) | Megacolección de configs | v2.2.3, 2026-10-01; commit 2026-11-06 | 299k | Estrellas virales; clones con malware detectados (issue #2242, jun-2026) | Enorme si se instala entero | Hooks y scripts variados | **Descartar** como instalación. Como mucho, leerlo de referencia |
| **hesreallyhim/awesome-claude-code** | Lista curada | commit 2026-11-08 | 57k | Referencia comunitaria | 0 | 0 | **Recomendado como lectura** (no se instala) |
| **Orquestadores**: claude-squad / Crystal / Conductor / Nimbalyst | Varias sesiones en paralelo con worktrees | squad: 2026-08-20; Crystal deprecado feb-2026; **Conductor cierra** (se une a Meta, downloads cerrados nov-2026) | 8,7k / 3,1k / — | aq.dev, agentsroom (2026) | 0 en contexto, pero se multiplica el gasto | tmux/Electron que corren shells | **Descartar por ahora**: claude-squad lleva sin commits desde agosto, Crystal está muerto y Conductor cierra. Claude Code ya trae worktrees, subagentes y sesiones en paralelo. Volver a mirarlo cuando tengas soltura |
| **Ralph loop** (Huntley) | Bucle `while` que relanza al agente contra un plan/spec | how-to-ralph-wiggum: ene-2026 | 1,8k | Boris Cherny lo usa para tareas largas (plugin ralph-wiggum) | Alto (muchas sesiones) | Autonomía larga = riesgo | **Descartar al inicio**. Solo para tareas largas con tests sólidos, en sandbox |

## Spec-driven vs TDD vs "plan mode + review"

| Enfoque | A favor | En contra | Quién lo dice |
|---|---|---|---|
| **Spec-driven** (spec-kit, Kiro, OpenSpec) | Deja la intención por escrito fuera del chat; sirve para alinearse con el equipo | Specs verbosas; el agente ignora o exagera instrucciones; supone que no aprendes nada mientras implementas | Böckeler/Thoughtworks (oct-2025, abr-2026); Kent Beck (vía Fowler, ene-2026): "suposición bizarra de que no aprenderás nada al implementar" |
| **TDD** | Verificación objetiva; te mantiene en el loop; evita regresiones | El agente tiende a escribir el código primero o a borrar tests: hay que forzarlo (skill o hook) | Kent Beck ("TDD es un superpoder con agentes", jun-2025); Simon Willison (guía *Agentic Engineering Patterns*, capítulo "Red/green TDD") |
| **Plan mode + review** | Nativo, barato, rápido; el plan se discute antes de tocar código | Si no hay verificación al final, es solo opinión | Boris Cherny: "la mayoría de sesiones empiezan en plan mode… dale a Claude cómo verificar su trabajo" |

**Conclusión práctica:** plan mode (o el brainstorming/writing-plans de Superpowers) para decidir **qué** hacer, TDD para **probar** que funciona y hooks deterministas para que no se salte ninguno de los dos. La spec formal (OpenSpec) solo para cambios que otros deben aprobar. Thoughtworks recomienda además "re-evaluar la necesidad de herramientas SDD a medida que los agentes mejoran".

## Combinación recomendada (y qué NO mezclar)

**Núcleo (instalar por repo, versiones fijas):**
1. Claude Code nativo: CLAUDE.md corto, plan mode y subagentes para explorar.
2. **Superpowers** (fijado a una versión) como único framework de flujo.
3. **Hooks propios** de Python: PostToolUse → `ruff format` + `ruff check --fix` sobre el archivo editado; Stop → `pytest -q` (y `mypy` si el repo lo usa), devolviendo solo el error.
4. **CodeGraph** con `codegraph telemetry off`.
5. Fuera de la sesión: **ccusage** (costo) + **ccstatusline** (status line con % de contexto).

**Opcionales (decidir uno por uno):** OpenSpec (si hace falta spec revisable), tdd-guard (si Claude se salta el TDD), 1-2 agentes sueltos copiados de wshobson/agents o del marketplace oficial.

**No mezclar, porque se pisan:**
- **Superpowers + Compound Engineering + GSD + gstack + BMAD**: los cinco quieren mandar en el flujo (brainstorm/plan/review). Uno solo. Instalar dos duplica skills de revisión y planificación, se contradicen y suben el costo de contexto (WotAI midió los dos juntos).
- **spec-kit + OpenSpec**, o cualquier SDD + el `writing-plans` de Superpowers en la misma feature: dos fuentes de verdad del plan.
- **CodeGraph + Serena** (u otro indexador): herramientas solapadas; Claude elige mal o no usa ninguno (el benchmark independiente vio que en Claude Code se llaman poco).
- **claude-mem + auto memory nativa + engram (gentle-ai)**: tres memorias que inyectan contexto en SessionStart.
- **tdd-guard + skill TDD de Superpowers + un hook Stop que corre pytest**: elegir como mucho dos capas.
- **Dos status lines** (ccstatusline y claude-powerline): solo cabe una.
- Hooks de formato de un plugin de terceros **y** tus hooks: el archivo se formatea dos veces y puede haber conflictos de configuración de ruff.

## Seguridad: puntos a vigilar

- Todo plugin con hooks ejecuta código en tu máquina con tus permisos en cada evento. Revisar `hooks/` y fijar el commit o la versión en el marketplace propio.
- Instaladores `npx …@latest` (GSD, Ruflo, OpenSpec, ccusage): fijar la versión. Ya tienes `ignore-scripts=true` en `~/.npmrc`.
- Telemetría activa por defecto: CodeGraph (apagable), claude-mem (opt-out, más el incidente de subida de historiales).
- Lethal trifecta (Willison): datos privados + contenido no confiable + acción externa. Evitar MCPs que mezclen las tres.
- Clones maliciosos de repos virales (caso ECC): instalar solo desde el org oficial.

## Alternativas a Claude Code (solo porque afectan a la portabilidad)

Superpowers, CodeGraph, OpenSpec, gentle-ai y wshobson/agents soportan también Codex CLI, OpenCode (anomalyco/opencode, 225k ★, activo), Cursor y Antigravity. Si mañana la empresa impone otro agente, el kit (skills en formato Agent Skills, hooks como scripts) se lleva casi entero. Amp (Sourcegraph) es la que usa Huntley. No hace falta adoptarla.

## Fuentes

- Anthropic, *Effective context engineering for AI agents* (2025-09-29): https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Anthropic, *Harness design for long-running application development* (2026-03-24): https://www.anthropic.com/engineering/harness-design-long-running-apps
- Anthropic, *Scaling Managed Agents* (2026-04-08), "los harnesses codifican supuestos que caducan": https://www.anthropic.com/engineering/managed-agents
- Claude Code best practices: https://code.claude.com/docs/en/best-practices
- Boris Cherny, consejos (2026-01-02): https://x.com/bcherny/status/2007179861115511237 · (2026-01-31): https://x.com/bcherny/status/2017742741636321619
- Thoughtworks Technology Radar vol. 34 (abr-2026): https://www.thoughtworks.com/content/dam/thoughtworks/documents/radar/2026/04/tr_technology_radar_vol_34_en.pdf · OpenSpec: https://www.thoughtworks.com/en-de/radar/tools/openspec
- Birgitta Böckeler, *Understanding SDD: Kiro, spec-kit, Tessl* (2025-10-15): https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html
- Martin Fowler, Fragments (2026-01-08, cita de Kent Beck sobre SDD): https://martinfowler.com/fragments/2026-01-08.html
- Kent Beck, *Augmented Coding: Beyond the Vibes* (2025-06-25): https://newsletter.kentbeck.com/p/augmented-coding-beyond-the-vibes · Pragmatic Engineer: https://newsletter.pragmaticengineer.com/p/tdd-ai-agents-and-coding-with-kent
- Simon Willison, *Agentic Engineering Patterns* (subagentes, red/green TDD): https://simonwillison.net/guides/agentic-engineering-patterns/subagents/ · etiqueta jesse-vincent: https://feeds.simonwillison.net/tags/jesse-vincent · Huntley (2026-10-13): https://feeds.simonwillison.net/tags/geoffrey-huntley/ · Armin Ronacher: https://simonwillison.net/tags/armin-ronacher/
- Jesse Vincent en Heavybit: https://www.heavybit.com/library/podcasts/open-source-ready/ep-36-managing-ai-coding-agents-with-jesse-vincent
- Superpowers release notes (v7.0.2): https://github.com/obra/superpowers/releases/tag/v7.0.2
- WotAI, *Compound engineering vs Superpowers, measured* (2026-08-28): https://wotai.co/blog/compound-engineering-vs-superpowers
- Every, *Compound Engineering Camp*: https://every.to/source-code/compound-engineering-camp-every-step-from-scratch
- Pulumi, *Superpowers, GSD, and GSTACK* (2026-04-13): https://www.pulumi.com/blog/claude-code-orchestration-frameworks/
- GSD movido y fork: https://github.com/gsd-build/get-shit-done · https://github.com/open-gsd/gsd-core/discussions/109
- Ruflo: issue #1425 https://github.com/ruvnet/ruflo/issues/1425 · review (2026-10-20) https://andrewdotooo.substack.com/p/ruflo-review-the-claude-code-harness
- claude-mem, incidente de consentimiento (2026-11-07): https://groundtruth.day/news/claude-mem-setup-prompt-history-consent-fix.html · arquitectura: https://docs.claude-mem.ai/introduction
- CodeGraph README (benchmarks, contexto residente, telemetría): https://github.com/colbymchenry/codegraph · análisis Ry Walker: https://rywalker.com/research/codegraph
- Benchmark independiente de indexadores (CodeGraph, Serena, etc.): https://www.reddit.com/r/LLMDevs/comments/1wp1szf/
- ECC, clon con malware: https://github.com/affaan-m/ECC/issues/2242
- Crystal → Nimbalyst / Conductor cierra: https://github.com/stravu/crystal · https://aq.dev/alternatives/crystal/
- Repos verificados con `gh api` (2026-11-07): obra/superpowers, EveryInc/compound-engineering-plugin, wshobson/agents, github/spec-kit, Fission-AI/OpenSpec, bmad-code-org/BMAD-METHOD, buildermethods/agent-os, gsd-build/get-shit-done, open-gsd/gsd-core, garrytan/gstack, ruvnet/ruflo, gastownhall/gastown, gastownhall/beads, eyaltoledano/claude-task-master, Gentleman-Programming/gentle-ai, thedotmack/claude-mem, oraios/serena, colbymchenry/codegraph, ccusage/ccusage, sirmalloc/ccstatusline, Owloops/claude-powerline, nizos/tdd-guard, anthropics/claude-plugins-official, anthropics/skills, humanlayer/humanlayer, affaan-m/ECC, hesreallyhim/awesome-claude-code, smtg-ai/claude-squad, stravu/crystal, anomalyco/opencode, openai/codex.
