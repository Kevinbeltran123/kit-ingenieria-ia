"""pesado.py: corre el comando en un turno, lo libera al salir y recupera turnos de procesos muertos."""

from __future__ import annotations

import os

from ayudas_flota import SCRIPTS, correr

PESADO = SCRIPTS / "pesado.py"


def test_corre_y_libera(tmp_path):
    env = {**os.environ, "FLOTA_TURNOS_DIR": str(tmp_path / "turnos"), "FLOTA_TURNOS": "1"}
    r = correr(PESADO, "sh", "-c", "exit 7", env=env)
    assert r.returncode == 7
    assert not list((tmp_path / "turnos").iterdir()), "el turno queda libre"


def test_recupera_turno_de_proceso_muerto(tmp_path):
    turno = tmp_path / "turnos" / "turno-1"
    turno.mkdir(parents=True)
    (turno / "pid").write_text("999999")
    env = {
        **os.environ,
        "FLOTA_TURNOS_DIR": str(tmp_path / "turnos"),
        "FLOTA_TURNOS": "1",
        "FLOTA_TURNOS_ESPERA": "0.1",
    }
    r = correr(PESADO, "true", env=env, timeout=10)
    assert r.returncode == 0


def test_sin_comando_muestra_uso(tmp_path):
    r = correr(PESADO, env=dict(os.environ))
    assert r.returncode == 2
