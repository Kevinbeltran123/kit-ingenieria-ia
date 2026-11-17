"""vivo.py y sus rutas: contexto con raíces sin repetir, detectores aislados y archivos servidos solo si se puede."""

from __future__ import annotations

import json
import sys
import threading
import types
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
import tablero
import vivo


def proyecto(tmp_path, nombre="demo"):
    repo = tmp_path / nombre
    run = tmp_path / f"{nombre}-flota"
    wt = run / "wt" / "api"
    for d in (repo, wt):
        d.mkdir(parents=True)
    (run / "carriles.json").write_text(
        json.dumps({"api": {"nombre": "api", "worktree": str(wt), "tipo": "claude", "sesion_agente": "u-1"}})
    )
    return {nombre: {"repo": str(repo), "run": str(run)}}, repo, run, wt


def test_contexto_raices_y_agentes(tmp_path, falsos):
    proyectos, repo, run, wt = proyecto(tmp_path)
    (tmp_path / "estado.json").write_text(json.dumps({"agentes": {"coord-demo": {"status": "idle"}}}))
    ctx = vivo.contexto("s", proyectos)
    rutas = [r["ruta"] for r in ctx["raices"]]
    assert rutas == [str(wt.resolve()), str(repo.resolve()), str(run.resolve())], "worktrees primero, sin repetir"
    assert ctx["raices"][0]["agente"] == "api"
    assert {a["nombre"] for a in ctx["agentes"]} == {"api", "coord-demo"}
    assert ctx["desde"] < ctx["ahora"]


def test_ruta_permitida(tmp_path, falsos):
    proyectos, repo, _run, _wt = proyecto(tmp_path)
    ctx = vivo.contexto("s", proyectos)
    (repo / "fig.png").write_bytes(b"png")
    (repo / "secreto.env").write_text("x")
    afuera = tmp_path / "afuera.png"
    afuera.write_bytes(b"png")
    (repo / "atajo.png").symlink_to(afuera)
    assert vivo.ruta_permitida(str(repo / "fig.png"), ctx) == (repo / "fig.png").resolve()
    assert vivo.ruta_permitida(str(repo / "secreto.env"), ctx) is None, "extensión no permitida"
    assert vivo.ruta_permitida(str(afuera), ctx) is None, "fuera de las raíces"
    assert vivo.ruta_permitida(str(repo / "atajo.png"), ctx) is None, "un enlace que sale de la raíz no vale"
    assert vivo.ruta_permitida(str(repo / ".." / "afuera.png"), ctx) is None
    assert vivo.ruta_permitida(str(repo / "no-existe.png"), ctx) is None


def test_un_detector_roto_no_tumba_a_los_demas(monkeypatch):
    bueno = types.SimpleNamespace(detectar=lambda ctx: [{"id": "a", "tipo": "codigo", "t": 2}, {"sin": "id"}])
    roto = types.SimpleNamespace(detectar=lambda ctx: 1 / 0)
    monkeypatch.setitem(sys.modules, "vivo_prueba_bueno", bueno)
    monkeypatch.setitem(sys.modules, "vivo_prueba_roto", roto)
    monkeypatch.setattr(vivo, "DETECTORES", ("vivo_prueba_bueno", "vivo_prueba_roto", "vivo_no_existe"))
    monkeypatch.setattr(vivo, "_cache", {})
    r = vivo.recolectar({"ahora": 100.0})
    assert [p["id"] for p in r["productos"]] == ["a"]
    assert "ZeroDivisionError" in r["errores"]["vivo_prueba_roto"]
    assert "vivo_no_existe" not in r["errores"]


@pytest.fixture
def servidor(tmp_path, falsos):
    proyectos, repo, _run, _wt = proyecto(tmp_path)
    (repo / "fig.png").write_bytes(b"\x89PNG")
    (repo / "informe.html").write_text("<script>alert(1)</script>")
    vivo._cache.clear()
    tablero.Tablero.ctx = {"fijos": proyectos, "sesion": "s", "token": "secreto"}
    srv = ThreadingHTTPServer(("127.0.0.1", 0), tablero.Tablero)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", repo
    srv.shutdown()


def pedir(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def test_paginas_y_vistas(servidor):
    base, _repo = servidor
    codigo, _, cuerpo = pedir(f"{base}/?t=secreto")
    assert codigo == 200
    assert b"<title>Flota</title>" in cuerpo, "la portada es el tablero de carriles"
    assert b"<title>En vivo</title>" in pedir(f"{base}/vivo?t=secreto")[2]
    codigo, cab, _ = pedir(f"{base}/vivo/vivo-noexiste.js")
    assert codigo == 200
    assert cab["Content-Type"].startswith("text/javascript")
    assert pedir(f"{base}/vivo/..%2Fcarril.py")[2] == b"/* vista no instalada */"


def test_api_vivo_y_archivos(servidor):
    base, repo = servidor
    assert pedir(f"{base}/api/vivo")[0] == 403, "sin token no hay datos"
    codigo, _, cuerpo = pedir(f"{base}/api/vivo?t=secreto")
    assert codigo == 200
    assert set(json.loads(cuerpo)) >= {"ahora", "productos", "errores"}
    ruta = urllib.request.quote(str(repo / "fig.png"))
    codigo, cab, cuerpo = pedir(f"{base}/api/vivo/archivo?ruta={ruta}&t=secreto")
    assert (codigo, cab["Content-Type"], cuerpo) == (200, "image/png", b"\x89PNG")
    html = urllib.request.quote(str(repo / "informe.html"))
    codigo, cab, _ = pedir(f"{base}/api/vivo/archivo?ruta={html}&t=secreto")
    assert codigo == 200
    assert cab["Content-Security-Policy"] == "sandbox", "el HTML del agente no corre scripts"
    fuera = urllib.request.quote(str(Path.home() / ".zshrc"))
    assert pedir(f"{base}/api/vivo/archivo?ruta={fuera}&t=secreto")[0] == 404
    assert pedir(f"{base}/api/vivo/archivo?ruta={ruta}")[0] == 403
