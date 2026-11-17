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
    llamada = next(x for x in (tmp_path / "cmux.log").read_text().splitlines() if x.startswith("new-workspace"))
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


def test_cierra_los_espacios_viejos_con_el_mismo_nombre(tmp_path):
    env = preparar_falsos(tmp_path)
    falso = (
        '#!/bin/sh\nprintf "%s\\n" "$*" >> "$FALSO_CMUX"\n'
        'case "$*" in "workspace list --json") exit 2;; "workspace list")'
        ' printf "  workspace:1  arco\\n* workspace:3  Flota  [selected]\\n  workspace:4  Flota de pesca\\n";; esac\n'
    )
    (tmp_path / "bin" / "cmux").write_text(falso)
    (tmp_path / "cmux.json").write_text(CMUX_JSON)
    env["FLOTA_CMUX_JSON"] = str(tmp_path / "cmux.json")
    r = correr(ABRIR, env=env)
    assert r.returncode == 0, r.stderr
    log = (tmp_path / "cmux.log").read_text().splitlines()
    nuevo = next(i for i, x in enumerate(log) if x.startswith("new-workspace"))
    assert log[nuevo + 1 :] == ["workspace close workspace:3"], "crea primero y cierra solo el que se llama igual"
