"""flota.py: registra cómo reanudar el panel en cmux y se convierte en el cliente de herdr de la sesión."""

from __future__ import annotations

from ayudas_flota import SCRIPTS, correr, llamadas, preparar_falsos


def test_registra_la_reanudacion_y_abre_herdr(tmp_path):
    env = {**preparar_falsos(tmp_path), "CMUX_SURFACE_ID": "surface:7", "HOME": str(tmp_path)}
    correr(SCRIPTS / "flota.py", env=env)
    cmux = (tmp_path / "cmux.log").read_text()
    assert f"surface resume set --name flota --shell python3 -I {SCRIPTS / 'flota.py'}" in cmux
    assert [] in llamadas(tmp_path), "termina como `herdr --session flota` (el falso recibe la sesión y nada más)"
    assert (tmp_path / ".local" / "state" / "flota" / "arranque.log").exists()
