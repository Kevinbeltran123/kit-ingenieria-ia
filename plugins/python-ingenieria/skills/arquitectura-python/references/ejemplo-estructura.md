# Estructura de ejemplo: servicio FastAPI + AWS

```
servicio-cosechas/
├── pyproject.toml            # uv, ruff, ty, import-linter, pytest
├── src/app/
│   ├── domain/
│   │   ├── lote.py           # Lote, registrar_cosecha(), reglas
│   │   └── errores.py        # ErrorDominio, LoteNoEncontrado, CosechaInvalida
│   ├── application/
│   │   ├── puertos.py        # RepositorioLotes, AlmacenImagenes (Protocol)
│   │   └── registrar_cosecha.py
│   ├── adapters/
│   │   ├── postgres/lotes.py # SQLAlchemy 2 (ver skill migraciones del kit de datos)
│   │   └── s3/imagenes.py    # boto3
│   └── entrypoints/
│       ├── api.py            # FastAPI app, routers, exception handlers
│       ├── lambda_handler.py # mismo caso de uso, otro entrypoint
│       └── config.py         # pydantic-settings
└── tests/
    ├── unit/                 # dominio y casos de uso con fakes en memoria
    ├── integration/          # adaptadores con testcontainers / LocalStack
    └── api/                  # TestClient o schemathesis
```

## Señales de que la estructura se está degradando

| Señal | Corrección |
|---|---|
| `import boto3` en `application/` | mover a un adaptador detrás de un puerto |
| Casos de uso que reciben `Request` o `Session` | recibir valores/DTOs y puertos |
| Entidades con métodos `save()` | persistencia al adaptador |
| Archivo `utils.py` creciendo | ubicar cada función en la capa que la usa |
| Router con `if` de negocio | mover la regla al dominio |
| Pruebas unitarias que necesitan Docker | el caso de uso depende de un adaptador concreto |

## Lambda

El handler es otro entrypoint: parsea el evento, arma el caso de uso con sus adaptadores (fuera del handler para reutilizar conexiones entre invocaciones) y llama al mismo caso de uso que la API.
