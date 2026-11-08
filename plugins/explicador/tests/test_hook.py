"""exigir_explicacion.py: el PR pide una explicación del commit actual y sin errores abiertos."""

from __future__ import annotations

import json

from ayudas import HOOK, SCRIPTS, completar, correr, git

RECOLECTAR, CONSTRUIR = SCRIPTS / "recolectar.py", SCRIPTS / "construir.py"


def entrada(raiz, comando: str) -> str:
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": comando}, "cwd": str(raiz)})


def explicar(repo, alerta=None) -> None:
    assert correr(RECOLECTAR, repo).returncode == 0
    completar(repo, alerta=alerta)
    r = correr(CONSTRUIR, repo)
    assert r.returncode == 0, r.stderr


def test_sin_explicacion_bloquea_el_pr(repo):
    r = correr(HOOK, repo, entrada=entrada(repo, "gh pr create --fill"))
    assert r.returncode == 2
    assert "explicar-cambios" in r.stderr


def test_con_explicacion_del_commit_actual_deja_pasar(repo):
    explicar(repo)
    r = correr(HOOK, repo, entrada=entrada(repo, "git push -u origin HEAD && gh pr create --fill"))
    assert r.returncode == 0, r.stderr


def test_explicacion_de_otro_commit_bloquea(repo):
    explicar(repo)
    (repo / "config.yml").write_text("nombre: otra\n")
    git(repo, "commit", "-q", "-am", "otro cambio")
    r = correr(HOOK, repo, entrada=entrada(repo, "gh pr create"))
    assert r.returncode == 2
    assert "Vuelve a generarla" in r.stderr


def test_error_abierto_bloquea_y_descartado_con_motivo_deja_pasar(repo):
    explicar(repo, alerta={"tipo": "bug", "estado": "abierta", "texto": "divide por cero"})
    r = correr(HOOK, repo, entrada=entrada(repo, "gh pr create"))
    assert r.returncode == 2
    assert "divide por cero" in r.stderr

    explicar(repo, alerta={"tipo": "bug", "estado": "descartada", "texto": "divide por cero",
                           "motivo": "Kevin: b nunca es 0 aquí"})
    assert correr(HOOK, repo, entrada=entrada(repo, "gh pr create")).returncode == 0


def test_un_riesgo_abierto_no_bloquea(repo):
    explicar(repo, alerta={"tipo": "riesgo", "estado": "abierta", "texto": "lento con listas grandes"})
    assert correr(HOOK, repo, entrada=entrada(repo, "gh pr create")).returncode == 0


def test_otros_comandos_no_se_revisan(repo):
    assert correr(HOOK, repo, entrada=entrada(repo, "git push origin HEAD")).returncode == 0
    assert correr(HOOK, repo, entrada=entrada(repo, "gh pr view 3")).returncode == 0


def test_la_persona_puede_desactivarlo(repo):
    assert correr(HOOK, repo, entrada=entrada(repo, "gh pr create"), env={"EXPLICADOR_DESACTIVAR": "1"}).returncode == 0
    (repo / ".claude").mkdir()
    (repo / ".claude" / "explicador.json").write_text('{"desactivar": true}')
    assert correr(HOOK, repo, entrada=entrada(repo, "gh pr create")).returncode == 0


def test_una_entrada_rara_no_bloquea(repo):
    assert correr(HOOK, repo, entrada="esto no es json").returncode == 0
