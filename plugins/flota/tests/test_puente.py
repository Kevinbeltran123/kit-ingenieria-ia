"""puente.py (plugin de herdr): registra cada cambio de estado y lo refleja en cmux sin avisos de más."""

from __future__ import annotations

import json

import pytest
from ayudas_flota import PUENTE, correr, preparar_falsos


def evento(pane, estado=None, agente="claude", tipo="pane_agent_status_changed"):
    datos = {"type": tipo, "pane_id": pane, "workspace_id": "w1"}
    if estado:
        datos.update(agent_status=estado, agent=agente)
    return json.dumps({"event": tipo, "data": datos})


def disparar(tmp_path, env, ev, **extra):
    env = {**env, "HERDR_PLUGIN_EVENT_JSON": ev, "HERDR_SESSION": "s", "HERDR_BIN_PATH": env["FLOTA_HERDR"], **extra}
    return correr(PUENTE, env=env)


def cmux_log(tmp_path):
    ruta = tmp_path / "cmux.log"
    return ruta.read_text().splitlines() if ruta.exists() else []


def test_registra_eventos_con_nombre_y_estado_previo(tmp_path):
    env = preparar_falsos(tmp_path, {"agentes": {"api": {"status": "working", "pane": "w2:p1"}}})
    assert disparar(tmp_path, env, evento("w2:p1", "working")).returncode == 0
    disparar(tmp_path, env, evento("w2:p1", "idle"))
    eventos = [json.loads(x) for x in (tmp_path / "eventos" / "s" / "eventos.jsonl").read_text().splitlines()]
    assert [(e["nombre"], e["de"], e["a"]) for e in eventos] == [("api", None, "working"), ("api", "working", "idle")]


def test_refleja_en_cmux_estado_log_y_aviso_al_terminar(tmp_path):
    env = preparar_falsos(tmp_path, {"agentes": {"api": {"status": "working", "pane": "w2:p1"}}})
    disparar(tmp_path, env, evento("w2:p1", "working"), CMUX_WORKSPACE_ID="workspace:3")
    disparar(tmp_path, env, evento("w2:p1", "idle"), CMUX_WORKSPACE_ID="workspace:3")
    log = cmux_log(tmp_path)
    assert any(
        x.startswith("set-status flota-api api: trabajando") and x.endswith("--workspace workspace:3") for x in log
    )
    assert any(x.startswith("log --level info --source flota api: trabajando → quieto") for x in log)
    avisos = [x for x in log if x.startswith("notify")]
    assert len(avisos) == 1
    assert "terminó su turno" in avisos[0]


def test_aviso_cuando_te_espera_y_limpia_al_cerrar(tmp_path):
    env = preparar_falsos(tmp_path, {"agentes": {"ui": {"status": "blocked", "pane": "w4:p1"}}})
    disparar(tmp_path, env, evento("w4:p1", "blocked", agente="codex"))
    disparar(tmp_path, env, evento("w4:p1", tipo="pane_closed"))
    log = cmux_log(tmp_path)
    assert any(x.startswith("notify --title Flota · ui --body te espera") for x in log)
    assert any(x.startswith("clear-status flota-ui") for x in log)


@pytest.mark.parametrize(
    ("previo", "nuevo", "agente", "modo", "aviso"),
    [
        ("working", "blocked", "claude", "todos", True),
        ("blocked", "blocked", "claude", "todos", False),
        ("working", "done", "codex", "todos", True),
        ("idle", "working", "codex", "todos", False),
        ("working", "done", "claude", "sin-claude", False),
        ("working", "done", "codex", "sin-claude", True),
        ("working", "blocked", "codex", "ninguno", False),
    ],
)
def test_decidir_aviso(previo, nuevo, agente, modo, aviso):
    import importlib.util

    spec = importlib.util.spec_from_file_location("puente", PUENTE)
    puente = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(puente)
    assert (puente.decidir_aviso(previo, nuevo, agente, modo) is not None) is aviso


def test_sin_cmux_no_falla(tmp_path):
    env = preparar_falsos(tmp_path, {"agentes": {}})
    (tmp_path / "bin" / "cmux").unlink()
    r = disparar(tmp_path, env, evento("w9:p1", "working"))
    assert r.returncode == 0
    assert (tmp_path / "eventos" / "s" / "eventos.jsonl").exists()


def test_errores_de_cmux_quedan_registrados(tmp_path):
    env = preparar_falsos(tmp_path, {"agentes": {}})
    (tmp_path / "bin" / "cmux").write_text("#!/bin/sh\necho 'Acceso denegado' >&2\nexit 1\n")
    assert disparar(tmp_path, env, evento("w9:p1", "working")).returncode == 0
    errores = (tmp_path / "eventos" / "s" / "cmux-errores.log").read_text()
    assert "cmux set-status: Acceso denegado" in errores


def test_si_el_espacio_de_cmux_ya_no_existe_reintenta_sin_el(tmp_path):
    env = preparar_falsos(tmp_path, {"agentes": {}})
    falso = '#!/bin/sh\nprintf "%s\\n" "$*" >> "$FALSO_CMUX"\ncase "$*" in *--workspace*) exit 1;; esac\n'
    (tmp_path / "bin" / "cmux").write_text(falso)
    disparar(tmp_path, env, evento("w9:p1", "working"), CMUX_WORKSPACE_ID="workspace:viejo")
    log = cmux_log(tmp_path)
    assert any("--workspace workspace:viejo" in x for x in log)
    assert any(x.startswith("set-status") and "--workspace" not in x for x in log)
    assert not (tmp_path / "eventos" / "s" / "cmux-errores.log").exists()
