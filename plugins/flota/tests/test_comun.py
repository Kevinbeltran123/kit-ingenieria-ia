"""comun.py: lee bien las entregas, la puerta y la bitácora, y escribe carriles.json sin dejarlo a medias."""

from __future__ import annotations

import comun


def test_lineas_listo_reconoce_entregas_y_revisiones(tmp_path):
    (tmp_path / "handover-api.md").write_text(
        "Hice el endpoint.\n- API-READY flota/api 1a2b3c4\nAPI-READY-no esto no es una entrega\n"
    )
    (tmp_path / "handover-ui.md").write_text("`UI-READY flota/ui sin commit`\n")
    (tmp_path / "review-api.md").write_text("Sin hallazgos.\nREVIEW-READY api PASS\n")
    (tmp_path / "notas.md").write_text("X-READY no cuenta: no es un handover\n")
    lineas = comun.lineas_listo(tmp_path)
    assert {"tipo": "listo", "carril": "api", "resto": "flota/api 1a2b3c4", "archivo": "handover-api.md"} in lineas
    assert {"tipo": "listo", "carril": "ui", "resto": "flota/ui sin commit`", "archivo": "handover-ui.md"} in lineas
    assert {"tipo": "revision", "carril": "api", "resto": "PASS", "archivo": "review-api.md"} in lineas
    assert len(lineas) == 3


def test_puerta_separa_secciones(tmp_path):
    (tmp_path / "gate").mkdir()
    (tmp_path / "gate" / "queue.md").write_text(
        "# Puerta\n\n## En cola\n- ui\n\n## Probando\n\n## Done\n- api PASS (uv run pytest: 41 passed)\n"
    )
    assert comun.puerta(tmp_path) == {
        "En cola": ["ui"],
        "Probando": [],
        "Done": ["api PASS (uv run pytest: 41 passed)"],
    }
    assert comun.puerta(tmp_path / "no-existe") == {}


def test_bitacora_y_anotar(tmp_path):
    (tmp_path / "STATE.md").write_text("# Corrida\n\n## Bitácora\n")
    comun.anotar(tmp_path, "carril api iniciado")
    comun.anotar(tmp_path, "api → gate")
    lineas = comun.bitacora(tmp_path)
    assert len(lineas) == 2
    assert lineas[0].endswith("carril api iniciado")


def test_guardar_y_cargar_carriles(tmp_path):
    run = tmp_path / "run"
    comun.guardar_carriles(run, {"api": {"tipo": "codex"}})
    assert comun.cargar_carriles(run) == {"api": {"tipo": "codex"}}
    assert not list(run.glob(".carriles-*")), "no deja temporales"
    (run / "carriles.json").write_text("{roto")
    assert comun.cargar_carriles(run) == {}


def test_herdr_traduce_errores(falsos, tmp_path):
    import json

    (tmp_path / "estado.json").write_text(json.dumps({"caido": True}))
    try:
        comun.herdr("s", "agent", "list")
    except comun.HerdrError as e:
        assert e.codigo == "server_not_running"
    else:
        raise AssertionError("debía fallar")
    assert comun.agentes("s") == []


def test_bitacora_ignora_otras_listas_del_state(tmp_path):
    (tmp_path / "STATE.md").write_text(
        "# Corrida\n\n## Modelos\n- Planear y revisar: Fable 5.2\n- Haiku no se usa\n\n"
        "## Bitácora\n- 2026-11-17 10:36 coord iniciado\n- nota suelta sin fecha\n"
    )
    assert comun.bitacora(tmp_path) == ["2026-11-17 10:36 coord iniciado"]
