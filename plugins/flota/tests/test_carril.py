"""carril.py: argumentos por nivel de permisos, diálogos de arranque, registro del carril y commit del coordinador."""

from __future__ import annotations

import json

import carril
import pytest
from ayudas_flota import SCRIPTS, correr, git, llamadas, preparar_falsos

CARRIL = SCRIPTS / "carril.py"


@pytest.mark.parametrize(
    ("tipo", "permisos", "esperado"),
    [
        ("claude", "auto", ["--permission-mode", "auto"]),
        ("claude", "abierto", ["--permission-mode", "bypassPermissions"]),
        ("claude", "preguntar", []),
        ("codex", "auto", ["-s", "workspace-write", "-a", "never"]),
        ("codex", "abierto", ["-s", "danger-full-access", "-a", "never"]),
        ("codex", "preguntar", ["-s", "workspace-write", "-a", "on-request"]),
    ],
)
def test_argumentos_por_permisos(tipo, permisos, esperado):
    args = carril.argumentos_agente(tipo, None, None, permisos, None)
    assert args == esperado


def test_argumentos_con_modelo_y_esfuerzo():
    assert carril.argumentos_agente("claude", "claude-opus-5-5", "high", "auto", "u-1") == [
        "--session-id", "u-1", "--model", "claude-opus-5-5", "--effort", "high", "--permission-mode", "auto",
    ]  # fmt: skip
    assert carril.argumentos_agente("codex", "gpt-6-luna", "low", "auto", None)[:4] == [
        "-m", "gpt-6-luna", "-c", "model_reasoning_effort=low",
    ]  # fmt: skip


def test_mensaje_de_codex_auto_pide_no_hacer_commit(tmp_path):
    texto = carril.mensaje_inicio(tmp_path, "api", "codex", "auto", "/b/api.md")
    assert "no hagas commit" in texto
    assert "API-READY" in texto
    assert "no hagas commit" not in carril.mensaje_inicio(tmp_path, "ui", "claude", "auto", "/b/ui.md")


def test_preparar_no_pisa_lo_existente(tmp_path, repo):
    run = tmp_path / "run"
    env = preparar_falsos(tmp_path)
    assert correr(CARRIL, "preparar", "--run", str(run), "--repo", str(repo), env=env).returncode == 0
    for nombre in ("STATE.md", "common.md", "gate/queue.md", "carriles.json"):
        assert (run / nombre).exists(), nombre
    (run / "STATE.md").write_text("mío")
    correr(CARRIL, "preparar", "--run", str(run), "--repo", str(repo), env=env)
    assert (run / "STATE.md").read_text() == "mío"


def test_iniciar_rechaza_nombre_invalido(tmp_path, repo):
    env = preparar_falsos(tmp_path)
    r = correr(CARRIL, "iniciar", "--run", str(tmp_path), "--sesion", "s", "--nombre", "Malo!", "--tipo", "claude",
               "--repo", str(repo), env=env)  # fmt: skip
    assert r.returncode == 2
    assert "nombre inválido" in r.stderr


def test_iniciar_codex_responde_confianza_registra_y_manda_brief(tmp_path, repo):
    estado = {"agentes": {}, "arranque_pantallas": ["Trust this folder?\n> 1. Trust and continue", "> Ask Codex"]}
    env = preparar_falsos(tmp_path, estado)
    run = tmp_path / "run"
    correr(CARRIL, "preparar", "--run", str(run), "--repo", str(repo), env=env)
    brief = run / "briefs" / "api.md"
    brief.write_text("# api\n")
    r = correr(CARRIL, "iniciar", "--run", str(run), "--sesion", "s", "--nombre", "api", "--tipo", "codex",
               "--repo", str(repo), "--modelo", "gpt-6-luna", "--brief", str(brief), env=env)  # fmt: skip
    assert r.returncode == 0, r.stderr
    hechas = llamadas(tmp_path)
    crear = next(x for x in hechas if x[:2] == ["worktree", "create"])
    assert crear[crear.index("--base") + 1] == git(repo, "rev-parse", "HEAD"), "sin remoto: base = HEAD local"
    assert crear[crear.index("--branch") + 1] == "flota/api"
    inicio = next(x for x in hechas if x[:2] == ["agent", "start"])
    assert inicio[inicio.index("--") + 1 :] == ["-m", "gpt-6-luna", "-s", "workspace-write", "-a", "never"]
    assert ["agent", "send-keys", "api", "enter"] in hechas, "acepta el diálogo de confianza de Codex"
    prompt = next(x for x in hechas if x[:2] == ["agent", "prompt"])
    assert str(brief) in prompt[3]
    registro = json.loads((run / "carriles.json").read_text())["api"]
    assert registro["pane"] == "w2:p1"
    assert registro["permisos"] == "auto"
    assert "frescura sin verificar" in registro["nota_base"]
    assert "carril api iniciado" in (run / "STATE.md").read_text()


def test_iniciar_no_responde_hooks_de_codex(tmp_path, repo):
    estado = {"agentes": {}, "arranque_pantallas": ["3 hooks need review before they run"]}
    env = preparar_falsos(tmp_path, estado)
    run = tmp_path / "run"
    correr(CARRIL, "preparar", "--run", str(run), "--repo", str(repo), env=env)
    r = correr(CARRIL, "iniciar", "--run", str(run), "--sesion", "s", "--nombre", "api", "--tipo", "codex",
               "--repo", str(repo), env=env)  # fmt: skip
    assert r.returncode == 3
    assert "hooks" in r.stderr
    assert not [x for x in llamadas(tmp_path) if x[:2] == ["agent", "send-keys"]]


def test_iniciar_rechaza_nombre_vivo(tmp_path, repo):
    env = preparar_falsos(tmp_path, {"agentes": {"api": {"status": "working"}}})
    run = tmp_path / "run"
    correr(CARRIL, "preparar", "--run", str(run), "--repo", str(repo), env=env)
    r = correr(CARRIL, "iniciar", "--run", str(run), "--sesion", "s", "--nombre", "api", "--tipo", "claude",
               "--repo", str(repo), env=env)  # fmt: skip
    assert r.returncode == 1
    assert "ya hay un agente vivo" in r.stderr


def test_teclas_solo_las_permitidas(tmp_path):
    env = preparar_falsos(tmp_path, {"agentes": {"api": {"status": "blocked"}}})
    assert correr(CARRIL, "teclas", "--sesion", "s", "--nombre", "api", "rm -rf", env=env).returncode == 2
    assert correr(CARRIL, "teclas", "--sesion", "s", "--nombre", "api", "down", "enter", env=env).returncode == 0
    assert ["agent", "send-keys", "api", "down"] in llamadas(tmp_path)


def test_commit_del_coordinador(tmp_path, repo):
    env = preparar_falsos(tmp_path)
    run = tmp_path / "run"
    wt = tmp_path / "wt-api"
    git(repo, "worktree", "add", "-q", "-b", "flota/api", str(wt))
    run.mkdir()
    (run / "STATE.md").write_text("# c\n")
    (run / "carriles.json").write_text(json.dumps({"api": {"worktree": str(wt)}}))
    r = correr(CARRIL, "commit", "--run", str(run), "--nombre", "api", "-m", "api: nada", env=env)
    assert r.returncode == 0
    assert "no hay cambios" in r.stdout
    (wt / "a.txt").write_text("a2\n")
    (wt / "b.txt").write_text("b\n")
    r = correr(CARRIL, "commit", "--run", str(run), "--nombre", "api", "-m", "api: agrega b", env=env)
    assert r.returncode == 1, "no mete archivos nuevos sin que el coordinador los revise"
    assert "b.txt" in r.stderr
    r = correr(
        CARRIL, "commit", "--run", str(run), "--nombre", "api", "-m", "api: agrega b", "--incluir-nuevos", env=env
    )
    assert r.returncode == 0, r.stderr
    assert "b.txt" in r.stdout
    assert git(wt, "log", "-1", "--format=%s") == "api: agrega b"
    assert json.loads((run / "carriles.json").read_text())["api"]["head"] == r.stdout.strip().splitlines()[-1]


def test_abierto_exige_decision_humana(tmp_path, repo):
    env = preparar_falsos(tmp_path)
    env.pop("FLOTA_PERMITIR_ABIERTO", None)
    run = tmp_path / "run"
    correr(CARRIL, "preparar", "--run", str(run), "--repo", str(repo), env=env)
    args = ("iniciar", "--run", str(run), "--sesion", "s", "--nombre", "api", "--tipo", "claude", "--repo", str(repo),
            "--permisos", "abierto")  # fmt: skip
    r = correr(CARRIL, *args, env=env)
    assert r.returncode == 2
    assert "FLOTA_PERMITIR_ABIERTO" in r.stderr
    assert not llamadas(tmp_path), "no toca herdr"


def test_nunca_acepta_la_confirmacion_de_bypass(tmp_path, repo):
    estado = {
        "agentes": {},
        "arranque_pantallas": ["WARNING: Bypass Permissions mode\n 1. No, exit\n 2. Yes, I accept"],
    }
    env = {**preparar_falsos(tmp_path, estado), "FLOTA_PERMITIR_ABIERTO": "1"}
    run = tmp_path / "run"
    correr(CARRIL, "preparar", "--run", str(run), "--repo", str(repo), env=env)
    r = correr(CARRIL, "iniciar", "--run", str(run), "--sesion", "s", "--nombre", "api", "--tipo", "claude",
               "--repo", str(repo), "--permisos", "abierto", env=env)  # fmt: skip
    assert r.returncode == 3
    assert "lo confirma la persona" in r.stderr
    assert not [x for x in llamadas(tmp_path) if x[:2] == ["agent", "send-keys"]]
