# Kit de ingeniería con IA

Marketplace propio de Claude Code para desarrollar con buenas prácticas: backend Python, GitHub + AWS,
ingesta de datos, optimización y visión por computador (detección de enfermedades en palma).
Se instala **por repo**, nunca global.

## Qué trae

### Plugins propios
| Plugin | Qué hace | Perfil |
|---|---|---|
| `calidad-python` | Hooks: ruff al editar; tipos, import-linter y pytest antes de terminar; aviso de macOS. Skill `verify` | base |
| `barreras` | Bloquea apply/deploy/destroy, SQL destructivo en producción, edición de `.env`/lockfiles/migraciones aplicadas, lectura de secretos | base |
| `flujo` | Superpowers v7.0.2 (5 skills, fijado por SHA): brainstorming, planes, TDD, depuración, verificar antes de terminar | base |
| `python-ingenieria` | Arquitectura hexagonal pragmática, deuda técnica, documentación, rendimiento, calidad de pruebas (mutmut), cadena de suministro | base |
| `devops-aws` | Acceso seguro del agente a AWS, GitHub Actions seguras, Dockerfile con uv, IaC sin apply, observabilidad | base (opcional) |
| `datos-optimizacion` | Formular modelos de optimización con verificador, ingesta idempotente, contratos de datos, migraciones Alembic | datos |
| `ml-vision` | División sin fuga (con verificador), receta de entrenamiento, carga segura, licencias, fichas, despliegue en AWS; hooks de evaluador bloqueado y licencias | ml |
| `explicador` | Explica cada cambio línea por línea en un HTML local (código y terminal lado a lado); el hook lo exige antes de `gh pr create` | base |

### Terceros (fijados por SHA, auditados en `terceros/AUDITORIA.md`)
aws-core, pr-review-toolkit, commit-commands, security-guidance, skill-creator, pyright-lsp,
property-based-testing, static-analysis, supply-chain-risk-auditor, differential-review, modern-python,
hf-cli. Varios con advertencias: leer la auditoría antes de activarlos.

### Plantillas para repos (`plantillas/`)
`pyproject` (ruff, ty, import-linter, deptry, complexipy, `exclude-newer`), pre-commit (prek), `.claude/settings.json`
(marketplace, plugins, reglas deny, sandbox, sin atribución a Claude), `CLAUDE.md`, CI, revisión con Claude, Dependabot, Dockerfile.

## Usarlo en un repo
```sh
python3 ~/Desarrollo/kit-ingenieria-ia/bin/adoptar.py /ruta/al/repo --perfil base --dry-run   # ver qué haría
python3 ~/Desarrollo/kit-ingenieria-ia/bin/adoptar.py /ruta/al/repo --perfil base             # aplicar (nunca sobrescribe)
```
Luego, en el repo: abrir Claude Code, aceptar la confianza de la carpeta e instalar los plugins con
`claude plugin install <plugin>@kit-ingenieria-ia --scope project`.

Para probar un plugin sin instalarlo: `claude --plugin-dir ~/Desarrollo/kit-ingenieria-ia/plugins/<plugin>`.

## Carpetas
- `investigacion/` — 8 informes con evidencia y fuentes + `00-resumen.md`
- `plugins/` — plugins propios, cada uno con README y pruebas
- `terceros/` — entradas fijadas, auditoría y cómo actualizar un SHA
- `plantillas/`, `bin/adoptar.py` — configuración base para repos
- `CONVENCIONES.md` — reglas para agregar skills, hooks y plugins
- `ESTADO.md` — dónde quedamos

## Verificar el kit
```sh
claude plugin validate .
for t in plugins/*/tests bin/tests; do python3 -m pytest "$t" -q; done
```
