---
name: dockerfile-python-uv
description: Escribe o revisa Dockerfiles de apps Python con uv siguiendo el patrón multi-stage oficial de Astral — uv fijado por versión o digest, uv sync --locked, caché con --mount, usuario no root, imagen final slim, .dockerignore, healthcheck, hadolint y escaneo con Trivy fijado por digest. Úsala al crear, modificar o revisar un Dockerfile, docker-compose o imagen de contenedor para un servicio Python (FastAPI, workers, jobs de datos o ML).
---

# Dockerfile de Python con uv

Objetivo: imagen pequeña, reproducible (mismo `uv.lock` → mismas dependencias), sin herramientas de build ni secretos en la imagen final, y que no corra como root.

## Patrón (basado en astral-sh/uv-docker-example, multistage)
```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm AS build
# uv fijado por versión (mejor aún por digest @sha256:...)
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app
# 1) Solo dependencias: esta capa se reutiliza mientras no cambie el lock
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev
# 2) El proyecto
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

FROM python:3.12-slim-bookworm
RUN groupadd --system app && useradd --system --gid app --no-create-home app
COPY --from=build --chown=app:app /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER app
WORKDIR /app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
CMD ["uvicorn", "mi_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
La plantilla lista para copiar está en `plantillas/` del kit.

## Reglas
- La imagen base de build y la final deben ser **la misma versión de Python y la misma distro**: el `.venv` se copia tal cual.
- `--locked`: falla si `uv.lock` no coincide con `pyproject.toml`. Nunca `uv pip install` sueltos.
- `--no-dev`: sin pytest ni linters en producción.
- **No root** (`USER app`). Si el servicio necesita escribir, solo en una carpeta propia.
- `.dockerignore` con al menos: `.venv`, `.git`, `__pycache__`, `.env*`, `tests/`, `*.pyc`, `.mypy_cache`, `.ruff_cache`, datos y modelos grandes.
- **Secretos nunca en la imagen** (ni en `ENV`, ni `COPY .env`, ni `ARG`). En build, `RUN --mount=type=secret`; en ejecución, variables del orquestador (ECS task definition con Secrets Manager).
- Proceso principal en forma exec (`CMD ["..."]`) para que reciba las señales de apagado.
- ML/GPU: partir de una base CUDA oficial fijada por digest; separar en otra etapa la descarga de pesos y cargarlos en formato safetensors.
- Distroless (`gcr.io/distroless/python3`) solo si se valida que la versión de Python coincide; si no, `slim` es la opción segura.

## Verificación
```bash
hadolint Dockerfile
docker build -t app:local .
docker run --rm app:local id -u          # no debe ser 0
trivy image --severity HIGH,CRITICAL app:local
```
- hadolint sin errores (las advertencias se justifican o se corrigen).
- `id -u` distinto de 0.
- Trivy sin CRITICAL sin justificar. **Trivy fijado:** en CI, la action `aquasecurity/trivy-action` por SHA y la imagen `aquasec/trivy` por `@sha256:` (en marzo de 2026 sus tags fueron envenenados).
- Tamaño razonable: `docker image ls app:local` (una API FastAPI típica, por debajo de ~250 MB).
