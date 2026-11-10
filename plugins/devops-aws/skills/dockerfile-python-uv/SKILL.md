---
name: dockerfile-python-uv
description: Escribe o revisa Dockerfiles de apps Python con uv siguiendo el patrón multi-stage oficial de Astral — uv fijado por versión o digest, uv sync --locked, caché con --mount, usuario no root, imagen final slim, .dockerignore, healthcheck, hadolint y escaneo con Trivy fijado por digest. Úsala al crear, modificar o revisar un Dockerfile, docker-compose o imagen de contenedor para un servicio Python (FastAPI, workers, jobs de datos o ML).
---

# Dockerfile de Python con uv

Objetivo: imagen pequeña, reproducible (mismo `uv.lock` → mismas dependencias), sin herramientas de build ni secretos en la imagen final, y que no corra como root.

## Patrón (multi-stage con uv, de astral-sh/uv-docker-example)

El Dockerfile de referencia es `plantillas/docker/Dockerfile` del kit, con su `.dockerignore` al lado: `bin/adoptar.py`
los copia al repo y la prueba de humo del kit construye la imagen y comprueba que no corre como root. No lo copies aquí
ni en otra skill: si hay que cambiar el patrón, se cambia la plantilla. Lo que hace:

1. Etapa `builder` sobre `ghcr.io/astral-sh/uv:<uv>-python<versión>-<distro>-slim`. Primero solo las dependencias
   (`uv sync --locked --no-install-project --no-dev` con `uv.lock` y `pyproject.toml` montados), que quedan en caché
   mientras no cambie el lock; después `COPY . /app` y `uv sync --locked --no-dev`.
2. Etapa final sobre `python:<versión>-slim-<distro>`, la misma versión de Python y la misma distro que el builder:
   copia `/app` con el `.venv` ya armado, usuario sin privilegios (`USER app`), `PATH` al `.venv` y `CMD` en forma exec.
3. Para un servicio HTTP, descomenta `EXPOSE` y `HEALTHCHECK` (la plantilla trae el ejemplo) y cambia el `CMD`.

## Reglas
- La imagen base de build y la final deben ser **la misma versión de Python y la misma distro**: el `.venv` se copia tal cual.
- `--locked`: falla si `uv.lock` no coincide con `pyproject.toml`. Nunca `uv pip install` sueltos.
- `--no-dev`: sin pytest ni linters en producción.
- **No root** (`USER app`). Si el servicio necesita escribir, solo en una carpeta propia.
- `.dockerignore` con al menos: `.venv`, `.git`, `__pycache__`, `*.pyc`, `.env*`, `secrets/`, `tests/`, `.github/`, `.claude/`,
  las cachés (`.pytest_cache`, `.ruff_cache`, `.mypy_cache`), `.explicaciones/`, y los datos y modelos grandes del repo. La plantilla
  trae todo menos lo último.
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
