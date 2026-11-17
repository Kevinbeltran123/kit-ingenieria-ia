"""vivo_web.py: detecta servidores de desarrollo de los proyectos del contexto, sin lsof real."""

from __future__ import annotations

import os

import vivo_web


def _ctx(raiz, agente="palma-ui"):
    return {"ahora": 2000.0, "desde": 1000.0, "raices": [{"ruta": str(raiz), "proyecto": "arco", "agente": agente}]}


def _escucha(*sockets):
    return lambda: [{"pid": p, "comando": c, "puerto": n, "host": "127.0.0.1"} for p, c, n in sockets]


def _fecha(ruta, t):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("x")
    os.utime(ruta, (t, t))
    return str(ruta)


def test_detecta_servidor_bajo_raiz_con_archivos_cambiados(tmp_path):
    nuevo = _fecha(tmp_path / "src" / "App.tsx", 1900)
    _fecha(tmp_path / "src" / "viejo.css", 500)  # fuera de la ventana
    _fecha(tmp_path / "node_modules" / "x" / "i.js", 1950)  # se salta
    _fecha(tmp_path / "notas.md", 1990)  # no es código web
    r = vivo_web.detectar(_ctx(tmp_path), _escucha((10, "node", 5173)), lambda pid: str(tmp_path))
    assert len(r) == 1
    p = r[0]
    assert (p["id"], p["tipo"], p["proyecto"], p["agente"], p["t"]) == ("web:5173", "web", "arco", "palma-ui", 1900)
    assert p["titulo"] == "arco · 5173"
    assert p["datos"] == {
        "url": "http://127.0.0.1:5173/",
        "puerto": 5173,
        "cwd": str(tmp_path),
        "ultimo_cambio": 1900,
        "archivos": [nuevo],
    }


def test_sin_cambios_deja_ultimo_cambio_en_none(tmp_path):
    r = vivo_web.detectar(_ctx(tmp_path), _escucha((10, "vite", 5173)), lambda pid: str(tmp_path / "web"))
    assert r[0]["datos"]["ultimo_cambio"] is None
    assert r[0]["datos"]["archivos"] == []


def test_filtra_cwd_ajeno_puertos_del_tablero_y_comandos_no_web(tmp_path):
    ajeno = tmp_path.parent / "otro"
    escucha = _escucha(
        (1, "node", 3000), (2, "Python", 8790), (3, "node", 8791), (4, "postgres", 5432), (5, "node", 4000)
    )
    cwds = {1: str(ajeno), 2: str(tmp_path), 3: str(tmp_path), 4: str(tmp_path), 5: str(tmp_path)}
    r = vivo_web.detectar(_ctx(tmp_path), escucha, cwds.get)
    assert [p["id"] for p in r] == ["web:4000"]


def test_un_puerto_repetido_en_ipv4_e_ipv6_cuenta_una_vez(tmp_path):
    r = vivo_web.detectar(_ctx(tmp_path), _escucha((1, "node", 5173), (1, "node", 5173)), lambda pid: str(tmp_path))
    assert len(r) == 1


def test_gana_la_raiz_mas_especifica(tmp_path):
    ctx = _ctx(tmp_path, agente=None)
    ctx["raices"].append({"ruta": str(tmp_path / "wt" / "ui"), "proyecto": "arco", "agente": "ui"})
    (tmp_path / "wt" / "ui").mkdir(parents=True)
    _fecha(tmp_path / "wt" / "ui" / "a.js", 1800)
    r = vivo_web.detectar(ctx, _escucha((1, "node", 5173)), lambda pid: str(tmp_path / "wt" / "ui"))
    assert r[0]["agente"] == "ui"
    assert r[0]["datos"]["ultimo_cambio"] == 1800
    # al recorrer la raíz general se salta wt/
    assert vivo_web._cambios(str(tmp_path), 0) == []


def test_sockets_escucha_parsea_el_formato_f(monkeypatch):
    salida = "p10\ncnode\nn127.0.0.1:5173\nn[::1]:5173\np20\ncpostgres\nn*:5432\np30\ncnode\nn192.168.1.5:3000\n"
    monkeypatch.setattr(vivo_web, "_lsof", lambda args: salida)
    r = vivo_web.sockets_escucha()
    assert [(s["pid"], s["comando"], s["puerto"]) for s in r] == [
        (10, "node", 5173),
        (10, "node", 5173),
        (20, "postgres", 5432),
    ]


def test_cwd_de_y_lsof_ausente(monkeypatch):
    monkeypatch.setattr(vivo_web, "_lsof", lambda args: "p10\nfcwd\nn/ruta/proyecto\n")
    assert vivo_web.cwd_de(10) == "/ruta/proyecto"
    monkeypatch.undo()
    monkeypatch.setattr(vivo_web.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError()))
    assert vivo_web.sockets_escucha() == []
    assert vivo_web.cwd_de(10) is None
