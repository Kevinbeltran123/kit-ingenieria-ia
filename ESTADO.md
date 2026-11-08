# Estado

## Dónde quedamos (2026-11-08)
Revisión completa del kit en `investigacion/09-revision-2026-11-08.md` (~60 hallazgos agrupados en 48, con
evidencia y arreglo). Hechos ese día, cada uno con pruebas que fallaban antes del arreglo (sin commit todavía):
1. **Hook de Stop** (calidad-python 0.2.1): vuelve a revisar después de que Claude corrige; 2 oportunidades y aviso.
2. **Python 3.9** en todos los hooks y scripts (`from __future__ import annotations`) y `"onFailure": "block"` en
   barreras y evaluador_bloqueado. Lo vigila `bin/tests/test_compatibilidad.py`.
3. **Plantilla de import-linter**: `include_external_packages = true`, capas opcionales; prueba de humo real en
   `bin/tests/test_plantillas.py`.
4. **SCP de AWS**: `Bool aws:ViaAWSMCPService` (la clave anterior no denegaba nada); prueba en devops-aws.
5. **Plugin `explicador` 0.1.0** (vista B elegida por Kevin): explica cada cambio línea por línea en un HTML local y
   lo exige antes de `gh pr create`. En los tres perfiles de `adoptar.py`.

Verificación: 338 pruebas pasan (14 se saltan sin OR-Tools), 199 también con el Python 3.9 de macOS, y
`claude plugin validate .` pasa.

## Siguiente, en este orden (detalle en la revisión)
1. A3: borrados locales en barreras (`rm -rf`, `git reset --hard`, `push --force`, `clean -fdx`, `--no-verify`),
   pasando las reglas del hook global `~/.claude/hooks/block-destructive-bash.py` con sus pruebas.
2. A9: que licencias.py impida que Claude escriba `APROBADO:` en `LICENSES.md`.
3. A4: `Read(**/.env)` en vez de `Read(./.env)` en la plantilla de settings.
4. B3 y B4: barreras contra migraciones-alembic, evaluador_bloqueado contra division-sin-fuga.
5. B5: `adoptar.py` mezcla fuentes al re-adoptar con `--marketplace-github`.
6. A5–A8, A10–A13: AWS (perfil SSO, `--skip-auth`, proxy 1.7.0, política de lectura), CI de revisión, torch ≥ 2.10,
   carga segura y MLflow.
7. Resto de B (bugs de scripts y hooks), C (contenido desactualizado) y E (proceso).

## Pendiente que decide Kevin
1. Commits: un commit por arreglo (sin co-autoría) para que cada uno tenga su explicación.
2. Subir el kit a un repo privado de GitHub. Al hacerlo: CI propio (E1) y decidir versiones (B6: subir `version`
   en cada cambio o quitarla para que Claude Code use el SHA).
3. Terceros a quitar: hf-cloud-sagemaker, react-best-practices, plugin-dev (D2, D3); `/clean_gone` "no usar" (D1).
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
