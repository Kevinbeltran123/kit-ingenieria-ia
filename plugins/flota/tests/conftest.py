from __future__ import annotations

import pytest
from ayudas_flota import crear_repo, preparar_falsos


@pytest.fixture
def repo(tmp_path):
    return crear_repo(tmp_path / "repo")


@pytest.fixture
def falsos(tmp_path, monkeypatch):
    """Entorno con herdr y cmux falsos, también aplicado al proceso de la prueba (para importar los módulos)."""
    env = preparar_falsos(tmp_path)
    for clave in ("PATH", "FALSO_ESTADO", "FALSO_LLAMADAS", "FALSO_CMUX", "FLOTA_EVENTOS_DIR", "FLOTA_HERDR"):
        monkeypatch.setenv(clave, env[clave])
    return env
