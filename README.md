# Kit de ingeniería con IA

Marketplace propio de Claude Code para desarrollar con buenas prácticas: backend Python, GitHub + AWS,
ingesta de datos, optimización y visión por computador (detección de enfermedades en palma).
Se instala **por repo**, nunca global.

## Qué trae

### Plugins propios
| Plugin | Qué hace | Perfil |
|---|---|---|
| `calidad-python` | Hooks: solo tú silencias reglas (`# noqa`, `# type: ignore`…); ruff al editar; tipos, import-linter y pytest antes de terminar; aviso de macOS. Skill `verify` | base |
| `barreras` | Bloquea apply/deploy/destroy, SQL destructivo en producción, edición de `.env`/lockfiles/migraciones aplicadas, lectura de secretos | base |
| `flujo` | Superpowers v7.0.2 (5 skills, fijado por SHA): brainstorming, planes, TDD, depuración, verificar antes de terminar; y `/correct` de pstack, que convierte una corrección repetida en una regla que se cumple sola | base |
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

### Si el repo ya tiene código
Las reglas aplican a todo el código, también al viejo. Para no arreglarlo todo de una vez ni tapar error por error,
cada herramienta guarda su propia línea base y solo falla lo nuevo. La crea la persona, una sola vez: a Claude se
lo impide `no_silenciar` (para hacerlo con Claude, arranca esa sesión con `CALIDAD_PYTHON_PERMITIR_SILENCIAR=1`).

1. **Formato y arreglos seguros**, en un commit aparte: `uv run ruff check . --fix` y `uv run ruff format .`. Pon
   el SHA de ese commit en `.git-blame-ignore-revs` (GitHub lo respeta en blame; en local:
   `git config blame.ignoreRevsFile .git-blame-ignore-revs`). Sin esto, el hook de edición reformatea cada archivo
   entero la primera vez que Claude lo toca, y el cambio real se pierde en el diff.
2. **ruff**: `uv run ruff check . --add-noqa="línea base"`. Cuando el código se arregla, RUF100 marca el `noqa` que
   sobra y el `--fix` del hook de edición lo quita: la línea base solo baja.
3. **ty**: `baseline = "ty-baseline.json"` en `[tool.ty]` y `uv run ty check --update-baseline`. Un error viejo que
   se mueve de línea sigue cubierto; uno nuevo falla, también en el hook de Stop. Está en preview: si al subir ty no
   lee el archivo, se regenera con el mismo comando.
4. **complexipy**: `uv run complexipy . --snapshot-create` (guarda `complexipy-snapshot.json`).
5. **import-linter**: los imports que hoy rompen un contrato van en su `ignore_imports`. Una entrada que deja de
   existir da error, así que la lista solo baja.
6. **vulture y deptry**: `uv run vulture --make-whitelist > vulture_whitelist.py` (y agrégalo a `paths`), y
   `per_rule_ignores` en `[tool.deptry]`.

Comprobado con ruff 0.17.3, ty 0.0.95 y complexipy 8.3.0: lo viejo pasa y lo nuevo falla.

## Entregas y versiones
Los plugins propios no llevan `version`: Claude Code usa el commit como versión, así que ningún cambio se queda
sin llegar por olvidar subirla. Las entregas para el equipo son tags (`v0.2.0`, `v0.3.0`…) y cada repo fija la suya:
```sh
python3 bin/adoptar.py /ruta/al/repo --marketplace-github Kevinbeltran123/kit-ingenieria-ia --ref v0.2.0
```
Para pasar un repo a una entrega nueva, se vuelve a correr con el tag nuevo (cambia la fuente en
`.claude/settings.json`) y después `claude plugin marketplace update kit-ingenieria-ia`. Sin `--ref`, el repo
sigue la cabeza de `main`. Sin adoptar.py, el marketplace en una entrega se agrega con
`claude plugin marketplace add Kevinbeltran123/kit-ingenieria-ia#v0.2.0` (comprobado: el plugin instalado queda
con el commit del tag como versión). Los plugins de terceros que declaran `version` en su propio `plugin.json` solo se
actualizan cuando su autor la sube (ver `terceros/README.md`).

## Carpetas
- `investigacion/` — 8 informes con evidencia y fuentes + `00-resumen.md`
- `plugins/` — plugins propios, cada uno con README y pruebas
- `terceros/` — entradas fijadas, auditoría y cómo actualizar un SHA
- `plantillas/`, `bin/adoptar.py` — configuración base para repos
- `CONVENCIONES.md` — reglas para agregar skills, hooks y plugins
- `ESTADO.md` — dónde quedamos

## Verificar el kit
El CI (`.github/workflows/ci.yml`) lo hace en cada push: las pruebas de cada plugin con Python 3.9 y 3.12,
`claude plugin validate`, la prueba de humo de las plantillas y zizmor. En local:
```sh
claude plugin validate .
for t in plugins/*/tests bin/tests; do python3 -m pytest "$t" -q; done
python3 bin/humo_plantillas.py   # repo nuevo con las plantillas y los pasos de su CI (necesita red)
```

## Licencia
MIT (ver `LICENSE`). Lo que viene de otros conserva su licencia: `plugins/flujo` es una copia editada de
obra/superpowers (MIT, © Jesse Vincent, ver `plugins/flujo/LICENSE`) con una skill y un punto de pstack (MIT,
© Lauren Tan, ver `plugins/flujo/LICENSE-pstack`), las 7 preguntas de benchmark de `rendimiento-python` también
vienen de pstack (ver `plugins/python-ingenieria/LICENSE-pstack`) y las fuentes IBM Plex Mono del explicador son
OFL 1.1 (ver su `OFL.txt`). Los plugins de terceros del marketplace no están copiados aquí: se instalan desde sus
repos, con sus licencias.
