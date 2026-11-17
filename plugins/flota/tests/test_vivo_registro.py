"""Pruebas del detector de registros de sesión de «En vivo» (codigo y comando), con registros falsos en tmp_path."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone

import pytest
import vivo_registro

AHORA = time.time()
CWD = "/abs/repo-flota/wt/palma.diseno"


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def uso(uid: str, nombre: str, entrada: dict, t: float) -> dict:
    return {
        "type": "assistant",
        "timestamp": iso(t),
        "message": {"content": [{"type": "tool_use", "id": uid, "name": nombre, "input": entrada}]},
    }


def resultado(uid: str, texto, t: float, error: bool = False) -> dict:
    bloque = {"type": "tool_result", "tool_use_id": uid, "content": texto, "is_error": error}
    return {"type": "user", "timestamp": iso(t), "message": {"content": [bloque]}}


@pytest.fixture
def sesiones(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "claude"))
    vivo_registro._cache.clear()
    carpeta = vivo_registro.carpeta_sesiones(CWD)
    carpeta.mkdir(parents=True)
    return carpeta


def escribir(carpeta, nombre: str, lineas: list[dict], extra: str = "") -> object:
    ruta = carpeta / f"{nombre}.jsonl"
    ruta.write_text(extra + "".join(json.dumps(linea) + "\n" for linea in lineas))
    return ruta


def ctx(sesion: str | None = None, desde: float = AHORA - 3600) -> dict:
    agente = {"nombre": "palma-diseno", "proyecto": "appalma", "cwd": CWD, "sesion_agente": sesion, "tipo": "claude"}
    return {"ahora": AHORA, "desde": desde, "proyectos": {}, "agentes": [agente], "raices": []}


def test_codifica_el_cwd_como_claude_code(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    carpeta = vivo_registro.carpeta_sesiones("/Users/kevin_beltran/Vilancizar/appalma-flota/wt/palma-diseno")
    assert carpeta == tmp_path / "projects" / "-Users-kevin-beltran-Vilancizar-appalma-flota-wt-palma-diseno"


def test_edit_y_write_agrupan_por_archivo(sesiones):
    archivo = CWD + "/src/a.py"
    escribir(
        sesiones,
        "s1",
        [
            uso("w1", "Write", {"file_path": archivo, "content": "uno\ndos\ntres\n"}, AHORA - 100),
            resultado("w1", "ok", AHORA - 99),
            uso("e1", "Edit", {"file_path": archivo, "old_string": "dos\n", "new_string": "DOS\nmedio\n"}, AHORA - 50),
            resultado("e1", [{"type": "text", "text": "ok"}], AHORA - 49),
        ],
    )
    (p,) = vivo_registro.detectar(ctx("s1"))
    assert p["id"] == f"codigo:{archivo}"
    assert p["tipo"] == "codigo"
    assert p["agente"] == "palma-diseno"
    assert p["proyecto"] == "appalma"
    assert p["t"] == pytest.approx(AHORA - 50, abs=0.01)
    assert p["titulo"] == "src/a.py +5 −1"
    d = p["datos"]
    assert (d["mas"], d["menos"], d["herramienta"], d["archivo"]) == (5, 1, "Edit", archivo)
    assert "-dos" in d["fragmento"].splitlines()
    assert "+DOS" in d["fragmento"].splitlines()


def test_multiedit_y_notebook(sesiones):
    escribir(
        sesiones,
        "s1",
        [
            uso(
                "m1",
                "MultiEdit",
                {
                    "file_path": "/otro/b.py",
                    "edits": [{"old_string": "a", "new_string": "b"}, {"old_string": "c", "new_string": "d"}],
                },
                AHORA - 10,
            ),
            uso("n1", "NotebookEdit", {"notebook_path": "/otro/n.ipynb", "new_source": "x = 1\ny = 2"}, AHORA - 5),
        ],
    )
    productos = {p["datos"]["archivo"]: p for p in vivo_registro.detectar(ctx("s1"))}
    assert (productos["/otro/b.py"]["datos"]["mas"], productos["/otro/b.py"]["datos"]["menos"]) == (2, 2)
    assert productos["/otro/b.py"]["titulo"] == "otro/b.py +2 −2"
    assert productos["/otro/n.ipynb"]["datos"]["mas"] == 2


def test_edicion_fallida_y_fuera_de_ventana_no_cuentan(sesiones):
    escribir(
        sesiones,
        "s1",
        [
            uso("v1", "Write", {"file_path": "/x/viejo.py", "content": "a"}, AHORA - 7200),
            uso("e1", "Edit", {"file_path": "/x/f.py", "old_string": "a", "new_string": "b"}, AHORA - 10),
            resultado("e1", "String to replace not found", AHORA - 9, error=True),
            uso("r1", "Read", {"file_path": "/x/f.py"}, AHORA - 8),
        ],
    )
    assert vivo_registro.detectar(ctx("s1")) == []


def test_fragmento_recortado_a_60_lineas(sesiones):
    contenido = "\n".join(f"l{i}" for i in range(200))
    escribir(sesiones, "s1", [uso("w1", "Write", {"file_path": "/x/g.py", "content": contenido}, AHORA - 1)])
    (p,) = vivo_registro.detectar(ctx("s1"))
    lineas = p["datos"]["fragmento"].splitlines()
    assert len(lineas) == 60
    assert lineas[-1] == "… 141 líneas más"
    assert p["datos"]["mas"] == 200


def test_comandos_con_resultado_pruebas_y_ultimos_diez(sesiones):
    lineas = []
    for i in range(12):
        lineas.append(uso(f"b{i}", "Bash", {"command": f"echo {i}"}, AHORA - 100 + i))
        lineas.append(resultado(f"b{i}", f"{i}", AHORA - 99 + i))
    salida = "\n".join(f"linea {i}" for i in range(30)) + "\n===== 12 passed, 1 failed in 0.3s ====="
    lineas.append(uso("bp", "Bash", {"command": "python3 -m pytest -q\n# segunda"}, AHORA - 20))
    lineas.append(resultado("bp", "Exit code 1\n" + salida, AHORA - 17, error=True))
    lineas.append(uso("bn", "Bash", {"command": "sleep 100"}, AHORA - 2))
    escribir(sesiones, "s1", lineas)
    comandos = [p for p in vivo_registro.detectar(ctx("s1")) if p["tipo"] == "comando"]
    assert len(comandos) == 10
    pytest_ = next(p for p in comandos if p["id"] == "comando:bp")
    assert pytest_["titulo"] == "python3 -m pytest -q · 12 passed, 1 failed"
    assert pytest_["datos"]["ok"] is False
    assert pytest_["datos"]["duracion"] == pytest.approx(3, abs=0.01)
    assert len(pytest_["datos"]["resultado"]) == 20
    assert pytest_["datos"]["resultado"][-1].startswith("===== 12 passed")
    pendiente = next(p for p in comandos if p["id"] == "comando:bn")
    assert (pendiente["datos"]["ok"], pendiente["datos"]["duracion"]) == (None, None)
    bien = next(p for p in comandos if p["id"] == "comando:b11")
    assert (bien["datos"]["ok"], bien["datos"]["resultado"]) == (True, ["11"])
    json.dumps(comandos)


def test_sin_sesion_usa_el_registro_mas_reciente(sesiones):
    viejo = escribir(sesiones, "vieja", [uso("w1", "Write", {"file_path": "/x/viejo.py", "content": "a"}, AHORA - 5)])
    os.utime(viejo, (AHORA - 600, AHORA - 600))
    escribir(sesiones, "nueva", [uso("w2", "Write", {"file_path": "/x/nuevo.py", "content": "a"}, AHORA - 5)])
    assert [p["datos"]["archivo"] for p in vivo_registro.detectar(ctx())] == ["/x/nuevo.py"]


def test_lee_solo_el_final_y_salta_lineas_raras(sesiones, monkeypatch):
    monkeypatch.setattr(vivo_registro, "TAIL", 400)
    relleno = json.dumps({"type": "user", "message": {"content": "tool_" + "x" * 2000}}) + "\n"
    ruta = escribir(
        sesiones,
        "s1",
        [uso("w1", "Write", {"file_path": "/x/fin.py", "content": "a"}, AHORA - 5)],
        extra=relleno
        + "{roto tool_\n"
        + json.dumps(uso("w0", "Write", {"file_path": "/x/ini.py", "content": "a"}, AHORA - 6))
        + "\n"
        + relleno,
    )
    assert ruta.stat().st_size > 400
    assert [p["datos"]["archivo"] for p in vivo_registro.detectar(ctx("s1"))] == ["/x/fin.py"]


def test_cachea_por_tamano_y_mtime(sesiones, monkeypatch):
    ruta = escribir(sesiones, "s1", [uso("w1", "Write", {"file_path": "/x/a.py", "content": "a"}, AHORA - 5)])
    vivo_registro.detectar(ctx("s1"))
    abiertos = []
    original = type(ruta).open

    def contar(self, *args, **kwargs):
        abiertos.append(self)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(type(ruta), "open", contar)
    vivo_registro.detectar(ctx("s1"))
    assert abiertos == []
    with ruta.open("a") as f:
        f.write(json.dumps(uso("w2", "Write", {"file_path": "/x/b.py", "content": "b"}, AHORA - 1)) + "\n")
    assert len(vivo_registro.detectar(ctx("s1"))) == 2
    assert len(abiertos) == 2  # el append de la prueba y la relectura


def test_agente_sin_registro_o_sin_cwd(sesiones):
    sin_cwd = {"nombre": "x", "proyecto": None, "cwd": None, "sesion_agente": None, "tipo": None}
    otro = {"nombre": "y", "proyecto": None, "cwd": "/no/existe", "sesion_agente": None, "tipo": None}
    contexto = {**ctx("falta"), "agentes": [sin_cwd, otro, ctx("falta")["agentes"][0]]}
    assert vivo_registro.detectar(contexto) == []
