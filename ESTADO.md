# Estado

## Dónde quedamos (2026-11-08)
Revisión completa del kit en `investigacion/09-revision-2026-11-08.md` (~60 hallazgos agrupados en 48, con
evidencia y arreglo). Están hechos todos los arreglos NECESARIOS que no dependen de GitHub, un commit por arreglo:
los de código con pruebas que fallaban antes, los de contenido verificados contra la fuente (docs oficiales o
corriendo la librería). `main` los tiene (fast-forward desde la rama `revision-2026-11-08`) y está en GitHub, en
el repo privado https://github.com/Kevinbeltran123/kit-ingenieria-ia (subido el 2026-11-08). Las explicaciones de
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

Verificación: 493 pruebas pasan (14 se saltan sin OR-Tools; con OR-Tools 9.15 también pasan), cada commit pasa
todas las suites por sí solo, los hooks y scripts corren con Python 3.9, y `claude plugin validate .` pasa.

## Siguiente
1. Con el kit ya en GitHub: E1 (CI del kit: pruebas por plugin, `claude plugin validate`, prueba de humo de las
   plantillas y hooks con Python 3.9) y A10 (revisión en CI con el plugin fijado).
2. Hallazgos nuevos de esta tanda:
   - Hecho (Kevin dijo «dale»): `evaluador_bloqueado` protege su propia configuración `.claude/ml-vision.json`
     (antes el agente podía vaciar `rutas_protegidas` y después escribir en `eval/`). Límite documentado: no ve
     comandos sobre la carpeta entera (`mv .claude otra`); eso lo frena el CODEOWNERS en el PR.
   - **EXTRA, para decidir:** `licencias.py` no revisa Dockerfiles (`RUN pip install ultralytics`).

## Pendiente que decide Kevin
1. B6, versiones: con el kit en GitHub, quien ya instaló un plugin no recibe cambios mientras `version` no cambie.
   Opciones: subir `version` en cada cambio, o quitarla para que Claude Code use el SHA del commit.
2. Limpieza de lo instalado en global (`~/.claude`): quitar/reemplazar software-architecture, write-concisely,
   code-simplifier, review-local-changes, commit, create-pr, playwright-skill, ui-ux-pro-max, antislop;
   security-guidance de global a proyecto; context7 en modo CLI y versión parcheada (CVE-2026-75130).
3. uv local: 0.10.7 acepta `exclude-newer = "7 days"`; subir a 0.13.7 lo alinea con el CI y el pre-commit de la
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
