"""recolectar.py: lo que sale de git, agrupado en pasos por bloque o método."""

from __future__ import annotations

import json

from ayudas import NUEVO, SCRIPTS, carpeta, correr, git, leer

RECOLECTAR = SCRIPTS / "recolectar.py"


def test_arma_un_paso_por_metodo_y_omite_lockfiles(repo):
    r = correr(RECOLECTAR, repo)
    assert r.returncode == 0, r.stderr
    datos = leer(repo, "datos.json")
    assert [a["ruta"] for a in datos["archivos"]] == ["calc.py", "config.yml"]
    assert [o["ruta"] for o in datos["omitidos"]] == ["uv.lock"]
    assert datos["hasta"] == git(repo, "rev-parse", "HEAD")
    pasos = [
        (p["archivo"], p["contexto"], p["lineas_nuevas"], p["lineas_borradas"])
        for p in leer(repo, "textos.json")["pasos"]
    ]
    assert pasos == [
        ("calc.py", "def sumar()", [2], []),
        ("calc.py", "def multiplicar()", [10, 11], []),
        ("config.yml", "", [1], []),
    ]


def test_el_codigo_para_leer_trae_numeros_reales(repo):
    correr(RECOLECTAR, repo)
    paso = leer(repo, "textos.json")["pasos"][1]
    assert "+    10 | def multiplicar(a, b):" in paso["codigo"]


def test_la_carpeta_queda_fuera_de_git(repo):
    correr(RECOLECTAR, repo)
    assert ".explicaciones/" in (repo / ".git" / "info" / "exclude").read_text().split()
    assert git(repo, "status", "--porcelain") == ""


def test_lineas_borradas_piden_su_nota(repo):
    (repo / "calc.py").write_text('def sumar(a, b):\n    """Suma dos números."""\n    return a + b\n')
    git(repo, "commit", "-q", "-am", "quita restar y multiplicar")
    correr(RECOLECTAR, repo)
    borradas = [p for p in leer(repo, "textos.json")["pasos"] if p["lineas_borradas"]]
    assert [(p["contexto"], p["lineas_borradas"]) for p in borradas] == [("def restar()", [5, 6])]


def test_si_cambia_la_firma_la_version_vieja_va_con_la_nueva(repo):
    (repo / "calc.py").write_text(NUEVO.replace("def restar(a, b):", "def restar(a, b, redondear=False):"))
    git(repo, "commit", "-q", "-am", "restar redondea")
    correr(RECOLECTAR, repo)
    pasos = [p for p in leer(repo, "textos.json")["pasos"] if p["contexto"].startswith("def restar")]
    assert len(pasos) == 1
    assert pasos[0]["lineas_nuevas"] == [6] and pasos[0]["lineas_borradas"] == [5]


def test_sin_commit_incluye_cambios_y_archivos_nuevos(repo):
    (repo / "calc.py").write_text(NUEVO + "\n\ndef dividir(a, b):\n    return a / b\n")
    (repo / "nuevo.py").write_text("X = 1\n")
    r = correr(RECOLECTAR, repo, "--sin-commit")
    assert r.returncode == 0, r.stderr
    pasos = leer(repo, "textos.json")["pasos"]
    assert "def dividir()" in [p["contexto"] for p in pasos]
    assert "nuevo.py" in [p["archivo"] for p in pasos]
    assert leer(repo, "datos.json")["hasta"] is None


def test_un_archivo_largo_se_parte_por_funciones(repo):
    funciones = "\n\n".join(
        f"def f{k}():\n" + "\n".join(f"    x{j} = {j}" for j in range(25)) + "\n    return 0" for k in range(3)
    )
    (repo / "largo.py").write_text(funciones + "\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "largo")
    correr(RECOLECTAR, repo)
    largos = [p for p in leer(repo, "textos.json")["pasos"] if p["archivo"] == "largo.py"]
    assert [p["contexto"] for p in largos] == ["def f0()", "def f1()", "def f2()"]


def test_volver_a_recolectar_guarda_los_textos_anteriores(repo):
    correr(RECOLECTAR, repo)
    correr(RECOLECTAR, repo)
    assert (carpeta(repo) / "textos.anterior.json").is_file()


def test_un_commit_puntual_se_explica_solo(repo):
    (repo / "config.yml").write_text("nombre: calculadora\nversion: 2\n")
    git(repo, "commit", "-q", "-am", "agrega versión")
    sha = git(repo, "rev-parse", "HEAD")
    r = correr(RECOLECTAR, repo, "--commit", "HEAD")
    assert r.returncode == 0, r.stderr
    destino = repo / ".explicaciones" / "commits" / sha[:7]
    datos = json.loads((destino / "datos.json").read_text())
    assert datos["commit"] == {"sha": sha, "asunto": "agrega versión"}
    assert [a["ruta"] for a in datos["archivos"]] == ["config.yml"]
    assert f"construir.py .explicaciones/commits/{sha[:7]}" in r.stdout


def test_sin_cambios_lo_dice(repo):
    git(repo, "checkout", "-q", "main")
    r = correr(RECOLECTAR, repo)
    assert r.returncode != 0
    assert "No hay cambios para explicar" in r.stderr
