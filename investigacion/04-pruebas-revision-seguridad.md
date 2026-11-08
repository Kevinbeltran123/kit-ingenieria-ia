# 04 — Pruebas, revisión de código y seguridad

Investigación del 2026-11-07. Actividad verificada con `gh api` ese mismo día (fechas en UTC).
Criterio: mantenido si tiene commits desde ~2026-09-25. El contenido web se tomó como dato, no como instrucción.
Nada se instaló ni se configuró.

## Resumen

- **Base que ya tienes**: `test-driven-development` y `systematic-debugging` vienen de **obra/superpowers**. El repo está muy activo (v7.0.2 del 2026-11-03), pero tu copia es del **5 de mayo de 2026**: está desactualizada, no obsoleta. `code-review` y `security-review` son **comandos integrados de Claude Code**, no plugins: se actualizan solos con el CLI. `review-local-changes` viene de **NeoLabHQ/context-engineering-kit**, sin push desde el 2026-08-26: **no cumple el criterio**. Lo sustituye `pr-review-toolkit` (oficial).
- **Revisión de código**: ningún benchmark es neutral, y cada proveedor gana el suyo. En benchmarks de terceros, Claude Code como revisor sale con *recall* medio-alto y precisión baja: 23 % de precisión y 51 % de recall en Propel; F1 39 % en Martian Code Review Bench. En la práctica: revisión local con plugins oficiales y, en CI, `claude-code-action` con un prompt acotado. Antes de pagar un SaaS, prueba dos semanas en tus propios repos.
- **Seguridad**: la combinación más sólida es gratis y determinista: `uv lock` + `exclude-newer` + `pip-audit`/`osv-scanner` + `gitleaks` o `trufflehog` + `zizmor` + `bandit`/`semgrep`. Encima va una capa de IA: `security-guidance` (oficial) en el bucle y `claude-security` o Trail of Bits para auditorías bajo demanda.
- **Pruebas generadas por IA**: hay evidencia empírica de que los agentes abusan de los mocks (MSR 2026). También hay casos con 100 % de cobertura y solo 4 % de *mutation score*. El remedio con evidencia es mutation testing (mutmut) más property-based testing (Hypothesis). Anthropic ya publicó resultados de un agente PBT sobre Hypothesis.

## Tabla

Estrellas solo como referencia. "Commit" = último commit en la rama principal. "Rel." = último release.

### Pruebas

| Nombre | Tipo | Qué hace | Último commit / release | Costo | Evidencia | Riesgo | Veredicto |
|---|---|---|---|---|---|---|---|
| **obra/superpowers** (TDD, systematic-debugging, verification-before-completion, requesting/receiving-code-review) | Plugin (skills) | Fuerza el ciclo rojo-verde-refactor, la depuración por causa raíz y la verificación antes de declarar algo terminado | 2026-11-03 / v7.0.2 (2026-11-03) | Gratis (MIT) | Evals del autor (Jesse Vincent, 2026-09-21): sin superpowers los builds salen "significativamente más defectuosos", y la ejecución nativa cuesta la mitad que SDD. Caso real: A. Connell, 415 issues / 320 PR (2026-10-24). 314k★ | Bajo-medio: solo skills, pero el plugin completo trae hooks SessionStart y el subagent-driven-development gasta mucho contexto (issue #2618: 830k tokens) | **Mantener**. Actualiza tu copia de mayo a v7.x **solo** con las skills que usas (TDD, debugging, verification, receiving-code-review), fijando el commit. No instales el plugin entero |
| **Trail of Bits: property-based-testing** | Plugin (skill) | Escribe, revisa y clasifica pruebas Hypothesis, y trae evals de efectividad | Repo 2026-11-06 (plugin 2026-09-16) | Gratis | Trail of Bits (firma de auditoría reconocida). Línea alineada con el paper de Anthropic sobre PBT agéntico: 56 % de reportes válidos, 86 % en el top (2026-01-14) | Bajo: solo skill y evals | **Adoptar** |
| **Trail of Bits: mutation-testing** | Plugin (skill) | Configura campañas de mutación y analiza mutantes sobrevivientes (¿hueco del test o mutante equivalente?) | ídem | Gratis | ToB. Ojo: usa **mewt/muton** (herramientas de ToB), no mutmut | Bajo | **Evaluar**. Útil para analizar sobrevivientes. Para Python, mejor ejecutar con mutmut (skill propia, ver vacíos) |
| **mutmut** | CLI | Mutation testing para Python | 2026-11-07 / 3.8.0 (2026-09-12) | Gratis | El estudio empírico de PBT en Python (OOPSLA, ACM 2025-10) lo usa como métrica: los PBT matan mutantes 6× más que los unit tests (39 % frente a 6,6 %) | Bajo | **Adoptar** en CI (nocturno, por módulo crítico) |
| cosmic-ray | CLI | Mutation testing para Python (distribuido) | 2026-10-15 / v8.7.0 (2026-08-09) | Gratis | Menos uso | Bajo | Alternativa: solo si mutmut no escala |
| **Hypothesis** | Librería | Property-based testing | 2026-11-06 / v6.170.15 (2026-11-06) | Gratis | Anthropic + Zac Hatfield-Dodds (mantenedor), arXiv 2510.09907 | Bajo | **Adoptar** |
| **pytest** | Librería | Base de pruebas | 2026-11-08 | Gratis | Estándar | Bajo | **Adoptar** |
| **testcontainers-python** | Librería | Postgres, Redis, LocalStack reales en tests | 2026-10-07 / v4.15.0 (2026-07-24) | Gratis | Estándar de facto contra el "todo mockeado" | Bajo (requiere Docker) | **Adoptar** para pruebas de integración (AWS → LocalStack) |
| **schemathesis** | CLI/librería | Pruebas basadas en propiedades desde OpenAPI (FastAPI) | 2026-11-08 / v4.33.1 (2026-11-04) | Gratis (núcleo) | Muy activo | Bajo | **Adoptar** si exponen APIs con OpenAPI |
| pact-python | Librería | Pruebas de contrato consumidor-proveedor | 2026-11-03 / 4.2.0 (2026-10-23) | Gratis | Activo | Bajo | Opcional: solo si hay microservicios con varios equipos |

### Revisión de código

| Nombre | Tipo | Qué hace | Último commit / release | Costo | Evidencia | Riesgo | Veredicto |
|---|---|---|---|---|---|---|---|
| **`/code-review`** (integrado en Claude Code) | Comando integrado | Revisa el diff, un PR o una rama por niveles de esfuerzo; `--comment` y `--fix` | Viaja con el CLI (claude-code 2026-11-06) | Incluido en tu plan | Oficial | Bajo | **Mantener** (es lo que ya tienes) |
| **pr-review-toolkit** (oficial) | Plugin (agentes) | 6 agentes: code-reviewer, **pr-test-analyzer**, **silent-failure-hunter**, type-design-analyzer, comment-analyzer, code-simplifier | 2026-10-26 | Gratis | Marketplace oficial de Anthropic | Bajo: solo agentes, sin hooks | **Adoptar**. Reemplaza `review-local-changes`. pr-test-analyzer apunta justo a "tests que no prueban" |
| code-review (plugin oficial) | Plugin | Revisión de PR multiagente con filtro de confianza | 2026-10-26 | Gratis | Oficial | Bajo | Redundante con el comando integrado. Opcional |
| review-local-changes (NeoLabHQ) | Skill | Revisión multiagente de cambios locales | push 2026-08-26 | Gratis | — | Bajo | **Retirar**: sin actividad en 6 semanas y cubierto por pr-review-toolkit |
| **anthropics/claude-code-action** | GitHub Action | Claude en CI: revisión de PR, `@claude`, tareas | 2026-11-06 / v1.0.269 (2026-11-06) | Tokens de API + minutos de Actions (≈ US$1/PR según estimación de repowise) | Oficial. Muy usado (9,8k★) | **Medio-alto**: corre con secretos en CI. Prompt injection vía título o cuerpo del PR, `pull_request_target` | **Adoptar con cuidado**: fijar por SHA, permisos mínimos, sin `pull_request_target`, allowlist de herramientas, auditar con zizmor |
| Claude Code Review (gestionado) | SaaS (GitHub App) | Flota de agentes que revisa PRs; GA desde 2026-10-15 | — | Team/Enterprise; US$15-25 por PR (Anthropic) | Anthropic reporta <1 % de hallazgos marcados como incorrectos (dato del propio proveedor) | Bajo-medio | Solo si la empresa tiene plan Team o Enterprise. Ojo: por defecto revisa "after every push", lo que multiplica el costo |
| claude-code-security-review (Action) | GitHub Action | Revisión de seguridad del diff en CI | push 2026-02-11 | Tokens | — | — | **Descartar**: sin mantenimiento. Lo cubren claude-code-action y claude-security |
| CodeRabbit | SaaS + plugin oficial (`coderabbit`) | Revisión de PR | skills 2026-11-07 | Pago (~US$24/dev/mes, plan anual) | Signal65 (2026-03, encargado por el proveedor): mejor precisión. Macroscope: 10,8 comentarios/PR (ruidoso). Martian: 70 % de precisión | Medio (datos a un tercero) | Probar 2 semanas solo si la empresa paga |
| Greptile | SaaS + plugin oficial | Revisión con índice del repo | skills 2026-11-03 | Pago | Martian: 79 % de precisión (oct-2026). Terceros: recall ~45 %, por debajo de lo que declara | Medio | Ídem |
| Qodo / **PR-Agent** (The-PR-Agent/pr-agent) | SaaS / OSS | Revisión de PR. PR-Agent es Apache-2.0, autoalojable, con tu propia API key | 2026-11-07 / v0.50.0 (2026-11-07) | OSS gratis + tokens; Qodo de pago | Martian: Qodo Extended en primer lugar por F1 (64 %). Signal65: Qodo con muchos falsos positivos | Medio | Alternativa OSS a claude-code-action si quieren otro modelo como "segundo par de ojos" |
| Copilot code review | SaaS | Revisión de PR en GitHub | — | Incluido en Copilot de pago | Propel: el F1 más bajo (25 %). Signal65: el que más falsos positivos dio | Bajo | Solo si la empresa ya paga Copilot |
| Cursor Bugbot | SaaS | Revisión de PR | — | Pago | Pocos comentarios, buena precisión (Macroscope, Signal65) | Medio | Fuera de tu stack |

### Seguridad (código, dependencias, secretos, CI)

| Nombre | Tipo | Qué hace | Último commit / release | Costo | Evidencia | Riesgo | Veredicto |
|---|---|---|---|---|---|---|---|
| **`/security-review`** (integrado) | Comando integrado | Revisión de seguridad del diff de la rama | Con el CLI | Incluido | Oficial | Bajo | **Mantener** |
| **security-guidance** (oficial) | Plugin (hooks + LLM) | 3 capas: avisos por regex en Edit/Write (~25 patrones: `yaml.load`, `pickle`, `torch.load`…), revisión del diff con LLM al final de cada turno y revisión agéntica en `git commit` | 2026-11-06 | Gratis + tokens extra | Oficial. Ya lo tienes instalado (global) | Medio: hooks que corren en cada turno; costo y latencia | **Adoptar por repo** y pasarlo de global a proyecto |
| **claude-security** (oficial) | Plugin (agentes + hooks + workflows) | Escaneo multiagente con modelo de amenazas y verificación independiente; salida MD/JSONL/**SARIF**; parches opcionales | 2026-09-25 (al límite del criterio) | Gratis + muchos tokens | Oficial. Versión local del producto Claude Security | Medio: corre con tus permisos y sin aislamiento propio; para repos no confiables, usar sandbox-runtime | **Adoptar bajo demanda** (activar, escanear, desactivar), p. ej. antes de cada release |
| **trailofbits/skills** (static-analysis, supply-chain-risk-auditor, differential-review, insecure-defaults, sharp-edges, agentic-actions-auditor, modern-python, fp-check) | Marketplace | Auditoría: Semgrep/CodeQL guiados, riesgo de dependencias (OSV), revisión diferencial, auditoría de GitHub Actions con agentes, Python moderno (uv/ruff/ty) | 2026-11-06 (static-analysis 2026-10-23) | Gratis | Trail of Bits. Recomendado en vanja.io (2026-11-02) para auditorías | Bajo-medio: `modern-python` trae **hooks con shims de pip/pipx** que interceptan comandos (revisar antes) | **Adoptar selectivo**: static-analysis, supply-chain-risk-auditor, differential-review, agentic-actions-auditor. modern-python solo tras revisar sus hooks |
| trailofbits/skills-curated | Marketplace | Selección de skills de terceros | push 2026-07-14 | Gratis | — | — | Descartar (inactivo) |
| **Semgrep CE** (CLI) | CLI | SAST multilenguaje | 2026-11-03 / v1.184.0 (2026-11-05) | Gratis (CE) | Estándar de industria | Bajo | **Adoptar** (pre-commit/CI) |
| Semgrep Guardian (plugin oficial `semgrep`) | Plugin (MCP + hooks) | Escanea el código que genera el agente (Code, Supply Chain, Secrets) y le pide regenerarlo hasta que quede limpio | repo semgrep/guardian 2026-11-05 | Requiere cuenta Semgrep (gratis con límites, luego de pago) | "Under active development" (aviso del propio README) | Medio: login y envío de metadatos a Semgrep; hooks en cada edición | Evaluar más adelante. El viejo `semgrep/mcp` está **archivado** |
| **bandit** | CLI | SAST específico de Python | 2026-10-27 / 1.9.4 (2026-02-25) | Gratis | PyCQA | Bajo | **Adoptar** (o reglas `S` de ruff, que lo replican) |
| **pip-audit** | CLI | CVE de dependencias Python (PyPA) | 2026-10-30 / v2.10.1 (2026-06-10) | Gratis | PyPA | Bajo | **Adoptar** |
| **osv-scanner** | CLI | CVE multiecosistema + base de **paquetes maliciosos** de OpenSSF | 2026-11-05 / v2.7.0 (2026-10-12) | Gratis | Google. El incidente mrmustard (PyPI, 2026-07) está registrado como MAL-2026-11049 | Bajo | **Adoptar** (complementa pip-audit) |
| **uv** (`uv lock` + `exclude-newer = "7 days"`) | Gestor | Lock reproducible con hashes y "enfriamiento" ante releases recién publicadas | 2026-11-08 | Gratis | Docs de uv (2026-10-14). zizmor y OWASP recomiendan 7 días de cooldown. Incidentes 2026: litellm, mrmustard, PyTorch Lightning | Bajo | **Adoptar**: es la defensa más barata contra paquetes comprometidos |
| **gitleaks** | CLI | Secretos en commits (rápido, pre-commit) | 2026-10-23 / v8.30.1 (2026-03-21) | Gratis | 30k★, estándar | Bajo | **Adoptar** en pre-commit |
| **trufflehog** | CLI | Secretos con **verificación** contra la API del proveedor | 2026-11-05 / v3.99.8 (2026-11-02) | Gratis (OSS) | Truffle Security | Bajo | **Adoptar** en CI (historial completo, `--only-verified`) |
| **zizmor** | CLI | Análisis estático de GitHub Actions: injection, `pull_request_target`, impostor commits, permisos, cooldown | 2026-11-08 / v1.32.0 (2026-11-02) | Gratis | OWASP GitHub Actions Cheat Sheet lo recomienda junto a CodeQL | Bajo | **Adoptar**: imprescindible con claude-code-action |
| step-security/harden-runner | GitHub Action | Control de egress y auditoría en runners | 2026-11-06 / v2.22.4 | Gratis (comunitario) | StepSecurity documentó el incidente mrmustard | Bajo | Opcional, recomendable en workflows con secretos |
| **snyk/agent-scan** (antes invariantlabs mcp-scan) | CLI | Escanea MCP servers y **skills** buscando prompt injection, tool poisoning, etc. | 2026-11-06 / v0.6.11 | Gratis (OSS) | Snyk / Invariant Labs | Bajo-medio (puede enviar descripciones a su API; revisar flags) | **Adoptar** como paso de auditoría antes de instalar |
| Socket (socket-mcp) | MCP | Puntaje de riesgo de paquetes antes de añadirlos | 2026-11-06 / v0.2.1 (2026-09-17) | Gratis con límites | Socket.dev | Medio (servicio externo) | Opcional |
| Snyk (studio-recipes, snyk-ls) | SaaS/MCP | SCA/SAST comercial | 2026-10-20 | Pago | — | Medio | Solo si la empresa ya lo usa |
| Aikido, SonarQube, Endor Labs (plugins oficiales) | Plugins de terceros | SAST/SCA de cada proveedor | 2026-11-05/06 | Pago (con capa gratis) | Listados en el marketplace oficial | Medio | Solo si la empresa ya los usa |
| **sandbox-runtime** + sandbox de Claude Code | Runtime | Aislamiento de filesystem y red para Bash (`/sandbox`) | 2026-11-06 / v0.0.81 (2026-10-20) | Gratis | Docs oficiales: defensa en profundidad incluso si un prompt injection evade al modelo | Bajo | **Adoptar** para tareas largas y repos no confiables |

## Riesgos propios de agentes (lo que hay que saber)

1. **Las skills son instrucciones, no documentación.** Un `SKILL.md` entra al contexto como prompt (Red Hat Developer, 2026-08-18). Ningún escáner automático lo detecta de forma fiable: CSA (2026-06) reporta 0 % de detección en escáneres clásicos para ataques en lenguaje natural.
2. **Contexto dinámico `!`**: los comandos `!` de una skill **se ejecutan antes** de que el modelo vea la skill, así que las defensas del modelo no intervienen (Datadog Security Labs, 2026-05-11). Se puede desactivar por configuración.
3. **Hooks = shell arbitrario** en cada evento. PromptArmor mostró un hook que esquiva la aprobación humana. CVE-2025-59536 (Check Point): RCE y robo de token a través de archivos del proyecto.
4. **Plugins oficiales también fallan**: Pluto Security encontró que **Hookify** (marketplace oficial) leía reglas del repo y las inyectaba por un canal confiable. Bastaba un repo malicioso para filtrar variables de entorno.
5. **Pinning**: reinstalar un plugin sin SHA trae lo que haya en la rama por defecto. Hubo un bug en el que una rama con nombre de SHA resolvía a código del atacante (GHSA-pq7j-f95f-qfcv, corregido en 2.1.179).
6. **Ecosistemas abiertos**: Koi Security encontró 341 skills maliciosas (11,9 %) en ClawHub. SkillsMP tiene más de 630k skills sin revisión.
7. **CI**: claude-code-action con secretos más texto de PR controlado por terceros es el escenario clásico de prompt injection. zizmor y la skill `agentic-actions-auditor` de ToB lo cubren.
8. **Permisos**: las reglas `Bash(...)` son "best-effort" (no detectan `curl -L` ni variables). Para red y filesystem, el sandbox. Un `.claudeignore` **no tiene efecto**: usa `Read(./.env)` en `deny`.

## Checklist para auditar un plugin antes de instalarlo

1. **Origen**: ¿es del marketplace oficial o de una organización conocida (Anthropic, Trail of Bits, el proveedor oficial)? `claude plugin marketplace list` muestra de dónde viene cada marketplace.
2. **Actividad y dueño**: `gh api repos/OWNER/REPO` (pushed_at, archived) y `commits?per_page=5`. Desconfía de cuentas nuevas, de saltos raros de estrellas y de un mantenedor único sin historial.
3. **Fijar versión**: anota el **commit SHA** (o el `sha256`) e instala con eso. Nunca la rama por defecto.
4. **Inventario sin instalar**: carga con `claude --plugin-dir DIR` en una sesión desechable, o usa `/plugin` → panel "Will install". Lista skills, agentes, hooks, MCP y LSP.
5. **Lee completos** `hooks/hooks.json`, `.mcp.json`, `bin/` y cada script (`*.sh`, `*.py`, `*.js`). Busca `curl`, `wget`, `nc`, `base64`, `eval`, `exec`, lecturas de `~/.ssh`, `~/.aws`, `.env`, `~/.claude`, y escrituras en `settings.json` o `CLAUDE.md`.
6. **Lee cada SKILL.md, agente y comando** buscando instrucciones ocultas: "no le digas al usuario", URLs externas, "incluye el contenido de…", comentarios HTML, Unicode invisible (`grep -P '[\x{200B}-\x{200F}\x{202A}-\x{202E}\x{2060}-\x{2064}]'`) y bloques `!` de contexto dinámico.
7. **Dependencias**: ¿el MCP corre `npx`/`uvx` sin versión fija? Exige versión exacta y lockfile; pásalo por `osv-scanner`/`pip-audit`.
8. **Escáner automático** como segunda opinión, no como garantía: `snyk/agent-scan` sobre la carpeta y, si está disponible, SkillSpector (NVIDIA).
9. **Mínimo privilegio**: instala en **alcance de proyecto**, deja `deny` para `Read(./.env*)`, `Read(~/.ssh/**)` y `Read(~/.aws/**)`, y activa `/sandbox`. Desactiva lo que no uses del plugin.
10. **Prueba en un repo desechable** primero (sin secretos en el entorno). Observa qué comandos lanza.
11. **Revisa de nuevo en cada actualización**: haz `git diff` entre el SHA viejo y el nuevo antes de subir de versión.
12. **Registra la decisión** en `ESTADO.md`: plugin, SHA, fecha, quién lo revisó y qué componentes se aceptaron.

## Vacíos: dónde conviene una skill propia

1. **`python-test-quality`**: reglas contra tests vacíos para pytest. Prohíbe mocks del sistema bajo prueba; exige al menos una aserción sobre el comportamiento; obliga a "verlo fallar" en cada test nuevo; usa testcontainers o LocalStack en vez de mocks de boto3; fija la semilla de Hypothesis. Respaldo: estudio MSR 2026 sobre sobremocking, que pide justo "guidance on mocking practices in agent configuration files".
2. **`mutmut-gate`**: corre mutmut solo sobre los archivos del diff (`--paths-to-mutate`), lista sobrevivientes y pide al agente matar cada uno o justificar que es equivalente. Ningún plugin activo hace esto para mutmut; el de ToB usa mewt/muton.
3. **`python-supply-chain`**: una sola skill y un solo comando para `uv lock --check`, `exclude-newer`, `pip-audit`, `osv-scanner`, `gitleaks` y `zizmor`, con salida resumida. Las herramientas existen; falta la orquestación.
4. **`gha-claude-secure`**: plantilla endurecida de `claude-code-action` (SHA fijo, `permissions` mínimos, sin `pull_request_target`, allowlist de herramientas, `trigger_phrase` propio, zizmor en el mismo PR).
5. **`audit-plugin`**: automatiza la checklist de arriba (inventario, grep de patrones peligrosos, Unicode invisible, diff entre SHAs, agent-scan) y escribe el registro en `ESTADO.md`.
6. **AWS**: falta una skill que revise IAM de mínimo privilegio, IaC (checkov o cfn-lint) y secretos en Lambda/ECS. Coordinar con el investigador de DevOps/AWS.

## Fuentes

- Actividad y releases: `gh api` sobre cada repositorio citado (consultado 2026-11-07).
- Benchmark Propel (externo): http://www.propelcode.ai/benchmarks
- Martian Code Review Bench / CodeAnt: https://codeant.ai/blogs/ai-code-review-benchmark-results-from-200-000-real-pull-requests
- Macroscope, señal/ruido (2026-11-02): https://macroscope.com/content/ai-code-review-false-positives-signal-to-noise
- Signal65 (2026-03-27): https://signal65.com/wp-content/uploads/2026/03/Signal65-Insights_Evaluating-AI-Code-Review-Tools.pdf
- Crítica de benchmarks (2026-10-28): https://dev.to/dev_barron/best-ai-code-review-tools-by-false-positive-rate-what-the-benchmarks-actually-show-2e8l
- c-CRAB, arXiv 2603.23448: https://arxiv.org/html/2603.23448v2
- Postil, comparación basada en evidencia (2026-07-08): https://postil.dev/blog/best-ai-code-review-tools-2026
- Claude Code Review, configuración: https://support.claude.com/en/articles/14233555-set-up-code-review-for-claude-code
- Claude Code Review, GA y costos: https://cc.bruniaux.com/guide/workflows/code-review/ · https://repowise.dev/blog/comparisons/claude-code-review-pricing
- Superpowers 6.4 (evals del autor, 2026-09-21): https://blog.fsck.com/2026/09/21/superpowers-6.4/
- Caso de 415 issues con superpowers (2026-10-24): https://www.andrewconnell.com/articles/superpowers-workflow-415-issue-program
- Issues de superpowers: https://github.com/obra/superpowers/issues
- Anthropic, PBT con Claude (2026-01-14): https://www.anthropic.com/research/property-based-testing · arXiv 2510.09907: https://arxiv.org/abs/2510.09907
- PBT en Python con mutmut (ACM): https://dl.acm.org/doi/10.1145/3764068
- Sobremocking en agentes (MSR 2026): https://dl.acm.org/doi/10.1145/3793302.3793362
- MutGen, 100 % de cobertura con 4 % de mutation score: https://arxiv.org/abs/2506.02954
- Meta ACH, tests guiados por mutación: https://arxiv.org/abs/2501.12862
- Seguridad de plugins (docs oficiales): https://code.claude.com/docs/en/plugins/security
- Permisos y sandbox: https://code.claude.com/docs/en/permissions · https://code.claude.com/docs/en/sandboxing
- Red Hat, seguridad de plugins (2026-08-18): https://developers.redhat.com/articles/2026/08/18/securing-claude-code-plug-ins-best-practices-repository-security
- Datadog, skills maliciosas y contexto dinámico (2026-05-11): https://securitylabs.datadoghq.com/articles/malicious-skills-supply-chain-risks-in-coding-agents-with-dynamic-context/
- CSA, Poisoned Skills (2026-06): https://labs.cloudsecurityalliance.org/wp-content/uploads/2026/06/CSA_research_note_ai-skill-supply-chain-attacks_20260624-csa-styled.pdf
- Envenenamiento de skills, arXiv 2604.03081: https://arxiv.org/html/2604.03081
- Plugins como "el harness de otro" (2026-11-02): https://vanja.io/claude-code-plugins
- Escaneo de skills de Claude (Enterprise): https://support.claude.com/en/articles/15927065-get-started-with-skill-and-plugin-scanning
- NVIDIA SkillSpector: https://docs.nvidia.com/skills/scanning-agent-skills
- Auditorías de zizmor: https://docs.zizmor.sh/audits · OWASP GitHub Actions Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/GitHub_Actions_Security_Cheat_Sheet.html
- uv `exclude-newer`: https://docs.astral.sh/uv/concepts/resolution
- Incidentes en PyPI 2026: https://safedep.io/blog/mrmustard-malicious-pypi-package · https://www.sonatype.com/blog/compromised-litellm-pypi-package-delivers-multi-stage-credential-stealer
- README de security-guidance y claude-security: https://github.com/anthropics/claude-plugins-official/tree/main/plugins
- Semgrep Guardian: https://github.com/semgrep/guardian
- Trail of Bits skills: https://github.com/trailofbits/skills
