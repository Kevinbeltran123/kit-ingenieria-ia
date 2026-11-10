# Plantillas para repos Python

Se aplican con `bin/adoptar.py`, que **nunca sobrescribe** archivos existentes:

    python3 bin/adoptar.py /ruta/al/repo --dry-run          # ver qué haría
    python3 bin/adoptar.py /ruta/al/repo                    # perfil base
    python3 bin/adoptar.py /ruta/al/repo --perfil datos     # + datos-optimizacion, devops-aws
    python3 bin/adoptar.py /ruta/al/repo --perfil ml        # + ml-vision, devops-aws
    python3 bin/adoptar.py /ruta/al/repo --sin-docker

| Plantilla | Destino en el repo | Notas |
|---|---|---|
| `python/.python-version` | `.python-version` | Fija Python 3.12 para uv en local, en CI y en la prueba de humo: la misma versión del Dockerfile y de `[tool.ty.environment]`. Sin él, `uv sync` toma el Python del runner (3.14 en el primer run del CI) |
| `python/pyproject.toml.fragmento` | (manual) `pyproject.toml` | ruff, ty, pytest, coverage, complexipy, deptry, vulture, import-linter, `exclude-newer = "7 days"` |
| `python/.pre-commit-config.yaml` | `.pre-commit-config.yaml` | Para `prek` (`uvx prek install`) o pre-commit. ruff y complexipy corren con `uv run`, con la versión de `uv.lock` |
| `claude/settings.json` | `.claude/settings.json` | Marketplace del kit, plugins por perfil, reglas deny, sandbox, sin co-autoría de Claude. Si ya existe, se fusiona agregando sin borrar |
| `claude/CLAUDE.md` | `CLAUDE.md` | < 80 líneas, con huecos `<...>` |
| `github/workflows/ci.yml` | `.github/workflows/ci.yml` | Acciones fijadas por SHA, permisos mínimos, zizmor y pip-audit. Vuelve a correr los hooks de pre-commit (`--no-verify` los salta en local) y gitleaks sobre toda la historia |
| `github/workflows/claude-review.yml` | `.github/workflows/claude-review.yml` | Revisión de PR con `pr-review-toolkit`, instalado desde el commit que auditó el kit (marketplace propio que arma el workflow); necesita el secreto `ANTHROPIC_API_KEY`. Comenta con el `GITHUB_TOKEN` del workflow: no hace falta instalar la Claude GitHub App. Una revisión por PR a la vez: un push nuevo cancela la anterior |
| `github/dependabot.yml` | `.github/dependabot.yml` | uv, Actions y Docker con cooldown de 7 días |
| `github/CODEOWNERS.ml` | `.github/CODEOWNERS` (solo perfil ml) | Dueños de `eval/`, `splits/`, la config del hook y `LICENSES.md`. No se crea si el repo ya tiene CODEOWNERS en la raíz o en `docs/` |
| `docker/Dockerfile`, `docker/.dockerignore` | raíz | Multi-stage con uv, usuario sin privilegios, ejemplo de `HEALTHCHECK` comentado. La prueba de humo construye la imagen y comprueba que no corre como root; es el único Dockerfile del kit (la skill `dockerfile-python-uv` remite aquí) |

## Marketplace: local o GitHub
JSON no admite comentarios, así que la variante se elige al adoptar:
- **Local (por defecto):** `{"source": "directory", "path": "/Users/.../kit-ingenieria-ia"}`. Sirve para probar en tu máquina; la ruta no existe en la de otra persona ni en CI.
- **GitHub:** `python3 bin/adoptar.py REPO --marketplace-github Kevinbeltran123/kit-ingenieria-ia --ref v0.3.0` escribe `{"source": "github", "repo": "Kevinbeltran123/kit-ingenieria-ia", "ref": "v0.3.0"}`. Es la opción para el equipo: cada repo queda en una entrega (tag) y pasa a la siguiente volviendo a correrlo con el tag nuevo. Hoy el repo es público; si vuelve a ser privado, cada persona necesita acceso de lectura y git autenticado (`gh auth login`).

El marketplace del repo solo se registra después de aceptar el diálogo de confianza de la carpeta. Las reglas `deny` aplican de inmediato.

## Decisiones que conviene conocer
- **Versiones y cooldown:** `exclude-newer = "7 days"` hace que uv ignore lo publicado hace menos de 7 días. Por eso el fragmento usa rangos (`uv.lock` fija las exactas) y ty, que está en beta y se fija exacto, va en una versión con más de 7 días. Para un parche de seguridad urgente: `exclude-newer-package = { paquete = false }`. Requiere uv reciente: 0.10.7 ya acepta la duración; está probado con 0.13.6, la misma versión del CI, del Dockerfile y de pre-commit.
- **Sandbox:** activo, con red limitada a PyPI y GitHub y `~/.aws/credentials` oculto. Si un comando necesita otro dominio, Claude Code pregunta. Para desactivarlo en un repo: `"sandbox": {"enabled": false}` en `.claude/settings.local.json`. `~/.ssh` no se bloquea en el sandbox para no romper `git push` por SSH; sí se bloquea su lectura con la herramienta Read.
- **`attribution`:** `commit` y `pr` vacíos y `sessionUrl: false` (no `false` a secas, que versiones anteriores a 2.1.281 rechazan).
- **Revisión con Claude en CI:** no corre en PRs de forks ni usa `pull_request_target`; solo herramientas de lectura y comentarios. Comenta con el `GITHUB_TOKEN` del workflow: sin `github_token`, la acción cambia un token OIDC por uno de la Claude GitHub App en api.anthropic.com y falla si la App no está instalada en la organización. Para usar la App, quitar `github_token` y devolver `id-token: write` al job.

## Verificado el 2026-11-08
- `settings.json` contra el esquema oficial (schemastore): 0 errores.
- zizmor 1.31.1 sobre los workflows adoptados: sin hallazgos.
- `uv lock` (uv 0.13.6) con el fragmento: resuelve con ruff 0.17.3, ty 0.0.95 e import-linter 2.15.
- Imágenes Docker: `ghcr.io/astral-sh/uv:0.13.6-python3.12-trixie-slim` y `python:3.12-slim-trixie` existen.
- Pruebas de `adoptar.py`: `python3 -m pytest bin/tests -q`.
