"""abrir_cmux.py: abre el espacio con el diseño del cmux.json de usuario, sin duplicarlo."""

from __future__ import annotations

import json

from ayudas_flota import SCRIPTS, correr, preparar_falsos

ABRIR = SCRIPTS / "abrir_cmux.py"

CMUX_JSON = """{
  // comentario como los del cmux.json real
  "schemaVersion": 1,
  "commands": [
    {"name": "Otro", "command": "ls"},
    {"name": "Flota", "workspace": {"name": "Flota", "cwd": "~",
      "layout": {"pane": {"surfaces": [{"type": "terminal", "command": "herdr --session flota"}]}}}}
  ]
}
"""


def test_abre_el_espacio_con_el_diseno_del_cmux_json(tmp_path):
    env = preparar_falsos(tmp_path)
    (tmp_path / "cmux.json").write_text(CMUX_JSON)
    env["FLOTA_CMUX_JSON"] = str(tmp_path / "cmux.json")
    r = correr(ABRIR, env=env)
    assert r.returncode == 0, r.stderr
    llamada = (tmp_path / "cmux.log").read_text().strip()
    assert llamada.startswith("new-workspace --name Flota --focus true --cwd ")
    diseno = json.loads(llamada.split("--layout ", 1)[1])
    assert diseno["pane"]["surfaces"][0]["command"] == "herdr --session flota"


def test_sin_el_comando_avisa(tmp_path):
    env = preparar_falsos(tmp_path)
    (tmp_path / "cmux.json").write_text('{"commands": []}')
    env["FLOTA_CMUX_JSON"] = str(tmp_path / "cmux.json")
    r = correr(ABRIR, env=env)
    assert r.returncode == 1
    assert "Flota" in r.stderr
