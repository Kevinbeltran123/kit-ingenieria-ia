# Multi-stage con uv, basado en la guía oficial de Astral. Cambia "app" y el comando final.
# Fija la imagen base por digest en producción (Dependabot la actualiza).
ARG PYTHON_VERSION=3.12

FROM ghcr.io/astral-sh/uv:0.13.7-python${PYTHON_VERSION}-trixie-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app
# Primero solo dependencias: se cachean mientras no cambie el lockfile.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

FROM python:${PYTHON_VERSION}-slim-trixie
RUN groupadd --system app && useradd --system --gid app --home-dir /app app
COPY --from=builder --chown=app:app /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
WORKDIR /app
USER app
CMD ["python", "-m", "app"]
