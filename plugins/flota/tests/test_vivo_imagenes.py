from __future__ import annotations

import os

import vivo_imagenes

AHORA = 1_800_000_000.0


def imagen(ruta, t):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(b"x")
    os.utime(ruta, (t, t))
    return str(ruta)


def ctx_de(raices, proyectos=None):
    return {"ahora": AHORA, "desde": AHORA - 3600, "proyectos": proyectos or {}, "agentes": [], "raices": raices}


def test_agrupa_por_carpeta_y_ordena(tmp_path):
    for i in range(15):
        imagen(tmp_path / "runs/e004/recortes" / f"r{i:02}.png", AHORA - 100 + i)
    imagen(tmp_path / "runs/e004/recortes/vieja.jpg", AHORA - 99999)
    imagen(tmp_path / "figuras/a.webp", AHORA - 10)
    (tmp_path / "notas.txt").write_text("no es imagen")
    r = vivo_imagenes.detectar(ctx_de([{"ruta": str(tmp_path), "proyecto": "p", "agente": "ag"}]))
    assert [p["datos"]["carpeta"] for p in r] == [str(tmp_path / "figuras"), str(tmp_path / "runs/e004/recortes")]
    p = r[1]
    assert p["id"] == f"imagenes:{tmp_path}/runs/e004/recortes"
    assert (p["proyecto"], p["agente"], p["tipo"]) == ("p", "ag", "imagenes")
    assert p["datos"]["total"] == 16 and p["datos"]["nuevas"] == 15
    assert len(p["datos"]["recientes"]) == 12
    assert p["datos"]["recientes"][0].endswith("r14.png") and p["t"] == AHORA - 86
    assert p["titulo"] == "15 imágenes nuevas en runs/e004/recortes (16 en total)"


def test_salta_caches_y_wt_de_la_corrida_y_raices_anidadas(tmp_path):
    run = tmp_path / "run"
    imagen(run / "wt/ag/x.png", AHORA - 5)
    imagen(run / "out/y.png", AHORA - 5)
    imagen(tmp_path / "repo/node_modules/z.png", AHORA - 5)
    imagen(tmp_path / "repo/.git/w.png", AHORA - 5)
    imagen(tmp_path / "repo/sub/hondo/v.png", AHORA - 5)
    raices = [{"ruta": str(run / "wt/ag"), "proyecto": "p", "agente": "ag"},
              {"ruta": str(run), "proyecto": "p", "agente": None},
              {"ruta": str(tmp_path / "repo"), "proyecto": "p", "agente": None}]  # fmt: skip
    r = vivo_imagenes.detectar(ctx_de(raices, {"p": {"repo": str(tmp_path / "repo"), "run": str(run)}}))
    assert {p["datos"]["carpeta"]: p["agente"] for p in r} == {
        str(run / "wt/ag"): "ag",
        str(run / "out"): None,
        str(tmp_path / "repo/sub/hondo"): None,
    }


def test_profundidad_y_raiz_inexistente(tmp_path):
    imagen(tmp_path.joinpath(*"abcdefgh") / "tope.png", AHORA - 5)
    r = vivo_imagenes.detectar(ctx_de([{"ruta": str(tmp_path), "proyecto": "p", "agente": None},
                                       {"ruta": str(tmp_path / "no"), "proyecto": "p", "agente": None}]))  # fmt: skip
    assert r == []


def test_tope_de_entradas(tmp_path, monkeypatch):
    monkeypatch.setattr(vivo_imagenes, "MAX_ENTRADAS", 25)
    for i in range(20):
        imagen(tmp_path / f"d{i}/i.png", AHORA - 5)
    r = vivo_imagenes.detectar(ctx_de([{"ruta": str(tmp_path), "proyecto": "p", "agente": None}]))
    assert 0 < len(r) < 20
