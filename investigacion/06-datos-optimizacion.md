# 06 — Ingeniería de datos, bases de datos, optimización y geoespacial

Investigación del 2026-11-07. Criterio de "activo": commits en la rama principal desde ~2026-09-25. Fechas tomadas con `gh api` (commits/releases), PyPI, npm y Docker Hub el mismo día. Nada se instaló ni se configuró.

## Hallazgos clave

1. **Los fabricantes ya publican sus propios plugins de Claude Code**: dbt, Dagster, Astronomer (Airflow), dltHub, Polars, MotherDuck y AWS (aws-data-analytics). Están activos y se instalan desde un marketplace, así que se pueden instalar **por repo** y solo donde la empresa use esa herramienta.
2. **El propio dbt Labs midió que los skills genéricos aportan poco con los modelos actuales.** En su eval del 2026-10-30, los proyectos de Claude 5.5 con y sin skills sacaron 3,9–4,7 y las diferencias cayeron dentro del ruido del revisor. Su conclusión: un skill que escriba *cómo trabaja tu equipo* (pruebas, despliegue, revisión) rinde más que uno que explique la herramienta. Vercel encontró algo parecido: un índice en AGENTS.md dio 100 % y el skill 79 %, porque en el 56 % de los casos el skill nunca se invocó. **Consecuencia para el kit:** instalar pocos skills de fabricante y poner el esfuerzo en skills propios del equipo y del dominio, más reglas siempre activas en CLAUDE.md.
3. **No existe nada mantenido para optimización con OR-Tools, Pyomo, PuLP, HiGHS ni CVXPY.** Lo único oficial es el MCP de Gurobi, que es experimental, exige una cuenta del Intelligence Hub y envía los modelos a la nube de Gurobi. Este es el vacío más grande y el más valioso para el trabajo en palma.
4. **Postgres:** el servidor de referencia de Anthropic está archivado y el popular `crystaldba/postgres-mcp` (3,4k★) está **inactivo** (último push el 2026-08-17; en PyPI, la 0.3.0 es de mayo de 2025). AWS avisa que su modo "solo lectura" es de mejor esfuerzo. **La única barrera real es un rol de base de datos de solo lectura.**
5. **Para palma de aceite no apareció ningún skill ni MCP específico.** En geoespacial hay opciones sueltas, casi todas de un solo autor.

## Tabla de evaluación

Leyenda de veredicto: **Adoptar** · **Condicional** (solo si la empresa usa esa herramienta) · **Observar** · **Referencia** (copiar ideas, no instalar) · **Descartar**.

### 1. Ingesta y pipelines

| Nombre | Tipo | Qué hace | Último commit / release | Evidencia | Riesgo | Veredicto |
|---|---|---|---|---|---|---|
| `dlt-hub/dlthub-ai-harness` (antes ai-workbench) | Toolkits (skills + reglas + MCP `dlt-workspace-mcp`) | Ingesta REST/SQL, calidad de datos, transformaciones y despliegue con dlt. Su skill `setup-secrets` está hecho para que el agente no lea secretos | commit 2026-11-04 (sin releases) | Documentación oficial de dltHub ([intro](https://dlthub.com/docs/hub/ai-harness/introduction), [toolkits](https://dlthub.com/docs/hub/ai-harness/toolkits)). 65★, proyecto joven | Medio: el plugin de Claude Code está en "Early Access"; recomiendan usar el CLI `uvx dlthub-init`, que escribe `.mcp.json` y `.claude/skills`. Parte del flujo empuja hacia la plataforma de pago de dltHub | **Adoptar para el repo de ingesta** si se elige dlt. Solo los toolkits `rest-api-pipeline`/`sql-database` |
| `dlt-hub/dlt-mcp` | MCP | Inspecciona pipelines, esquemas y SQL SELECT | último push 2026-02-19 | — | — | **Descartar** (inactivo; lo reemplaza el harness) |
| `dbt-labs/dbt-agent-skills` | Plugin (skills) | Modelos, pruebas, semantic layer, Mesh, migraciones | commit 2026-10-21; 757★ | Blog oficial ([2026-02-05](https://docs.getdbt.com/blog/dbt-agent-skills)); su propia eval que relativiza el valor ([2026-10-30](https://docs.getdbt.com/blog/do-coding-agents-still-need-dbt-skills)) | Bajo (solo texto) | **Condicional** (solo si se usa dbt) |
| `dbt-labs/dbt-mcp` | MCP | CLI de dbt, linaje, semantic layer, Discovery API | v2.10.1 2026-11-03 | Oficial, releases semanales | Medio: puede ejecutar comandos dbt y SQL; las herramientas se desactivan con variables de entorno | **Condicional** |
| `AltimateAI/data-engineering-skills` | Plugin | Skills de dbt y Snowflake | commit 2026-10-27; 135★ | ADE-bench: 46,5 % → 53,5 % con Sonnet 4.5 ([blog 2026-01-22](https://altimate.ai/blog/teaching-claude-code-the-art-of-data-engineering-introducing-altimate-skills)) | Bajo | **Condicional** (solo dbt + Snowflake) |
| `dagster-io/skills` | Plugin (skill `dagster-expert` + MCP Dagster+) | Escribir assets y jobs, con el CLI `dg` como verificación determinista | v1.13.29 2026-11-05 | [Docs oficiales](https://dagster.io/docs/getting-started/ai-tools/plugin); framework propio de evals ([blog](https://dagster.io/blog/evaluating-agent-skills)) | Medio: el MCP es de Dagster+ (nube) y actúa con los permisos de tu usuario. El plugin `dagster-expert` está obsoleto desde el 2026-09-14 | **Condicional** (Dagster) |
| `astronomer/agents` (`astronomer-data`) | Plugin (22+ skills + MCP Airflow + CLI `af`) | Escribir y depurar DAGs, linaje, migrar de Airflow 2 a 3 | commit 2026-10-29; MCP 0.9.1 2026-07-08 | En el [directorio de Claude](https://claude.com/plugins/astronomer-data-agents), 2.311 instalaciones | Medio: el MCP dispara DAGs; hay que limitarlo con permisos de la API de Airflow | **Condicional** (Airflow/MWAA) |
| `PrefectHQ/prefect-mcp-server` | MCP | Inspeccionar despliegues y ejecuciones de Prefect | último commit en main 2026-09-23; 0.0.1-beta.13 2026-09-01 | Oficial, pero en beta | Medio | **Observar** (en el borde de la ventana y en beta) |
| `polars-inc/skills` | Plugin (skill `polars`) | API perezosa por defecto, expresiones nativas, Polars 2.0 | commit 2026-10-26 (v0.4.0) | Oficial de Polars ([repo](https://github.com/polars-inc/skills)) | Bajo; contexto pequeño | **Adoptar** si el equipo usa Polars |
| `polars-mcp` (PyPI) | MCP | Consulta la API instalada (docstrings) | 0.2.1 2026-01-13 | Complemento del skill | Bajo | **Descartar** (context7 ya cubre esto) |
| `motherduckdb/mcp-server-motherduck` | MCP | Consultas DuckDB/MotherDuck (también DuckDB local) | v1.1.0 2026-10-07 | Oficial; 540★ | Medio: confirmar que arranque en modo solo lectura antes de usarlo | **Observar** (útil para explorar Parquet localmente) |
| `motherduckdb/agent-skills` | Plugin (21 skills) | Skills de MotherDuck y SQL de DuckDB | push 2026-10-25 | Oficial | Bajo; muy centrado en MotherDuck | **Descartar** salvo que se use MotherDuck |
| `aws/agent-toolkit-for-aws` → plugin `aws-data-analytics` | Plugin (skills + AWS MCP Server) | Tablas Iceberg en S3 Tables, ingesta, Athena, Glue Data Catalog, conexiones Glue/JDBC | carpeta del plugin con commits el 2026-10-26; repo el 2026-11-06 | Oficial de AWS y en `claude-plugins-official` ([docs](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/plugins.html)) | **Alto si hay credenciales con escritura.** Usar un perfil AWS de solo lectura en desarrollo | **Adoptar** (el stack de la empresa es AWS), con perfil restringido |
| `awslabs` `aws-dataprocessing-mcp-server` | MCP | Glue, EMR y Athena; Athena solo SELECT salvo `--allow-write` | 0.2.2 2026-09-22 | [Docs](https://awslabs.github.io/mcp/servers/aws-dataprocessing-mcp-server) | Medio; expone muchas herramientas, lo que cuesta contexto | **Observar** (se solapa con el AWS MCP Server del toolkit) |
| Soda MCP (`soda-mcp`) | MCP | Contratos, checks e incidentes de Soda Cloud | docs vigentes; no está en PyPI público | [Docs Soda](https://docs.soda.io/soda-ai/soda-mcp) | Exige Soda Cloud (de pago) y tiene mucha superficie, incluida la gestión de secretos | **Descartar** salvo que la empresa use Soda Cloud |
| Great Expectations | Librería | Validación de datos | el repo ahora es `fivetran/great_expectations`, push 2026-11-06 | No encontré un MCP ni un skill oficial mantenido | — | Solo la librería |
| Pandera (`unionai-oss/pandera`) | Librería | Contratos de DataFrame (pandas/Polars) en Python | push 2026-11-06 | Sin skill oficial | — | **Librería recomendada; falta un skill propio** |
| `anthropics/knowledge-work-plugins` → `data` | Plugin | Analista: SQL, exploración y `validate-data` (lista de QA antes de entregar) | repo 2026-11-07 | Oficial de Anthropic; pensado para Cowork | Bajo, pero orientado a análisis y no a ingeniería | **Referencia** (copiar la lista de validación) |

### 2. Bases de datos

| Nombre | Tipo | Qué hace | Último commit / release | Evidencia | Riesgo | Veredicto |
|---|---|---|---|---|---|---|
| `googleapis/mcp-toolbox` (MCP Toolbox for Databases) | MCP | Herramientas SQL **curadas en YAML** (consultas parametrizadas); soporta Postgres, AlloyDB, etc. | v1.16.0 2026-11-05 | 16,8k★; Google; releases quincenales | **El más bajo de todos para producción:** el agente solo ejecuta las consultas que tú definiste | **Adoptar para producción** (patrón de consultas curadas) |
| `microsoft/postgres-mcp` | MCP (npm) | Consulta, esquema y diagnóstico; `postgres_mcp_query` es de solo lectura; perfiles `access_mode: ro`; quita secretos de los errores | v0.3.0 2026-10-22; commit 2026-11-05 | [README](https://github.com/microsoft/postgres-mcp/blob/main/README.md) con un modelo de seguridad explícito | Medio: está en "Preview" y los perfiles permiten escribir si no pones `ro` | **Adoptar para dev/staging** con perfil `ro` y rol de solo lectura |
| `awslabs` `postgres-mcp-server` | MCP | Aurora/RDS Postgres vía Data API o pgwire | 1.2.3 2026-10-30 | [Docs AWS](https://awslabs.github.io/mcp/servers/postgres-mcp-server): "read-only enforcement is best effort"; recomiendan `--privilege_check enforce` | Medio | **Condicional** (si la base es Aurora/RDS): sin `--allow_write_query` y con un rol que solo tenga SELECT |
| `YawLabs/postgres-mcp` | MCP | Solo lectura por defecto (`BEGIN READ ONLY`), `application_name` para auditoría | v0.13.10 2026-10-31 | 10★, un solo mantenedor | Medio (poca comunidad) | **Observar** |
| `crystaldba/postgres-mcp` (Postgres MCP Pro) | MCP | Ajuste de índices y salud de la base | push 2026-08-17; PyPI 0.3.0 2025-05-16 | 3,4k★ pero sin actividad | Paquete sin mantener | **Descartar** |
| `supabase/agent-skills` → `supabase-postgres-best-practices` (ya instalado) | Skill | 8 categorías de reglas (consultas, conexiones, seguridad/RLS, esquema, locks…) en 34 archivos de referencia | release v0.1.9 2026-09-28; commit 2026-10-02 | Oficial de Supabase; 3k★; SKILL.md de unos 3 KB con carga progresiva | Bajo; contexto pequeño | **Mantener.** Sirve para cualquier Postgres, pero **no cubre Alembic ni SQLAlchemy 2** y el contenido de RLS es muy de Supabase |
| `bm629/agent-skills` (alembic, sqlalchemy) | Skills | Alembic multi-dialecto, migraciones en modo batch, ORM tipado 2.x | commit 2026-10-31 | 6★, sin aval de expertos | Bajo | **Referencia** para escribir el skill propio |

### 3. Optimización / investigación de operaciones

| Nombre | Tipo | Qué hace | Último commit / release | Evidencia | Riesgo | Veredicto |
|---|---|---|---|---|---|---|
| Gurobi Intelligence Hub — MCP local (`gurobi/mcp`) | MCP (Docker) | Expone Gurobot, Explainer (infactibilidad, restauración, sensibilidad) y Modeler (especificación → formulación → gurobipy → pruebas unitarias) | imagen Docker 1.0.0 del 2026-11-07 | [Docs MCP](https://docs.gurobi.com/projects/intelligence/en/current/mcp-server.html), [FAQ](https://www.gurobi.com/resources/faq/gurobi-intelligence-hub), [Help Center 2026-09-24](https://support.gurobi.com/hc/en-us/articles/36441000626449-Gurobi-AI-Modeling-Tools) | **Alto en datos:** los modelos se envían al backend de Gurobi; es "experimental"; límite de 2M tokens/día; requiere licencia y API key | **Condicional** (solo si la empresa ya licencia Gurobi y aprueba compartir los modelos) |
| Guía "Testing" de gurobi-ai-modeling | Documentación | Lista para validar modelos hechos con LLM: objetivo plausible, código verificador de factibilidad, casos borde (todo en 0, cotas) | vigente | [gurobi-ai-modeling.readthedocs.io](https://gurobi-ai-modeling.readthedocs.io/en/latest/eval-testing.html) | — | **Referencia** para el skill propio |
| `optuna/optuna-mcp` | MCP | Optimización de hiperparámetros dirigida por el LLM y dashboard | v0.2.0 2025-11-10; commit de CI 2026-10-22 | Oficial de Optuna | Bajo | **Observar / opcional** (útil para afinar modelos de reconocimiento; no es investigación de operaciones) |
| OR-Tools, Pyomo, PuLP, HiGHS, CVXPY | Librerías | Solvers y modelado | todas con push entre el 2026-11-03 y el 2026-11-07 | Muy activas | — | **Sin skills ni MCP mantenidos → skill propio + context7 para la documentación** |
| `K-Dense-AI/scientific-agent-skills` | Plugin (177 skills) | Incluye `pymoo`, `geopandas`, `polars`, `dask`, `geomaster` | v2.72.0 2026-10-01; commits recientes solo del escaneo de seguridad | 56k★ | **Costo de contexto alto si se instala completo**, y está orientado a biología | **Referencia** (copiar 1 o 2 skills a mano, no instalar el plugin) |
| Literatura LLM → modelos de OR | Investigación | NEMO: simulador independiente y pruebas pytest; ORPilot (2026-08): IR determinista que compila a Gurobi/PuLP/Pyomo/OR-Tools; OptiSkill (EMNLP 2026): banco de skills de modelado | 2026 | [NEMO](https://arxiv.org/html/2601.21372v3), [ORPilot](https://arxiv.org/html/2605.02728v1), [OptiSkill](https://aclanthology.org/2026.emnlp-main.1316.pdf), [SemOPT](https://aclanthology.org/2026.findings-emnlp.185.pdf) | — | **Referencia**: la validación asimétrica (un verificador independiente del modelo) es el patrón con mejor evidencia |

### 4. Geoespacial / agro

| Nombre | Tipo | Qué hace | Último commit / release | Evidencia | Riesgo | Veredicto |
|---|---|---|---|---|---|---|
| `jaakla/openmapstack-skills` (antes open-gis) | Skill | Stack GIS abierto: STAC, COG, GeoParquet, DuckDB/PostGIS, CRS, validación | v0.5.0 2026-10-28 | 78★, un solo autor | Bajo; trae analítica (PostHog) en su página web, no en el skill | **Observar / referencia** |
| `sparkgeo/geo-mcp-servers` | Catálogo + skill | 114 MCP geoespaciales con chequeo de salud | revisado el 2026-11-03 | Sparkgeo (consultora geo) | Bajo | **Referencia** (para buscar cuando haga falta) |
| `opengeos/GeoAgent` | Framework de agente (Strands) | Agente para leafmap/QGIS/STAC | push 2026-11-04; 534★ | Qiusheng Wu (opengeos, referente en geo con Python) | No es un plugin de Claude Code | **Referencia** |
| `BnJam/stac-mcp` | MCP | Búsqueda en catálogos STAC | último commit 2026-08-07 | 20★ | — | **Descartar** (fuera de la ventana) |
| `eo-mcp/eo-mcp` | MCP | Flujos STAC y sandbox de Python arbitrario | push 2026-10-20 | 16★ | **Alto**: ejecuta código arbitrario | **Descartar** |
| `opengeos/geoai-skills`, `JordanGunn/gdal-mcp`, `isaaccorley/planetary-computer-mcp`, `IBM/chuk-mcp-stac` | Varios | — | marzo, mayo, abril y archivado, respectivamente | — | — | **Descartar** (inactivos o archivados) |
| pystac, rasterio, geopandas | Librerías | STAC, ráster, vector | push entre el 2026-10-31 y el 2026-11-05 | Muy activas | — | Solo las librerías |

## Seguridad: acceso a bases de datos de producción

1. **La base de datos es la frontera, no el MCP.** Microsoft, YawLabs y AWS dicen lo mismo: crear un rol `LOGIN` con `CONNECT` + `USAGE` + `SELECT` (o `pg_read_all_data`) y `default_transaction_read_only = on`. El MCP se conecta con ese rol y nunca con el de la aplicación.
2. **En producción, consultas curadas** (MCP Toolbox con herramientas YAML parametrizadas) en lugar de SQL libre. En dev/staging se permite SQL libre con perfil `ro`.
3. Poner `application_name` y `statement_timeout` en la conexión, para que el tráfico del agente se vea en `pg_stat_activity` y no tumbe la base.
4. Cargar las credenciales desde variables de entorno o un gestor de secretos, nunca en `.mcp.json` versionado. El patrón del skill `setup-secrets` de dlt (el agente nunca lee los secretos) es bueno para copiar.
5. En AWS, usar un perfil de solo lectura para los MCP y skills, y dejar `--allow-write` / `--allow_write_query` desactivados.
6. Gurobi MCP envía los archivos de modelo a su backend. Antes de usarlo con datos reales de plantación o de costos hay que pedir aprobación interna.

## Costo de contexto

- Los skills cuestan poco hasta que se usan: solo se carga la descripción. Los MCP cargan sus esquemas de herramientas al iniciar; los de muchas herramientas (Soda, awslabs dataprocessing, Dagster+) son los más caros.
- K-Dense (177 skills) y el plugin completo de Astronomer (22+) inflan la lista de skills. Conviene instalarlos solo en el repo que los necesita.
- Por la eval de dbt y la de Vercel: las reglas críticas deben ir en un CLAUDE.md corto y siempre activo, no en skills que quizá no se disparen.

## Stack recomendado de ingesta

Supuesto: Python + AWS, y todavía no sé qué orquestador usa la empresa. Hay que confirmarlo el primer día.

| Capa | Elección | Por qué |
|---|---|---|
| Extracción y carga | **dlt** (+ toolkits del harness en el repo de ingesta) | Esquema inferido y versionado, cargas incrementales, `merge` con claves primarias (idempotencia), skills oficiales activos |
| Transformación | **Polars** (perezoso) y **DuckDB** para SQL sobre Parquet | Rápidos en local; skill oficial de Polars |
| Contratos de datos | **Pandera** (DataFrames) + **Pydantic v2** (registros y API en el borde) | Contratos en Python, probables en pytest |
| Almacenamiento analítico | **S3 + Iceberg (S3 Tables) + Glue Catalog + Athena** | Nativo de AWS; cubierto por el plugin oficial `aws-data-analytics` |
| Base operacional | **Postgres** con **SQLAlchemy 2** (tipado `Mapped[]`) + **Alembic** | Estándar; skill de Supabase ya instalado |
| Orquestación | Lo que use la empresa. Si no hay nada: **Dagster** (assets, linaje y el `dg` para verificar) | El plugin de Dagster tiene la mejor evidencia de evals entre los orquestadores |
| Optimización | **OR-Tools (CP-SAT)** para asignación y rutas; **HiGHS** vía Pyomo o PuLP para LP/MILP; Gurobi solo si hay licencia | Libres, activos y con buen rendimiento |
| Geoespacial | **rasterio + geopandas + pystac / pystac-client**, COG y GeoParquet | Librerías activas |

Plugins para instalar por repo (sin global), en orden: `aws-data-analytics`, `polars`, el toolkit de dlt (solo en el repo de ingesta), un MCP de Postgres (Toolbox en producción, microsoft/postgres-mcp con `ro` en desarrollo). El plugin del orquestador va solo cuando se confirme cuál usa la empresa.

## Vacíos para skills propios del kit (prioridad)

1. **`formular-modelo-optimizacion`** (el más importante). Sigue un flujo fijo; las fuentes de cada paso son Gurobi Modeler/Testing, NEMO, ORPilot y SemOPT:
   1. Especificación en lenguaje natural con conjuntos, parámetros, variables, restricciones y objetivo.
   2. **Tabla de unidades y dimensiones** de cada parámetro (ha, t RFF, jornales, km, horas).
   3. Instancia mínima resoluble a mano, con su óptimo conocido.
   4. **Verificador de factibilidad independiente del modelo**: código aparte que comprueba la solución contra las reglas del negocio.
   5. Casos borde: todo en 0, cotas al máximo, una instancia infactible a propósito que el modelo debe detectar (IIS o `feasRelax`).
   6. Pruebas pytest de regresión y un análisis de sensibilidad.
   7. Escalado gradual del tamaño de la instancia, con límites de tiempo y gap registrados.

   Plantillas para palma: ciclos y rondas de cosecha por lote, asignación de cuadrillas (CP-SAT) y rutas de recolección (VRP con OR-Tools). Los parámetros agronómicos (frecuencia de ronda, rendimientos) **los debe validar la empresa**; no los tengo verificados.
2. **`ingesta-idempotente`**: claves naturales y `merge`/upsert, marcas de agua (watermarks), reprocesos seguros, particionado por fecha de carga, cuarentena de filas inválidas y linaje mínimo (fuente, hora, versión del esquema). Se puede montar sobre dlt.
3. **`contratos-datos-pandera`**: ningún fabricante tiene un skill para esto. Esquemas Pandera y Pydantic versionados junto al código, pruebas con datos sintéticos (hypothesis) y fallo en CI.
4. **`migraciones-alembic-sqlalchemy2`**: revisar siempre el autogenerate (no detecta cambios de enums ni ciertos índices), separar los cambios de esquema de los de datos, migraciones reversibles, `CREATE INDEX CONCURRENTLY` y prueba de upgrade y downgrade en CI. Complementa el skill de Supabase. Referencia: bm629/agent-skills.
5. **Hook o guardia de SQL en producción**: un PreToolUse que bloquee DDL y DML cuando la conexión apunte a producción, y exija el rol de solo lectura. Coordinarlo con el investigador de harnesses.
6. **`geo-raster-agro`**: CRS (MAGNA-SIRGAS / CTM12 para Colombia, por confirmar), COG y teselado para imágenes de dron, STAC para Sentinel-2 y el puente con el modelo de reconocimiento (conteo y detección de palmas). Ningún skill mantenido cubre esto.
7. **CLAUDE.md del equipo de datos**: convenciones de nombres, capas (raw/staging/marts), cómo se prueba y despliega. Es lo que dbt Labs concluye que más rinde.

## Fuentes

- dbt: https://docs.getdbt.com/blog/do-coding-agents-still-need-dbt-skills (2026-10-30) · https://docs.getdbt.com/blog/dbt-agent-skills (2026-02-05) · https://github.com/dbt-labs/dbt-agent-skills · https://github.com/dbt-labs/dbt-mcp · https://www.getdbt.com/blog/ade-bench-dbt-data-benchmarking
- Vercel, AGENTS.md vs skills: https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals (2026-01-27)
- Altimate: https://altimate.ai/blog/teaching-claude-code-the-art-of-data-engineering-introducing-altimate-skills · https://github.com/AltimateAI/data-engineering-skills
- Dagster: https://github.com/dagster-io/skills · https://dagster.io/docs/getting-started/ai-tools/plugin · https://dagster.io/blog/evaluating-agent-skills
- Astronomer: https://github.com/astronomer/agents · https://claude.com/plugins/astronomer-data-agents
- dltHub: https://dlthub.com/docs/hub/ai-harness/introduction · https://dlthub.com/docs/hub/ai-harness/installation · https://dlthub.com/docs/hub/ai-harness/toolkits · https://github.com/dlt-hub/dlthub-ai-workbench
- Polars: https://github.com/polars-inc/skills
- MotherDuck: https://github.com/motherduckdb/mcp-server-motherduck · https://github.com/motherduckdb/agent-skills
- Prefect: https://github.com/PrefectHQ/prefect-mcp-server
- AWS: https://github.com/aws/agent-toolkit-for-aws/tree/main/plugins/aws-data-analytics · https://docs.aws.amazon.com/agent-toolkit/latest/userguide/plugins.html · https://awslabs.github.io/mcp/servers/aws-dataprocessing-mcp-server · https://awslabs.github.io/mcp/servers/postgres-mcp-server · https://pypi.org/project/awslabs.postgres-mcp-server/1.2.3
- Soda: https://docs.soda.io/soda-ai/soda-mcp
- Anthropic data plugin: https://github.com/anthropics/knowledge-work-plugins/tree/main/data
- Postgres MCP: https://github.com/googleapis/mcp-toolbox · https://github.com/microsoft/postgres-mcp/blob/main/README.md · https://github.com/YawLabs/postgres-mcp · https://github.com/crystaldba/postgres-mcp
- Supabase skill: https://github.com/supabase/agent-skills
- Alembic/SQLAlchemy (comunidad): https://github.com/bm629/agent-skills
- Gurobi: https://docs.gurobi.com/projects/intelligence/en/current/mcp-server.html · https://www.gurobi.com/resources/faq/gurobi-intelligence-hub · https://support.gurobi.com/hc/en-us/articles/36441000626449-Gurobi-AI-Modeling-Tools · https://gurobi-ai-modeling.readthedocs.io/en/latest/eval-testing.html · https://hub.docker.com/r/gurobi/mcp
- Optuna MCP: https://github.com/optuna/optuna-mcp
- Investigación LLM + OR: https://arxiv.org/html/2601.21372v3 (NEMO) · https://arxiv.org/html/2605.02728v1 (ORPilot) · https://aclanthology.org/2026.emnlp-main.1316.pdf (OptiSkill) · https://aclanthology.org/2026.findings-emnlp.185.pdf (SemOPT) · https://arxiv.org/html/2602.22465v2 (ConstraintBench)
- Geo: https://github.com/sparkgeo/geo-mcp-servers · https://github.com/jaakla/open-gis · https://github.com/opengeos/GeoAgent · https://github.com/wayfinder-foundry/stac-mcp · https://github.com/eo-mcp/eo-mcp.github.io
- K-Dense: https://github.com/K-Dense-AI/scientific-agent-skills
