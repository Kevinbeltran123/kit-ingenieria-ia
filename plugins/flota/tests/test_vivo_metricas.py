from __future__ import annotations

import json
import os

import vivo_metricas

AHORA = 1_800_000_000.0


def sin_pueue(args):
    return None


def escribir(ruta, texto, t=AHORA - 10):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto)
    os.utime(ruta, (t, t))
    return ruta


def ctx_de(raices, proyectos=None):
    return {"ahora": AHORA, "desde": AHORA - 3600, "proyectos": proyectos or {}, "agentes": [], "raices": raices}


def raiz(ruta, agente="ag"):
    return {"ruta": str(ruta), "proyecto": "p", "agente": agente}


def test_csv_con_log_progreso_y_errores(tmp_path):
    escribir(
        tmp_path / "runs/e004/metrics.csv", "epoch,train_loss,val_loss,val_f1,nota\n0,1.0,0.9,0.5,a\n1,0.8,0.7,0.6,b\n"
    )
    log = "\n".join([f"linea {i}" for i in range(20)] + ["Epoch 2/40", "RuntimeError: algo", "loss nan", "INFO ok"])
    escribir(tmp_path / "runs/e004/log.txt", log + "\n", t=AHORA - 5)
    (r,) = vivo_metricas.detectar(ctx_de([raiz(tmp_path)]), sin_pueue)
    d = r["datos"]
    assert (r["id"], r["tipo"], r["proyecto"], r["agente"]) == (
        f"metricas:{tmp_path}/runs/e004/metrics.csv",
        "metricas",
        "p",
        "ag",
    )
    assert r["t"] == AHORA - 5
    assert d["archivo"] == str(tmp_path / "runs/e004/metrics.csv")
    assert d["x"] == "epoch"
    assert d["series"] == {"epoch": [0, 1], "train_loss": [1.0, 0.8], "val_loss": [0.9, 0.7], "val_f1": [0.5, 0.6]}
    assert d["ultima"]["val_loss"] == 0.7
    assert d["progreso"] == {"actual": 2, "total": 40}
    assert d["errores"] == 2  # «INFO» no cuenta como inf
    assert len(d["log"]) == 15 and d["log"][-1] == "INFO ok"
    assert r["titulo"] == "runs/e004 · 2/40 · val_loss 0.7 · val_f1 0.6 · 2 con error"
    json.dumps(r, allow_nan=False)


def test_lightning_celdas_vacias_y_filas_juntas(tmp_path):
    texto = "epoch,step,train_loss,val_loss\n0,49,1.5,\n0,99,1.2,\n0,99,,1.1\n1,149,0.9,\n1,199,nan,\n1,199,,0.8\n"
    escribir(tmp_path / "runs/e1/lightning_logs/version_0/metrics.csv", texto)
    escribir(tmp_path / "runs/e1/log.txt", "época 2 de 3\n")
    (r,) = vivo_metricas.detectar(ctx_de([raiz(tmp_path)]), sin_pueue)
    d = r["datos"]
    assert d["x"] == "step"
    assert d["series"]["step"] == [49, 99, 149, 199]
    assert d["series"]["val_loss"] == [None, 1.1, None, 0.8]
    assert d["series"]["train_loss"] == [1.5, 1.2, 0.9, None]  # nan no es un número para la gráfica
    assert d["ultima"] == {"epoch": 1, "step": 199, "train_loss": 0.9, "val_loss": 0.8}
    assert d["progreso"] == {"actual": 2, "total": 3}  # el log de la corrida, dos carpetas arriba
    assert r["titulo"].startswith("runs/e1 · 2/3 · val_loss 0.8")


def test_submuestra_conserva_la_ultima_y_las_series_ralas(tmp_path):
    filas = ["step,train_loss,val_loss"]
    for i in range(5000):
        filas.append(f"{i},{1 / (i + 1)},")
        if i % 100 == 99:
            filas.append(f"{i},,{i / 1000}")
    escribir(tmp_path / "history.csv", "\n".join(filas) + "\n")
    (r,) = vivo_metricas.detectar(ctx_de([raiz(tmp_path)]), sin_pueue)
    s = r["datos"]["series"]
    assert len(s["step"]) <= 500
    assert s["step"][-1] == 4999
    assert len([v for v in s["val_loss"] if v is not None]) == 50  # ninguna validación se pierde
    assert r["datos"]["ultima"]["val_loss"] == 4.999
    assert len({len(v) for v in s.values()}) == 1  # siguen alineadas


def test_sin_eje_usa_la_fila_y_patrones_de_nombre(tmp_path):
    escribir(tmp_path / "a/train_metrics.csv", "loss,acc\n0.5,0.1\n0.4,0.2\n")
    escribir(tmp_path / "b/progress.csv", "x\n1\n")
    escribir(tmp_path / "c/log_2026.csv", "x\n1\n")
    escribir(tmp_path / "d/datos.csv", "loss\n1\n")
    escribir(tmp_path / "e/metrics.csv", "loss\n1\n", t=AHORA - 99999)  # fuera de la ventana
    escribir(tmp_path / "a/salida.log", "step 300/1000\n14/40 [00:01<00:02]\n")
    r = vivo_metricas.detectar(ctx_de([raiz(tmp_path)]), sin_pueue)
    assert sorted(p["datos"]["archivo"].split("/")[-2] for p in r) == ["a", "b", "c"]
    a = next(p for p in r if p["datos"]["archivo"].endswith("train_metrics.csv"))
    assert a["datos"]["x"] == "fila" and a["datos"]["series"] == {"loss": [0.5, 0.4], "acc": [0.1, 0.2]}
    assert a["datos"]["progreso"] == {"actual": 14, "total": 40}  # la última línea con progreso
    b = next(p for p in r if p["datos"]["archivo"].endswith("progress.csv"))
    assert (b["datos"]["log"], b["datos"]["errores"], b["datos"]["progreso"]) == ([], 0, None)


def test_salta_caches_wt_de_la_corrida_y_raices_anidadas(tmp_path):
    run = tmp_path / "run"
    escribir(run / "wt/ag/metrics.csv", "loss\n1\n")
    escribir(run / "node_modules/metrics.csv", "loss\n1\n")
    escribir(run / ".venv/metrics.csv", "loss\n1\n")
    escribir(run / "runs/e1/metrics.csv", "loss\n1\n")
    otra = tmp_path / "repo"
    escribir(otra / "sub/metrics.csv", "loss\n1\n")
    ctx = ctx_de(
        [raiz(otra / "sub", "ag2"), raiz(otra, None), raiz(run, None)], {"p": {"repo": str(otra), "run": str(run)}}
    )
    r = vivo_metricas.detectar(ctx, sin_pueue)
    assert sorted((p["datos"]["archivo"], p["agente"]) for p in r) == [
        (str(otra / "sub/metrics.csv"), "ag2"),
        (str(run / "runs/e1/metrics.csv"), None),
    ]


def test_archivos_raros_no_rompen(tmp_path):
    escribir(tmp_path / "a/metrics.csv", "")
    escribir(tmp_path / "b/metrics.csv", "solo,texto\nhola,mundo\n")
    (tmp_path / "c").mkdir()
    (tmp_path / "c/metrics.csv").write_bytes(b"\xff\xfe\x00loss\n\x001\n")
    os.utime(tmp_path / "c/metrics.csv", (AHORA, AHORA))
    r = vivo_metricas.detectar(ctx_de([raiz(tmp_path), raiz(tmp_path / "no-existe")]), sin_pueue)
    assert {p["datos"]["archivo"].split("/")[-2] for p in r} <= {"a", "b", "c"}
    for p in r:
        json.dumps(p, allow_nan=False)


def test_pueue_tareas_en_curso(tmp_path):
    estado = {
        "tasks": {
            "3": {"id": 3, "label": "e004", "command": "just entrenar e004", "path": str(tmp_path / "repo"), "group": "gpu",
                  "status": {"Running": {"enqueued_at": "2027-01-15T08:00:00Z", "start": "2027-01-15T08:00:00.123456789+00:00"}}},
            "4": {"id": 4, "command": "sleep 9", "path": "/otro", "status": {"Done": {"result": "Success"}}},
            "5": {"id": 5, "command": "python largo.py", "path": "/otro", "status": "Running", "start": None},
        }
    }  # fmt: skip
    llamadas = []

    def ejecutar(args):
        llamadas.append(args)
        if args[:2] == ["status", "--json"]:
            return json.dumps(estado)
        if args[-1] == "3":
            return json.dumps(
                {"3": {"task": {}, "output": "cargando\nEpoch 3/10\nTraceback (most recent call last)\n"}}
            )
        return "no es json"

    ctx = ctx_de([raiz(tmp_path / "repo")])
    r = vivo_metricas.tareas_pueue(ctx, ejecutar)
    assert [p["id"] for p in r] == ["metricas:pueue:3", "metricas:pueue:5"]
    p = r[0]
    assert (p["proyecto"], p["agente"]) == ("p", "ag")
    assert p["datos"]["progreso"] == {"actual": 3, "total": 10} and p["datos"]["errores"] == 1
    assert p["datos"]["pueue"]["comando"] == "just entrenar e004" and p["datos"]["pueue"]["label"] == "e004"
    assert p["datos"]["pueue"]["inicio"] == 1_800_000_000.123456
    assert p["titulo"].startswith("pueue 3 · e004 · 3/10")
    assert r[1]["datos"]["log"] == [] and r[1]["proyecto"] is None
    assert ["log", "--json", "--lines", "15", "3"] in llamadas
    json.dumps(r, allow_nan=False)


def test_pueue_ausente_o_roto():
    ctx = ctx_de([])
    assert vivo_metricas.tareas_pueue(ctx, lambda a: None) == []
    assert vivo_metricas.tareas_pueue(ctx, lambda a: "basura") == []
    assert vivo_metricas.tareas_pueue(ctx, lambda a: json.dumps({"tasks": []})) == []


def test_pueue_sin_binario_no_llama(monkeypatch):
    monkeypatch.setattr(vivo_metricas.shutil, "which", lambda nombre: None)
    assert vivo_metricas.tareas_pueue(ctx_de([])) == []
