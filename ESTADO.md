# Estado

## Dónde quedamos (2026-11-08)
Revisión completa del kit en `investigacion/09-revision-2026-11-08.md` (~60 hallazgos agrupados en 48, con
evidencia y arreglo). Todo está en la rama `revision-2026-11-08` (sin pasar a `main`), un commit por arreglo,
cada uno con pruebas que fallaban antes; las explicaciones de los primeros arreglos están en
`.explicaciones/commits/` (fuera de git). Hecho:
- Seguridad: A1 Python 3.9 y `onFailure`, A2 SCP, A3 regla `local` en barreras (borrados, `--no-verify`),
  A4 `Read(**/.env)`, A5–A6 sesión de AWS solo con el rol de lectura, A7 aws-core no se activa (proxy 1.7.0),
  A8 tfstate y `GetParameterHistory`, A9 Claude no se aprueba licencias, A11 torch ≥ 2.10, A12 `torch.hub.load`
  y descargas sin revisión, A13 MLflow registra ONNX.
- Bugs: B1 import-linter, B2 hook de Stop, B3 migraciones recién generadas, B4 splits contra el evaluador,
  B5 `adoptar.py` con GitHub.
- Terceros: AUDITORIA.md corregida (aws-core, `/clean_gone`, pyright-lsp, hf-cloud-sagemaker, react, modern-python).
- Nuevo: plugin `explicador` (vista B, línea por línea, exigido antes de `gh pr create`; `--commit` para un
  commit puntual). Es para el código de la empresa; en el kit no se generan explicaciones.

Verificación: 403 pruebas pasan (14 se saltan sin OR-Tools), los hooks y scripts también con Python 3.9, y
`claude plugin validate .` pasa.

## Siguiente, en este orden (detalle en la revisión)
1. B7–B13, bugs en scripts y hooks: verificar_division da OK sin imágenes; vulture al 80 % no ve funciones
   muertas; mutantes sin rama base muta todo; suministro.py da OK sin revisar; evaluador_bloqueado y rutas
   (`cwd`, `cd`, worktrees); licencias.py y `uv run --with`, `uvx`, PEP 723; Pandera sobre LazyFrame.
2. C1–C8, contenido: SageMaker SDK v3, LocalStack de pago (moto por defecto), escala ICA, receta (selección en
   test, IC por bootstrap), paridad ONNX con preprocesamiento, CODEOWNERS en el perfil ml, Terraform plan en CI,
   detalles menores.
3. E2–E4 y E6: pre-commit en el CI de la plantilla, versiones duplicadas (ruff, complexipy, uv), verify frente a
   CI, huecos menores de barreras.
4. Al subir el kit a GitHub: A10 (revisión en CI con plugin fijado), E1 (CI del kit) y B6 (versiones).

## Pendiente que decide Kevin
1. Pasar la rama `revision-2026-11-08` a `main` (cada commit pasa sus pruebas por sí solo).
   Después se puede quitar el hook global `~/.claude/hooks/block-destructive-bash.py`: la regla `local` lo cubre.
2. Subir el kit a un repo privado de GitHub. Al hacerlo: CI propio (E1) y decidir versiones (B6: subir `version`
   en cada cambio o quitarla para que Claude Code use el SHA).
3. Terceros a quitar: hf-cloud-sagemaker, react-best-practices, plugin-dev (D2, D3).
4. Limpieza de lo instalado en global (`~/.claude`): quitar/reemplazar software-architecture, write-concisely,
   code-simplifier, review-local-changes, commit, create-pr, playwright-skill, ui-ux-pro-max, antislop;
   security-guidance de global a proyecto; context7 en modo CLI y versión parcheada (CVE-2026-75130).
5. uv local: 0.10.7 ya acepta `exclude-newer = "7 days"`; actualizar sirve para `uv audit`.
6. Datos de la empresa: orquestador de datos, Terraform vs CDK, monitoreo, gestor de tareas, framework web.
7. Skills no construidas aún: `geo-raster-agro`, CLAUDE.md del equipo de datos, observabilidad de ML (drift).

## Decisiones
- Stack empresa: casi todo Python, GitHub, AWS. Sin política de IA.
- Alcance: marketplace propio, instalar por repo, nada global.
- Superpowers: opción B (5 skills copiadas, fijadas por SHA; executing-plans fuera porque depende de partes no copiadas).
- Excluido de terceros: web-design-guidelines de Vercel (descarga instrucciones sin fijar en cada uso).
- Sin atribución a Claude en commits/PR (plantilla settings.json).
- Explicador (2026-11-08): vista B (código y terminal lado a lado), una nota por cada línea cambiada, HTML local
  fuera de git (`.explicaciones/`, vía `.git/info/exclude`), se exige al abrir PR. Fuente única IBM Plex Mono incrustada.
- Hooks y scripts: compatibles con Python 3.9; las barreras fallan cerrado también si el hook no arranca.
