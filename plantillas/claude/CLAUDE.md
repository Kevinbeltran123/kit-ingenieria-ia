# <NOMBRE DEL REPO>

<Una frase: qué hace este servicio y para quién.>

## Comandos
- Instalar: `uv sync`
- Pruebas: `uv run pytest -q`
- Lint y formato: `uv run ruff check --fix . && uv run ruff format .`
- Tipos: `uv run ty check`
- Arquitectura: `uv run lint-imports`
- Todo junto antes de commit: `uvx prek run --all-files`
- Correr local: `<comando>`

## Arquitectura
- `src/app/domain/`: entidades y reglas puras. Sin frameworks, sin AWS, sin I/O.
- `src/app/application/`: casos de uso y puertos (`Protocol`).
- `src/app/adapters/`: implementaciones de los puertos (boto3, SQLAlchemy, httpx).
- `src/app/entrypoints/`: routers FastAPI, handlers Lambda, CLI.
- Las dependencias van hacia adentro; import-linter lo hace cumplir.
- <Servicios externos de los que depende y cómo se simulan en pruebas.>

## Convenciones
- Python 3.12, tipado en todo el código nuevo. Docstrings estilo Google en funciones públicas.
- Nada de abstracciones para un solo uso. Tres líneas parecidas son mejores que una abstracción prematura.
- Cambios pequeños y enfocados; no reformatear ni refactorizar código que no toca la tarea.
- Errores: <cómo se manejan y se registran (structlog / logging)>.
- Configuración por variables de entorno vía <pydantic-settings / otro>; nunca secretos en el código.
- Commits: Conventional Commits en español. Sin co-autoría de IA.

## Pruebas
- Toda corrección de bug empieza con una prueba que falla.
- Probar comportamiento, no implementación. Mocks solo en los bordes (AWS, red, reloj).
- AWS en pruebas: <moto / LocalStack con testcontainers>.

## Cómo verificar antes de decir "listo"
1. `uv run pytest -q` pasa.
2. `uv run ty check` y `uv run lint-imports` sin errores.
3. Si tocaste infraestructura: solo `plan`/`diff`; el `apply` se hace desde CI.

## No hacer
- No leer `.env`, `secrets/` ni credenciales de AWS.
- No ejecutar `terraform apply`, `cdk deploy` ni nada contra producción.
- No editar migraciones ya aplicadas; crear una nueva.
- <Otras reglas del equipo.>
