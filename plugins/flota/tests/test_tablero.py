"""tablero.py: columnas de flujo, estado completo y un servidor que solo obedece con token, host y JSON correctos."""

from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest
import tablero
from ayudas_flota import SCRIPTS, llamadas


@pytest.mark.parametrize(
    ("c", "vivo", "listo", "en_puerta", "col"),
    [
        ({"estado": "enviado"}, "idle", True, True, "enviado"),
        ({"estado": "gate"}, "idle", False, False, "puerta"),
        ({}, "idle", True, True, "puerta"),
        ({}, "idle", True, False, "listo"),
        ({}, "blocked", False, False, "espera"),
        ({}, "working", False, False, "trabajando"),
        ({}, "idle", False, False, "quieto"),
        ({"estado": "cerrado"}, None, False, False, "quieto"),
    ],
)
def test_columna(c, vivo, listo, en_puerta, col):
    assert tablero.columna(c, vivo, listo=listo, en_puerta=en_puerta) == col


def preparar_run(tmp_path):
    run = tmp_path / "run"
    (run / "gate").mkdir(parents=True)
    (run / "STATE.md").write_text("# c\n## Bitácora\n- 2026-11-17 09:00 carril api iniciado\n")
    (run / "carriles.json").write_text(json.dumps({
        "api": {"nombre": "api", "tipo": "codex", "estado": "activo"},
        "ui": {"nombre": "ui", "tipo": "claude", "estado": "activo", "brief": str(run / "briefs" / "ui.md")},
        "docs": {"nombre": "docs", "tipo": "claude", "estado": "activo"},
    }))  # fmt: skip
    (run / "handover-ui.md").write_text("UI-READY flota/ui abc1234\n")
    (run / "gate" / "queue.md").write_text("## En cola\n- docs\n## Done\n- api FAIL: conflicto en calc.py\n")
    return run


def escribir_estado(tmp_path, agentes):
    (tmp_path / "estado.json").write_text(json.dumps({"agentes": agentes}))


def test_estado_reune_todo(tmp_path, falsos):
    run = preparar_run(tmp_path)
    escribir_estado(
        tmp_path, {"api": {"status": "blocked"}, "ui": {"status": "idle"}, "coordinador": {"status": "working"}}
    )
    d = tablero.estado({"demo": {"repo": "", "run": str(run)}}, "s")
    cols = {f["nombre"]: f["columna"] for f in d["carriles"]}
    assert cols == {"api": "espera", "ui": "listo", "docs": "puerta"}
    assert [o["nombre"] for o in d["otros"]] == ["coordinador"]
    assert {f["proyecto"] for f in d["carriles"]} == {"demo"}
    assert d["proyectos"][0]["resumen"]["listo"] == 1
    assert d["resumen"]["espera"] == 1
    assert d["bitacora"] == ["2026-11-17 09:00 demo · carril api iniciado"]
    assert "TITULO" not in tablero.vista_terminal(d)
    assert "api" in tablero.vista_terminal(d)


def test_la_pagina_no_carga_nada_de_internet():
    html = (SCRIPTS / "tablero.html").read_text()
    assert not re.search(r"""(src|href)\s*=\s*["']https?:|url\(\s*["']?https?:|@import""", html)
    assert "innerHTML" not in html, "todo se pinta con textContent/append"


@pytest.fixture
def servidor(tmp_path, falsos):
    run = preparar_run(tmp_path)
    escribir_estado(tmp_path, {"api": {"status": "blocked", "pantallas": ["¿Continuar? (y/n)"]}})
    tablero.Tablero.ctx = {"fijos": {"demo": {"repo": "", "run": str(run)}}, "sesion": "s", "token": "secreto"}
    srv = ThreadingHTTPServer(("127.0.0.1", 0), tablero.Tablero)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def pedir(url, cuerpo=None, cabeceras=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(url, data=datos, headers=cabeceras or {})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def test_sin_token_no_hay_nada(servidor):
    assert pedir(f"{servidor}/")[0] == 403
    assert pedir(f"{servidor}/api/estado")[0] == 403
    assert pedir(f"{servidor}/api/estado?t=otro")[0] == 403
    codigo, cuerpo = pedir(f"{servidor}/?t=secreto")
    assert codigo == 200
    assert "<title>Flota</title>" in cuerpo


def test_host_ajeno_se_rechaza(servidor):
    puerto = servidor.rsplit(":", 1)[1]
    assert pedir(f"{servidor}/api/estado?t=secreto", cabeceras={"Host": f"malo.example:{puerto}"})[0] == 403


def test_estado_y_lectura_de_pantalla(servidor):
    codigo, cuerpo = pedir(f"{servidor}/api/estado", cabeceras={"X-Flota-Token": "secreto"})
    assert codigo == 200
    assert {c["nombre"] for c in json.loads(cuerpo)["carriles"]} == {"api", "ui", "docs"}
    codigo, cuerpo = pedir(f"{servidor}/api/leer?nombre=api&t=secreto")
    assert codigo == 200
    assert json.loads(cuerpo)["texto"] == "¿Continuar? (y/n)"
    assert pedir(f"{servidor}/api/leer?nombre=nadie&t=secreto")[0] == 404


def test_archivos_solo_los_de_la_corrida(servidor):
    codigo, cuerpo = pedir(f"{servidor}/api/archivo?nombre=ui&cual=handover&t=secreto")
    assert codigo == 200
    assert "UI-READY" in json.loads(cuerpo)["texto"]
    assert pedir(f"{servidor}/api/archivo?nombre=../../etc/passwd&cual=otro&t=secreto")[0] == 404


def test_post_exige_token_en_cabecera_json_y_origen(servidor, tmp_path):
    json_tok = {"Content-Type": "application/json", "X-Flota-Token": "secreto"}
    assert (
        pedir(
            f"{servidor}/api/teclas?t=secreto", {"nombre": "api", "tecla": "y"}, {"Content-Type": "application/json"}
        )[0]
        == 403
    )
    assert (
        pedir(
            f"{servidor}/api/teclas",
            {"nombre": "api", "tecla": "y"},
            {"X-Flota-Token": "secreto", "Content-Type": "text/plain"},
        )[0]
        == 415
    )
    assert (
        pedir(f"{servidor}/api/teclas", {"nombre": "api", "tecla": "y"}, {**json_tok, "Origin": "http://malo.example"})[
            0
        ]
        == 403
    )
    assert pedir(f"{servidor}/api/teclas", {"nombre": "api", "tecla": "rm"}, json_tok)[0] == 400
    assert pedir(f"{servidor}/api/teclas", {"nombre": "nadie", "tecla": "y"}, json_tok)[0] == 404
    assert pedir(f"{servidor}/api/teclas", {"nombre": "api", "tecla": "y"}, json_tok)[0] == 200
    assert pedir(f"{servidor}/api/enviar", {"nombre": "api", "texto": "sigue"}, json_tok)[0] == 200
    assert pedir(f"{servidor}/api/enfocar", {"nombre": "api"}, json_tok)[0] == 200
    hechas = llamadas(tmp_path)
    assert ["agent", "send-keys", "api", "y"] in hechas
    assert ["agent", "prompt", "api", "sigue"] in hechas
    assert ["agent", "focus", "api"] in hechas


def test_estado_junta_varios_proyectos(tmp_path, falsos):
    a, b = tmp_path / "a-flota", tmp_path / "b-flota"
    for run, carril in ((a, "uno"), (b, "dos")):
        run.mkdir()
        (run / "STATE.md").write_text(f"- 2026-11-17 09:0{len(carril)} {carril} iniciado\n")
        (run / "carriles.json").write_text(json.dumps({carril: {"nombre": carril, "tipo": "claude"}}))
    escribir_estado(tmp_path, {"uno": {"status": "working"}, "coord-b": {"status": "idle"}})
    d = tablero.estado(
        {"a": {"repo": str(tmp_path / "a"), "run": str(a)}, "b": {"repo": str(tmp_path / "b"), "run": str(b)}}, "s"
    )
    assert {(f["nombre"], f["proyecto"], f["columna"]) for f in d["carriles"]} == {
        ("uno", "a", "trabajando"),
        ("dos", "b", "quieto"),
    }
    assert [(o["nombre"], o["proyecto"]) for o in d["otros"]] == [("coord-b", "b")]
    assert {p["nombre"]: p["coordinador"] for p in d["proyectos"]} == {"a": None, "b": "idle"}
    assert [x.split(" · ")[0][-1] for x in d["bitacora"]] == ["a", "b"], "bitácora mezclada y en orden de hora"


def test_boton_coordinador_solo_para_proyectos_registrados(servidor, tmp_path):
    json_tok = {"Content-Type": "application/json", "X-Flota-Token": "secreto"}
    assert pedir(f"{servidor}/api/coordinador", {"proyecto": "otro"}, json_tok)[0] == 404
    codigo, cuerpo = pedir(f"{servidor}/api/coordinador", {"proyecto": "demo"}, json_tok)
    assert codigo == 200, cuerpo
    assert any(x[:3] == ["agent", "start", "coord-demo"] for x in llamadas(tmp_path))
