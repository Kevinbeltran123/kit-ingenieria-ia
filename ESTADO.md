# Estado

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

Verificación: 548 pruebas pasan, en Python 3.9 y 3.12 (con OR-Tools 9.15 también las 14 de optimización), cada
commit pasa todas las suites por sí solo, la prueba de humo de las plantillas pasa (8/8 pasos) y
`claude plugin validate .` pasa (con un aviso por plugin, que sugiere `version`: ver B6).

Con el kit en GitHub (2026-11-08) también quedaron hechos:
- E1: CI del kit en `.github/workflows/ci.yml` (pruebas en 3.9 y 3.12, validación, prueba de humo
  `bin/humo_plantillas.py` y zizmor). Cada job se probó en local con sus mismos comandos; en GitHub corre desde que
  el repo es público (ver Pendiente 1), y el primer run pasó entero: los 5 jobs en verde, con las suites en 3.9
  y 3.12 (más las 19 de OR-Tools) y la prueba de humo 8/8 en el runner nuevo (Ubuntu con Python 3.14).
- A10: la revisión en CI instala `pr-review-toolkit` desde el commit auditado, con un marketplace propio que
  arma el workflow (una copia local del oficial no sirve: Claude Code reserva su nombre).
- B6: los plugins propios no llevan `version`; las entregas son tags (`v0.2.0` es la primera).
- Pins con menos de 7 días corregidos: uv 0.13.6 y zizmor 1.31.1.

## Siguiente
1. Hallazgos nuevos de la revisión:
   - Hecho (Kevin dijo «dale»): `evaluador_bloqueado` protege su propia configuración `.claude/ml-vision.json`
     (antes el agente podía vaciar `rutas_protegidas` y después escribir en `eval/`). Límite documentado: no ve
     comandos sobre la carpeta entera (`mv .claude otra`); eso lo frena el CODEOWNERS en el PR.
   - **EXTRA, para decidir:** `licencias.py` no revisa Dockerfiles (`RUN pip install ultralytics`).
2. Ideas de gentle-factory y pstack (revisadas el 2026-11-08; Kevin aprobó las 3 primeras con «si, dale»):
   - Hecho: el hook de Stop no da por revisado lo que no pudo correr (ae8b00e). `no_silenciar.py`: solo la persona
     agrega `# noqa`, `# type: ignore`, `# pragma: no cover` y similares, y Claude no corre `ruff --add-noqa` ni
     `ty --add-ignore` (42ff91f; probado con Claude Code 2.1.319 real). Plantillas con FBT001/FBT002,
     `acyclic_siblings` y el anti-patrón "fijar una constante" (015b345; probado al derecho y al revés).
   - **Para decidir:** 4) copiar 4 skills de pstack fijadas por SHA 6b03002 (MIT, Lauren Tan) como se hizo con
     `flujo`: create- y maintain-verification-skill, correct y blast-radius; benchmark-checklist dentro de
     `rendimiento-python`, y 3 principios para skills que ya existen (las dos ediciones, las 3 preguntas de
     idempotencia, el estado legítimo). 5) Checklist de revisión con fuentes (los 107 de gentle-factory: SWE at
     Google, eng-practices, ASVS 5.0, CWE). 6) Gate que juzga solo lo nuevo de un PR (huellas de los hallazgos en
     base y en head).
   - **EXTRA posible:** que `no_silenciar` bloquee también `@pytest.mark.skip`/`xfail` nuevos (hoy no lo hace).

## Pendiente que decide Kevin
1. Resuelto el 2026-11-08: el repo pasó a público, así Actions corre gratis (Kevin no va a pagar más). Si vuelve a
   ser privado, el CI deja de correr hasta que la cuenta tenga minutos ("recent account payments have failed or
   your spending limit needs to be increased").
2. Limpieza de lo instalado en global (`~/.claude`): quitar/reemplazar software-architecture, write-concisely,
   code-simplifier, review-local-changes, commit, create-pr, playwright-skill, ui-ux-pro-max, antislop;
   security-guidance de global a proyecto; context7 en modo CLI y versión parcheada (CVE-2026-75130).
3. uv local: 0.10.7 acepta `exclude-newer = "7 days"`; subir a 0.13.6 (la que fija la plantilla) lo alinea con el CI y el pre-commit de la
   plantilla, y sirve para `uv audit`.
4. Datos de la empresa: orquestador de datos, Terraform vs CDK, monitoreo, gestor de tareas, framework web.
5. Skills no construidas aún: `geo-raster-agro`, CLAUDE.md del equipo de datos, observabilidad de ML (drift).
6. EXTRA de la revisión sin hacer: D5 (aws-core cuesta ~4.900 tokens fijos), D6 (solapes entre skills), F2 (skills
   según el stack de la empresa).

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
