"""construir.py: no arma nada a medias, y lo que arma no depende de internet."""

from __future__ import annotations

import json
import re

from ayudas import SCRIPTS, carpeta, completar, correr, git, guardar, leer

RECOLECTAR, CONSTRUIR = SCRIPTS / "recolectar.py", SCRIPTS / "construir.py"
RECURSO_EXTERNO = re.compile(r"""(src|href)\s*=\s*["']https?:|url\(\s*["']?https?:|@import""")


def preparar(repo, **kw) -> dict:
    assert correr(RECOLECTAR, repo).returncode == 0
    return completar(repo, **kw)


def test_arma_el_html_sin_recursos_de_internet(repo):
    preparar(repo)
    r = correr(CONSTRUIR, repo)
    assert r.returncode == 0, r.stderr
    htmls = list(carpeta(repo).glob("*.html"))
    assert len(htmls) == 1
    pagina = htmls[0].read_text()
    assert "Agrega multiplicar" in pagina
    assert RECURSO_EXTERNO.search(pagina) is None
    assert "font/woff2;base64," in pagina
    ultimo = leer(repo, "ultimo.json")
    assert ultimo["hasta"] == git(repo, "rev-parse", "HEAD")
    assert ultimo["alertas"] == []
    assert (repo / ".explicaciones" / "index.html").is_file()


def test_si_falta_una_nota_dice_cual_y_no_arma_nada(repo):
    textos = preparar(repo)
    del textos["pasos"][1]["notas"]["11"]
    guardar(repo, textos)
    r = correr(CONSTRUIR, repo)
    assert r.returncode == 1
    assert "paso 2 (calc.py): falta nota para la línea 11" in r.stderr
    assert not list(carpeta(repo).glob("*.html"))


def test_acepta_rangos_de_lineas(repo):
    textos = preparar(repo)
    textos["pasos"][1]["notas"] = {"10-11": "La función nueva completa."}
    guardar(repo, textos)
    assert correr(CONSTRUIR, repo).returncode == 0


def test_una_nota_fuera_del_paso_es_un_error(repo):
    textos = preparar(repo)
    textos["pasos"][0]["notas"]["99"] = "No existe."
    guardar(repo, textos)
    r = correr(CONSTRUIR, repo)
    assert r.returncode == 1
    assert "apunta fuera del paso" in r.stderr


def test_falta_el_resumen(repo):
    textos = preparar(repo)
    textos["resumen"]["como_se_probo"] = ""
    guardar(repo, textos)
    r = correr(CONSTRUIR, repo)
    assert r.returncode == 1
    assert "resumen.como_se_probo" in r.stderr


def test_tras_un_commit_nuevo_pide_recolectar_otra_vez(repo):
    preparar(repo)
    (repo / "config.yml").write_text("nombre: otra\n")
    git(repo, "commit", "-q", "-am", "otro cambio")
    r = correr(CONSTRUIR, repo)
    assert r.returncode == 1
    assert "corre recolectar.py otra vez" in r.stderr


def test_un_commit_viejo_se_puede_explicar_aunque_haya_otros_despues(repo):
    sha = git(repo, "rev-parse", "HEAD")
    assert correr(RECOLECTAR, repo, "--commit", sha).returncode == 0
    destino = repo / ".explicaciones" / "commits" / sha[:7]
    textos = json.loads((destino / "textos.json").read_text())
    textos["titulo"] = "Agrega multiplicar"
    textos["resumen"].update(problema="p", solucion="s", como_se_probo="c")
    for paso in textos["pasos"]:
        paso.update(
            titulo="t",
            explicacion="e",
            notas={str(n): "n" for n in paso["lineas_nuevas"]},
            notas_borradas={str(n): "b" for n in paso["lineas_borradas"]},
        )
    (destino / "textos.json").write_text(json.dumps(textos))
    (repo / "config.yml").write_text("nombre: otra\n")
    git(repo, "commit", "-q", "-am", "otro cambio")
    r = correr(CONSTRUIR, repo, str(destino))
    assert r.returncode == 0, r.stderr
    assert "commits/" + sha[:7] in (repo / ".explicaciones" / "index.html").read_text()
    # Con la ruta relativa que imprime recolectar.py (desde la raíz del repo) también funciona.
    r = correr(CONSTRUIR, repo, f".explicaciones/commits/{sha[:7]}")
    assert r.returncode == 0, r.stderr


def test_alerta_descartada_necesita_motivo(repo):
    preparar(repo, alerta={"tipo": "bug", "estado": "descartada", "texto": "divide por cero"})
    r = correr(CONSTRUIR, repo)
    assert r.returncode == 1
    assert "necesita 'motivo'" in r.stderr


def test_el_codigo_explicado_puede_contener_los_marcadores(repo):
    (repo / "notas.md").write_text("__DATOS__ y /*__FUENTES__*/ y __TITULO__ y </script>\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "marcadores")
    preparar(repo)
    assert correr(CONSTRUIR, repo).returncode == 0
    pagina = next(carpeta(repo).glob("*.html")).read_text()
    crudo = re.search(r'<script type="application/json" id="datos">(.*?)</script>', pagina, re.S).group(1)
    datos = json.loads(crudo.replace("<\\/", "</"))
    lineas = [l["c"] for a in datos["archivos"] if a["ruta"] == "notas.md" for l in a["lineas"]]
    assert lineas == ["__DATOS__ y /*__FUENTES__*/ y __TITULO__ y </script>"]
