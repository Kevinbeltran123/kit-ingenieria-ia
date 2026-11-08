---
name: arquitectura-python
description: Arquitectura hexagonal pragmática para servicios Python (FastAPI, Lambda, workers) en AWS. Capas domain ← application ← adapters ← entrypoints, contratos de import-linter, inyección de dependencias simple, errores de dominio y configuración con pydantic-settings. Úsala al crear un servicio, agregar un módulo o caso de uso, decidir dónde va un código, refactorizar acoplamiento o cuando hablen de "clean architecture", "hexagonal", "ports and adapters", "DDD", "estructura del proyecto".
---

# Arquitectura Python (hexagonal pragmática)

Objetivo: que la lógica de negocio se pueda probar sin FastAPI, sin base de datos y sin AWS, y que cambiar un adaptador no toque el dominio. No es una meta en sí: si el servicio es un CRUD delgado o un script, no apliques todo esto.

## Las cuatro capas

```
src/app/
├── domain/        # entidades, value objects, reglas puras, errores de dominio
├── application/   # casos de uso + puertos (typing.Protocol) que necesitan
├── adapters/      # implementaciones: SQLAlchemy, boto3, httpx, colas
└── entrypoints/   # FastAPI routers, handlers Lambda, CLI, consumidores
```

Regla de dependencias: cada capa solo importa de las de abajo.
`entrypoints → adapters → application → domain`. El dominio no importa nada del proyecto ni de frameworks.

| Capa | Contiene | No contiene |
|---|---|---|
| domain | `dataclass`/Pydantic sin I/O, validaciones de negocio, `class SaldoInsuficiente(ErrorDominio)` | fastapi, sqlalchemy, boto3, httpx, logging de infraestructura |
| application | `class RegistrarCosecha:` con `__call__`, puertos `class RepositorioLotes(Protocol)` | SQL, clientes de AWS, objetos `Request` |
| adapters | `class RepositorioLotesPostgres:` que cumple el Protocol | reglas de negocio |
| entrypoints | parseo HTTP/evento → DTO → caso de uso → respuesta | lógica de negocio |

## Hacerla cumplir con import-linter

En `pyproject.toml` (ajusta `app` al paquete real):

```toml
[tool.importlinter]
root_package = "app"

[[tool.importlinter.contracts]]
name = "Capas hexagonales"
type = "layers"
layers = ["app.entrypoints", "app.adapters", "app.application", "app.domain"]

[[tool.importlinter.contracts]]
name = "Dominio y aplicación sin frameworks ni AWS"
type = "forbidden"
source_modules = ["app.domain", "app.application"]
forbidden_modules = ["fastapi", "sqlalchemy", "boto3", "botocore", "httpx", "pydantic_settings"]
```

`lint-imports` falla si alguien rompe la regla; el hook de `calidad-python` y la skill `verify` lo corren solos.

## Inyección de dependencias: simple

Sin contenedores de DI. Constructores con parámetros y una función que arma todo (composition root) en `entrypoints`:

```python
# application/registrar_cosecha.py
class RepositorioLotes(Protocol):
    def obtener(self, lote_id: str) -> Lote: ...
    def guardar(self, lote: Lote) -> None: ...

class RegistrarCosecha:
    def __init__(self, lotes: RepositorioLotes) -> None:
        self._lotes = lotes

    def __call__(self, lote_id: str, toneladas: float) -> Lote:
        lote = self._lotes.obtener(lote_id)
        lote.registrar_cosecha(toneladas)  # la regla vive en el dominio
        self._lotes.guardar(lote)
        return lote

# entrypoints/api.py
def registrar_cosecha_dep(session: Annotated[Session, Depends(get_session)]) -> RegistrarCosecha:
    return RegistrarCosecha(RepositorioLotesPostgres(session))
```

En pruebas, el puerto se cumple con un fake en memoria (no un `Mock`): ver `calidad-pruebas`.

## Errores de dominio

- Jerarquía propia: `class ErrorDominio(Exception)` y subclases con significado (`LoteNoEncontrado`, `CosechaInvalida`).
- El dominio lanza errores de dominio; los adaptadores traducen errores técnicos (`botocore.ClientError`, `IntegrityError`) a errores de dominio o los dejan subir si son fallas de infraestructura.
- Un solo lugar traduce a HTTP: un `exception_handler` de FastAPI que mapea `LoteNoEncontrado → 404`, `CosechaInvalida → 422`. Nada de `HTTPException` dentro de casos de uso.

## Configuración

`pydantic-settings` en `entrypoints/config.py` (o `adapters/config.py`), leída una vez y pasada hacia abajo como valores, no como objeto global:

```python
class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env")
    database_url: SecretStr
    bucket_imagenes: str
    region: str = "us-east-1"
```

Secretos en AWS Secrets Manager/SSM, nunca en el repo; en local, `.env` en `.gitignore`.

## Cuándo NO abstraer

- Un solo adaptador y ninguna razón concreta para un segundo: el Protocol puede esperar. Escribe la clase concreta y extrae el puerto cuando aparezca la segunda implementación o cuando la prueba lo necesite.
- CRUD sin reglas: router → repositorio está bien. No inventes un caso de uso que solo reenvía.
- Scripts, notebooks, jobs de una sola vez: una función clara gana.
- No crees `BaseRepository[T]` genéricos, fábricas abstractas ni capas "service" que solo delegan.
- Tres líneas parecidas son mejores que una abstracción prematura.

## Decisiones que se documentan

Cambios de capa, nuevo adaptador externo, nueva dependencia de framework → un ADR corto (skill `documentacion-python`).

## Verificación

1. `lint-imports` pasa con los contratos de arriba.
2. Los casos de uso tienen pruebas que corren sin red, base de datos ni AWS.
3. `grep -rn "HTTPException" src/app/application src/app/domain` no devuelve nada.
4. Corre la skill `verify`.

Más detalle y estructura de ejemplo: `references/ejemplo-estructura.md`.
