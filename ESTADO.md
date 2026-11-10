# Estado

## Dónde quedamos (2026-11-09)
Segunda revisión del kit, de solo lectura, con 15 hallazgos; Kevin dijo «dale» a todos y están aplicados en `main`, un
commit por arreglo (19 commits sobre v0.3.0, más este). **En GitHub desde el 2026-11-09**, con el CI en verde: run
42743919255, los 6 jobs, incluida la construcción de la imagen Docker de la prueba de humo, que en este Mac no se pudo
(el cliente docker de Homebrew no trae buildx y el Dockerfile usa `--mount`). Hecho:
- Errores confirmados: `[tool.typos]` ya no cuenta como ty configurado (verify.py y el hook de Stop comparan la
  cabecera de la tabla); barreras frena `git checkout .`, `git stash drop` y `git stash clear`; `claude-review.yml`
  comenta con el `GITHUB_TOKEN` del workflow (sin `github_token`, la acción cambiaba el OIDC por un token de la Claude
  GitHub App en api.anthropic.com y fallaba en una organización sin la App; verificado en action.yml y token.ts del
  commit fijado) y tiene `concurrency` por PR.
- El kit se aplica lo que exige: `pyproject.toml` con ruff (120 columnas, py39, sin C90/PLR09/T20/S/D, con el porqué),
  commit de solo formato en `.git-blame-ignore-revs`, 62 hallazgos arreglados sin cambiar comportamiento, job `estilo`
  en el CI; `dependabot.yml` propio (acciones y Claude Code del lockfile, cooldown 7 días);
  `bin/tests/test_versiones.py` ata uv, gitleaks, prek, ruff, los SHA de las acciones del kit y de las plantillas, y el
  lockfile de Claude Code; prek fijado (`uvx prek@0.5.9`) en todos los textos; `terceros/marketplace-entradas.json`
  borrado (marketplace.json es la única lista).
- Plantillas: `.python-version` (3.12) copiado por adoptar.py; un solo Dockerfile (la skill `dockerfile-python-uv`
  remite a la plantilla), `.dockerignore` con `tests/`, `.github/`, `.claude/`, y `humo_plantillas.py` construye la
  imagen y comprueba que no corre como root (sin Docker con BuildKit sale con 1; `--sin-docker` lo salta a propósito);
  deny `Edit(**/.claude/settings.json)` en la plantilla de settings.
- barreras: `rm -rf` de `.venv`, `dist`, `build`, `htmlcov`, `.tox`, `.nox`, `.coverage` y `*.egg-info` pasa (nombre
  exacto); autoprotección también de `.claude/settings.json` y `settings.local.json` (Edit/Write y Bash que escribe;
  leer, `git diff` y `git add` pasan; no se desactiva).
- Menores: línea `/plugin install <plugin> --marketplace Kevinbeltran123/kit-ingenieria-ia` en los 8 README (único
  aviso nuevo de `claude plugin validate` 2.1.319; quedan los 8 de `version`, decididos en B6); README de plantillas al
  día; `.impeccable/` fuera del kit; rama local `revision-2026-11-08` borrada.

Verificación local: 623 pruebas pasan y 14 se saltan sin OR-Tools (con OR-Tools 9.15, las 19 de optimización
también), `claude plugin validate .` pasa, `uvx ruff@0.17.3 check .` y `format --check .` limpios, zizmor sin
hallazgos en los workflows del kit y de las plantillas, prueba de humo 8/8 con `--sin-docker`. En GitHub, el job
`plantillas` construyó la imagen (9/9 pasos) y `estilo` pasó.

## Dónde quedamos (2026-11-08)
Revisión completa del kit en `investigacion/09-revision-2026-11-08.md` (~60 hallazgos agrupados en 48, con
evidencia y arreglo). Están hechos todos los arreglos NECESARIOS que no dependen de GitHub, un commit por arreglo:
los de código con pruebas que fallaban antes, los de contenido verificados contra la fuente (docs oficiales o
corriendo la librería). `main` los tiene (fast-forward desde la rama `revision-2026-11-08`) y está en GitHub, en
el repo https://github.com/Kevinbeltran123/kit-ingenieria-ia (subido el 2026-11-08; público desde ese día para
que GitHub Actions corra gratis). Las explicaciones de
los primeros arreglos están en `.explicaciones/commits/` (fuera de git). Hecho:
- Seguridad: A1 Python 3.9 y `onFailure`, A2 SCP, A3 regla `local` en barreras (borrados, `--no-verify`),
  A4 `Read(**/.env)`, A5–A6 sesión de AWS solo con el rol de lectura, A7 aws-core no se activa (proxy 1.7.0),
  A8 tfstate y `GetParameterHistory`, A9 Claude no se aprueba licencias, A11 torch ≥ 2.10, A12 `torch.hub.load`
  y descargas sin revisión, A13 MLflow registra ONNX.
- Bugs: B1 import-linter, B2 hook de Stop, B3 migraciones recién generadas, B4 splits contra el evaluador,
  B5 `adoptar.py` con GitHub, B7 splits sin imágenes, B8 vulture al 60 %, B9 mutantes sin rama base,
  B10 `suministro.py` no da OK sin revisar, B11 evaluador con `cwd`, `cd`, `bash -c` y worktrees, B12 licencias
  con `uvx`, `uv run --with`, PEP 723 y sin bloquear texto, B13 Pandera valida el DataFrame y no el LazyFrame.
- Contenido: C1 SageMaker SDK v3 (`ModelTrainer`), C2 moto por defecto y marcador `integration`, C3 escala ICA
  completa, C4 modelo elegido en validación e IC por lote, C5 paridad ONNX con el preprocesamiento de la Lambda,
  C6 CODEOWNERS en el perfil ml, C7 `terraform plan` en CI y lock nativo de S3, C8 detalles (scalene 2.x,
  structlog con la librería estándar, dlt `lag`, Alembic, HiGHS, licencias de RF-DETR/timm/DINOv3, MLflow App).
- Plantillas y verificación: E2 el CI corre pre-commit y gitleaks sobre la historia, E3 una sola versión de
  ruff/complexipy y uv fijado en CI, E4 verify revisa el lock y no da OK sin herramientas, E6 barreras con
  `timeout -s/-k` y `.envrc`.
- Terceros: AUDITORIA.md corregida (D1, D4); quitados hf-cloud-sagemaker, react-best-practices y plugin-dev (D2, D3).
- Nuevo: plugin `explicador` (vista B, línea por línea, exigido antes de `gh pr create`; `--commit` para un
  commit puntual). Es para el código de la empresa; en el kit no se generan explicaciones.

Verificación: 577 pruebas pasan, en Python 3.9 y 3.12 (con OR-Tools 9.15 también las 14 de optimización), cada
commit pasa todas las suites por sí solo, la prueba de humo de las plantillas pasa (8/8 pasos) y
`claude plugin validate .` pasa (con un aviso por plugin, que sugiere `version`: ver B6).

Con el kit en GitHub (2026-11-08) también quedaron hechos:
- E1: CI del kit en `.github/workflows/ci.yml` (pruebas en 3.9 y 3.12, validación, prueba de humo
  `bin/humo_plantillas.py` y zizmor). Cada job se probó en local con sus mismos comandos; en GitHub corre desde que
  el repo es público (ver Pendiente 1), y el primer run pasó entero: los 5 jobs en verde, con las suites en 3.9
  y 3.12 (más las 19 de OR-Tools) y la prueba de humo 8/8 en el runner nuevo (Ubuntu con Python 3.14).
- A10: la revisión en CI instala `pr-review-toolkit` desde el commit auditado, con un marketplace propio que
  arma el workflow (una copia local del oficial no sirve: Claude Code reserva su nombre).
- B6: los plugins propios no llevan `version`; las entregas son tags (`v0.2.0` es la primera; `v0.3.0`, del 2026-11-08, trae lo de gentle-factory y pstack).
- Pins con menos de 7 días corregidos: uv 0.13.6 y zizmor 1.31.1.

## Siguiente
1. Hallazgos nuevos de la revisión:
   - Hecho (Kevin dijo «dale»): `evaluador_bloqueado` protege su propia configuración `.claude/ml-vision.json`
     (antes el agente podía vaciar `rutas_protegidas` y después escribir en `eval/`). Límite documentado: no ve
     comandos sobre la carpeta entera (`mv .claude otra`); eso lo frena el CODEOWNERS en el PR.
   - Hecho (2026-11-08, ver abajo): `licencias.py` revisa Dockerfiles y Containerfiles, sus `RUN` y la imagen de
     `FROM` (718fe4f).
2. Ideas de gentle-factory y pstack (revisadas el 2026-11-08; Kevin aprobó las 3 primeras con «si, dale»):
   - Hecho: el hook de Stop no da por revisado lo que no pudo correr (ae8b00e). `no_silenciar.py`: solo la persona
     agrega `# noqa`, `# type: ignore`, `# pragma: no cover` y similares, y Claude no corre `ruff --add-noqa` ni
     `ty --add-ignore` (42ff91f; probado con Claude Code 2.1.319 real). Plantillas con FBT001/FBT002,
     `acyclic_siblings` y el anti-patrón "fijar una constante" (015b345; probado al derecho y al revés).
   - Decidido el 2026-11-08 (Kevin: «Escoge las mejores alternativas desde un punto de vista objetivo»), con la
     evidencia de cada una:
     - 4) De pstack: `/correct` y la pregunta del estado legítimo en `flujo` (f8d63a3), y las 7 preguntas de
       benchmark en `rendimiento-python` (512d88e). No: create- y maintain-verification-skill (Claude Code 2.1.319 ya
       trae `/run-skill-generator` y `/run`), blast-radius (lo cubre `differential-review` y depende de 4 skills de
       pstack) y las otras dos ideas (ya estaban en `calidad-pruebas` e `ingesta-idempotente`).
     - 5) Checklist de revisión: no por ahora. *Software Engineering at Google* es CC BY-NC-ND (58 de las 107
       preguntas no se pueden publicar ni usar en un kit de empresa), la automatización de gentle-factory es de
       ESLint y nadie midió el efecto. Se retoma si la revisión en PRs reales de la empresa sale ruidosa: "citar o
       marcar como opinión" con un catálogo cerrado de eng-practices (CC BY 3.0) y ASVS (CC BY-SA 4.0).
     - 6) Gate solo de lo nuevo: no se construye. Cada herramienta trae su línea base; el README («Si el repo ya
       tiene código») las explica, probadas con ruff 0.17.3, ty 0.0.95 y complexipy 8.3.0 (eef1007).
     - Extra: Claude tampoco salta pruebas (skip, xfail, `SkipTest`, salir en verde); un `skipif` nuevo se le
       pregunta a la persona (0812aa2, probado con Claude Code real).
     - `.impeccable/config.json` versionado, como pide impeccable (e749b61). Quitado el 2026-11-09: es una herramienta
       local, no parte del kit (queda `.impeccable/` en .gitignore).

## Pendiente que decide Kevin
1. Resuelto el 2026-11-08: el repo pasó a público, así Actions corre gratis (Kevin no va a pagar más). Si vuelve a
   ser privado, el CI deja de correr hasta que la cuenta tenga minutos ("recent account payments have failed or
   your spending limit needs to be increased").
2. Limpieza de lo instalado en global (`~/.claude`): quitar/reemplazar software-architecture, write-concisely,
   code-simplifier, review-local-changes, commit, create-pr, playwright-skill, ui-ux-pro-max, antislop;
   security-guidance de global a proyecto; context7 en modo CLI y versión parcheada (CVE-2026-75130).
3. Resuelto el 2026-11-08: uv local en 0.13.6, la misma del CI y de la plantilla (es el de miniconda, instalado con
   pip y primero en el PATH; el de Homebrew, 0.13.7, queda detrás). Con él pasa la prueba de humo (8/8).
4. Datos de la empresa: orquestador de datos, Terraform vs CDK, monitoreo, gestor de tareas, framework web.
5. Skills no construidas aún: `geo-raster-agro`, CLAUDE.md del equipo de datos, observabilidad de ML (drift).
6. EXTRA de la revisión sin hacer: D5 (aws-core cuesta ~4.900 tokens fijos), D6 (solapes entre skills), F2 (skills
   según el stack de la empresa).
7. Resuelto el 2026-11-09: push hecho y CI en verde (run 42743919255), con el `docker build` de la prueba de humo y el
   job `estilo`. Dependabot abrirá sus primeros PR cuando toque (semanal, cooldown 7 días).
8. Al subir ty (fijado en 0.0.95; la última es 0.0.99): 0.0.97 renombró `unresolved-import` a `import-not-found`
   (changelog de ty). Revisar los `# ty: ignore[...]` y regenerar las líneas base con `--update-baseline`.

## Decisiones
- Stack empresa: casi todo Python, GitHub, AWS. Sin política de IA.
- Alcance: marketplace propio, instalar por repo, nada global.
- Superpowers: opción B (5 skills copiadas, fijadas por SHA; executing-plans fuera porque depende de partes no copiadas).
- Excluido de terceros: web-design-guidelines de Vercel (descarga instrucciones sin fijar en cada uso).
- Sin atribución a Claude en commits/PR (plantilla settings.json).
- Explicador (2026-11-08): vista B (código y terminal lado a lado), una nota por cada línea cambiada, HTML local
  fuera de git (`.explicaciones/`, vía `.git/info/exclude`), se exige al abrir PR. Fuente única IBM Plex Mono incrustada.
- Hooks y scripts: compatibles con Python 3.9; las barreras fallan cerrado también si el hook no arranca.
- El hook global `~/.claude/hooks/block-destructive-bash.py` se queda: `barreras` solo actúa en los repos que
  adoptan el kit.
- Lo no revisado no cuenta como OK: los scripts de verificación (`suministro.py`, `verify.py`,
  `verificar_division.py`) salen con un código distinto de 0 si una herramienta falta o no hubo nada que revisar.
  El hook de Stop, igual: una herramienta configurada que no está instalada bloquea como sin revisar.
- Las excepciones a las reglas (`# noqa` y similares) solo las agrega la persona: Claude explica el falso positivo
  y dice cuál y dónde (hook `no_silenciar`). Para una línea base en un repo viejo, `CALIDAD_PYTHON_PERMITIR_SILENCIAR=1`.
- FBT003 fuera de la plantilla: marca APIs de terceros (`model.train(False)`), y FBT001 ya cubre el código propio.
- De otros proyectos se toma solo lo que el kit y Claude Code no traen ya (pstack: `/correct`, el estado legítimo,
  las preguntas de benchmark). Repos con código viejo: la línea base de cada herramienta, no un gate propio.
  Nada de *Software Engineering at Google* en el kit (CC BY-NC-ND).
- El kit se aplica sus propias reglas (2026-11-09): ruff con `pyproject.toml` en la raíz, 120 columnas y sin las
  familias que no tienen sentido en hooks (T20, S, D, FAST, TID) ni las de complejidad (C90, PLR09: los hooks que
  analizan shell concentran ramas por diseño y los cubren sus pruebas). Las excepciones van en la configuración, no
  en `# noqa`. Los commits de solo formato, en `.git-blame-ignore-revs`.
- La revisión con Claude en CI usa el `GITHUB_TOKEN` del workflow, no la Claude GitHub App (menos piezas externas; la
  App exige instalarla en la organización). Si se quiere la App: quitar `github_token` y devolver `id-token: write`.
- Una versión repetida en varios sitios se ata con una prueba (`test_versiones.py`), no con un comentario.
- Lo que no es del kit (herramientas locales como impeccable) no se versiona en el kit.
