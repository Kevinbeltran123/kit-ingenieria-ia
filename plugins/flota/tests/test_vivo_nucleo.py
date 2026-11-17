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


def ctx_de(tmp_path):
    repo, wt = tmp_path / "repo", tmp_path / "repo-flota" / "wt" / "api"
    return {"ahora": 100.0, "agentes": [{"nombre": "api", "proyecto": "demo"}],
            "raices": [{"ruta": str(wt), "proyecto": "demo", "agente": "api"},
                       {"ruta": str(repo), "proyecto": "demo", "agente": None}]}  # fmt: skip


def prod(tipo, agente=None, t=1.0, **datos):
    return {"id": f"{tipo}:{datos}", "tipo": tipo, "agente": agente, "proyecto": "demo", "t": t, "titulo": tipo,
            "datos": datos}  # fmt: skip


def test_agrupar_solo_lo_que_produjo_un_agente(tmp_path):
    ctx = ctx_de(tmp_path)
    repo = str(tmp_path / "repo")
    productos = [
        prod("codigo", "api", 5, archivo=f"{repo}/docs/diseno.md", mas=10, menos=0),
        prod("documento", None, 5, archivo=f"{repo}/docs/diseno.md"),  # lo escribió api: cuenta
        prod("documento", None, 6, archivo=f"{repo}/README.md"),  # nadie lo tocó: fuera
        prod("comando", "api", 4, comando="just entrenar tabla runs/e004"),
        prod("metricas", None, 7, archivo=f"{repo}/runs/e004/metrics.csv"),  # su carpeta sale en un comando: cuenta
        prod("metricas", None, 3, archivo=f"{repo}/runs/viejo/metrics.csv"),  # nadie la lanzó: queda del proyecto
        prod("web", None, 2, url="http://127.0.0.1:5173/"),  # servidor de la persona: del proyecto
        prod("documento", "api", 8, archivo=f"{repo}/.explicaciones/x/index.html"),  # carpeta oculta: ruido
    ]
    g = vivo.agrupar(ctx, productos, {"api": "working", "otro": "idle"})
    api = g["carriles"][0]
    assert api["nombre"] == "api" and api["estado"] == "working"
    assert [p["tipo"] for p in api["productos"]] == ["metricas", "documento"], "lo más reciente primero"
    assert api["principal"] == api["productos"][0]["id"]
    assert [a["archivo"] for a in api["archivos"]] == [f"{repo}/docs/diseno.md"]
    assert {p["tipo"] for p in g["proyecto"]} == {"metricas", "web"}
    assert all("README" not in str(p["datos"]) for c in g["carriles"] for p in c["productos"])


def test_agentes_sin_productos_siguen_visibles(tmp_path):
    ctx = ctx_de(tmp_path)
    g = vivo.agrupar(ctx, [], {"api": "working"})
    assert [(c["nombre"], c["principal"]) for c in g["carriles"]] == [("api", None)]


def test_imagenes_de_solo_carpetas_permitidas(tmp_path):
    carpeta = tmp_path / "repo" / "runs" / "e1" / "recortes"
    carpeta.mkdir(parents=True)
    for i in range(3):
        (carpeta / f"p{i}.png").write_bytes(b"x")
    (carpeta / "nota.txt").write_text("x")
    ctx = ctx_de(tmp_path)
    assert len(vivo.imagenes_de(str(carpeta), ctx)) == 3
    afuera = tmp_path / "afuera"
    afuera.mkdir()
    assert vivo.imagenes_de(str(afuera), ctx) == []


def test_ruta_carriles(servidor):
    base, _repo = servidor
    codigo, _, cuerpo = pedir(f"{base}/api/vivo/carriles?t=secreto")
    assert codigo == 200
    assert set(json.loads(cuerpo)) >= {"carriles", "proyecto", "ahora"}
    assert pedir(f"{base}/api/vivo/carriles")[0] == 403
