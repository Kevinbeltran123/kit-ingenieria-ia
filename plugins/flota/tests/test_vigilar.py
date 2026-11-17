"""vigilar.py: BASELINE la primera vez, CHANGED con entregas nuevas, STOPPED si un carril para sin entregar."""

from __future__ import annotations

import json
import subprocess
import sys
import time

from ayudas_flota import SCRIPTS, correr, preparar_falsos

VIGILAR = SCRIPTS / "vigilar.py"


def preparar_run(tmp_path):
    run = tmp_path / "run"
    (run / "gate").mkdir(parents=True)
    (run / "carriles.json").write_text(json.dumps({"api": {}}))
    return run


def test_baseline_y_luego_changed(tmp_path):
    env = preparar_falsos(tmp_path)
    run = preparar_run(tmp_path)
    (run / "handover-api.md").write_text("API-READY flota/api aaa\n")
    r = correr(VIGILAR, "--run", str(run), "--timeout", "1", "--intervalo", "0.2", env=env)
    assert r.stdout.startswith("BASELINE:")
    r = correr(VIGILAR, "--run", str(run), "--timeout", "0.5", "--intervalo", "0.2", env=env)
    assert r.stdout.startswith("TIMEOUT")
    (run / "gate" / "queue.md").write_text("## Done\n- api PASS\n")
    r = correr(VIGILAR, "--run", str(run), "--timeout", "2", "--intervalo", "0.2", env=env)
    assert r.stdout.startswith("CHANGED:")
    assert "done:api PASS" in r.stdout
    assert "API-READY" not in r.stdout, "solo lo nuevo"


def test_stopped_cuando_un_carril_para_sin_entregar(tmp_path):
    env = preparar_falsos(tmp_path, {"agentes": {"api": {"status": "working"}}})
    run = preparar_run(tmp_path)
    correr(VIGILAR, "--run", str(run), "--timeout", "1", env=env)  # baseline
    proc = subprocess.Popen(
        [sys.executable, "-I", str(VIGILAR), "--run", str(run), "--sesion", "s", "--timeout", "10", "--intervalo", "0.3"],
        stdout=subprocess.PIPE, text=True, env=env,
    )  # fmt: skip
    time.sleep(1.2)
    (tmp_path / "estado.json").write_text(json.dumps({"agentes": {"api": {"status": "idle"}}}))
    salida, _ = proc.communicate(timeout=10)
    assert salida.startswith("STOPPED: api quedó idle")
