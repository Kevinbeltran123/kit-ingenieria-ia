"""vivo_documentos.py: detecta los .md y .html que cambian, con título, tamaño y líneas, y salta el ruido."""

from __future__ import annotations

import os
import time

import vivo_documentos


def contexto(tmp_path, *raices, desde=None, proyectos=None):
    return {
        "ahora": time.time(),
        "desde": time.time() - 3600 if desde is None else desde,
        "proyectos": proyectos or {},
        "agentes": [],
        "raices": [{"ruta": str(r), "proyecto": "p", "agente": a} for r, a in raices],
    }


def escribir(ruta, texto="hola\n"):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto)
    return ruta


def test_detecta_md_con_encabezado_tamano_y_lineas(tmp_path):
    ruta = escribir(tmp_path / "diseno-t21.md", "intro\n# Diseño de T21\n\ncuerpo\n")
    productos = vivo_documentos.detectar(contexto(tmp_path, (tmp_path, "palma")))
    assert len(productos) == 1
    p = productos[0]
    assert p["tipo"] == "documento"
    assert p["id"] == f"documento:{ruta}"
    assert p["agente"] == "palma"
    assert p["titulo"] == "diseno-t21.md: Diseño de T21"
    assert p["datos"] == {"archivo": str(ruta), "formato": "md", "tamano": ruta.stat().st_size, "lineas": 4}


def test_md_sin_encabezado_y_encabezado_dentro_de_codigo(tmp_path):
    escribir(tmp_path / "a.md", "texto\n```\n# comentario de shell\n```\n")
    productos = vivo_documentos.detectar(contexto(tmp_path, (tmp_path, None)))
    assert productos[0]["titulo"] == "a.md"


def test_html_usa_solo_el_nombre(tmp_path):
    escribir(tmp_path / "informe.html", "<h1>x</h1>")
    p = vivo_documentos.detectar(contexto(tmp_path, (tmp_path, None)))[0]
    assert p["titulo"] == "informe.html"
    assert p["datos"]["formato"] == "html"
    assert p["datos"]["lineas"] == 1


def test_ventana_y_orden_por_cambio(tmp_path):
    viejo = escribir(tmp_path / "viejo.md")
    medio = escribir(tmp_path / "medio.md")
    nuevo = escribir(tmp_path / "nuevo.md")
    ahora = time.time()
    os.utime(viejo, (ahora - 7200, ahora - 7200))
    os.utime(medio, (ahora - 100, ahora - 100))
    productos = vivo_documentos.detectar(contexto(tmp_path, (tmp_path, None)))
    assert [p["datos"]["archivo"] for p in productos] == [str(nuevo), str(medio)]


def test_salta_carpetas_de_dependencias_y_ruido(tmp_path):
    for sucio in (
        ".git/x.md",
        "node_modules/m/README.md",
        ".venv/l/README.md",
        "dist/o.md",
        "build/o.md",
        ".claude/notas.md",
        ".pytest_cache/README.md",
        "CHANGELOG.md",
        "changelog.html",
    ):
        escribir(tmp_path / sucio)
    escribir(tmp_path / "README.md")
    productos = vivo_documentos.detectar(contexto(tmp_path, (tmp_path, None)))
    assert [p["titulo"] for p in productos] == ["README.md"]


def test_html_enorme_se_excluye(tmp_path):
    grande = tmp_path / "generado.html"
    with grande.open("wb") as f:
        f.truncate(vivo_documentos.TAMANO_MAXIMO + 1)
    escribir(tmp_path / "chico.html")
    productos = vivo_documentos.detectar(contexto(tmp_path, (tmp_path, None)))
    assert [p["titulo"] for p in productos] == ["chico.html"]


def test_wt_de_la_corrida_se_salta_y_el_worktree_es_su_raiz(tmp_path):
    run = tmp_path / "repo-flota"
    escribir(run / "diseno-t21.md", "# Diseño\n")
    wt = run / "wt" / "palma"
    escribir(wt / "handover.md", "# Handover\n")
    ctx = contexto(
        tmp_path, (wt, "palma"), (run, None), proyectos={"p": {"repo": str(tmp_path / "x"), "run": str(run)}}
    )
    productos = vivo_documentos.detectar(ctx)
    por_archivo = {p["titulo"]: p["agente"] for p in productos}
    assert por_archivo == {"handover.md: Handover": "palma", "diseno-t21.md: Diseño": None}


def test_raices_anidadas_no_repiten_documentos(tmp_path):
    escribir(tmp_path / "sub" / "a.md")
    productos = vivo_documentos.detectar(contexto(tmp_path, (tmp_path / "sub", "ag"), (tmp_path, None)))
    assert len(productos) == 1
    assert productos[0]["agente"] == "ag"


def test_tope_de_entradas_y_raiz_inexistente(tmp_path, monkeypatch):
    for i in range(10):
        escribir(tmp_path / f"d{i}.md")
    monkeypatch.setattr(vivo_documentos, "TOPE_ENTRADAS", 3)
    productos = vivo_documentos.detectar(contexto(tmp_path, (tmp_path, None), (tmp_path / "no-existe", None)))
    assert len(productos) <= 3


def test_archivo_ilegible_se_salta(tmp_path):
    secreto = escribir(tmp_path / "secreto.md")
    escribir(tmp_path / "ok.md")
    secreto.chmod(0)
    try:
        productos = vivo_documentos.detectar(contexto(tmp_path, (tmp_path, None)))
    finally:
        secreto.chmod(0o644)
    assert "ok.md" in [p["titulo"] for p in productos]
