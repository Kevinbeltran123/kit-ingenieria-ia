"""Pruebas de los hooks con herramientas falsas en .venv/bin del proyecto de prueba."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parent.parent / "hooks"


@pytest.fixture
def proyecto(tmp_path):
    raiz = tmp_path / "repo"
    (raiz / ".venv" / "bin").mkdir(parents=True)
    (raiz / "app.py").write_text("x = 1\n")
    temporal = tmp_path / "tmp"
    temporal.mkdir()
    return raiz, temporal


def herramienta_falsa(raiz: Path, nombre: str, codigo: int, salida: str = "") -> Path:
    """Crea .venv/bin/<nombre> que guarda sus argumentos, imprime `salida` y sale con `codigo`."""
    registro = raiz / f"{nombre}.args"
    script = raiz / ".venv" / "bin" / nombre
    script.write_text(f'#!/bin/sh\necho "$@" >> "{registro}"\necho "{salida}"\nexit {codigo}\n')
    script.chmod(0o755)
    return registro


def correr(hook: str, datos: dict, raiz: Path, temporal: Path, path_extra: str = "", path_minimo: bool = False):
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(raiz), "TMPDIR": str(temporal)}
    if path_minimo:  # sin las herramientas de la máquina (un pytest global, por ejemplo)
        env["PATH"] = "/usr/bin:/bin"
    if path_extra:
        env["PATH"] = path_extra + os.pathsep + env["PATH"]
    return subprocess.run(
        [sys.executable, "-I", str(HOOKS / hook)],
        input=json.dumps(datos),
        capture_output=True,
        text=True,
        env=env,
    )


def marca(temporal: Path, sesion: str) -> Path:
    return temporal / "claude-calidad-python" / sesion


def editar(raiz, temporal, sesion="s1"):
    datos = {"session_id": sesion, "tool_input": {"file_path": str(raiz / "app.py")}}
    return correr("ruff_al_editar.py", datos, raiz, temporal)


# --- ruff_al_editar.py ---


def test_ignora_archivos_que_no_son_python(proyecto):
    raiz, temporal = proyecto
    (raiz / "notas.md").write_text("hola")
    r = correr(
        "ruff_al_editar.py", {"session_id": "s1", "tool_input": {"file_path": str(raiz / "notas.md")}}, raiz, temporal
    )
    assert r.returncode == 0
    assert not marca(temporal, "s1").exists()


def test_errores_de_ruff_se_devuelven_a_claude(proyecto):
    raiz, temporal = proyecto
    herramienta_falsa(raiz, "ruff", 1, "app.py:1:1: F401 unused import")
    r = editar(raiz, temporal)
    assert r.returncode == 2
    assert "F401" in r.stderr
    assert str(raiz / "app.py") in marca(temporal, "s1").read_text()


def test_ruff_limpio_pasa(proyecto):
    raiz, temporal = proyecto
    registro = herramienta_falsa(raiz, "ruff", 0)
    r = editar(raiz, temporal)
    assert r.returncode == 0
    llamadas = registro.read_text()
    assert "check --fix" in llamadas and "format" in llamadas


# --- revisar_al_terminar.py ---


def test_sin_ediciones_de_python_no_revisa(proyecto):
    raiz, temporal = proyecto
    registro = herramienta_falsa(raiz, "pytest", 1)
    (raiz / "tests").mkdir()
    r = correr("revisar_al_terminar.py", {"session_id": "s1"}, raiz, temporal)
    assert r.returncode == 0
    assert not registro.exists()


def test_pruebas_que_fallan_bloquean_el_final(proyecto):
    raiz, temporal = proyecto
    herramienta_falsa(raiz, "ruff", 0)
    herramienta_falsa(raiz, "pytest", 1, "FAILED tests/test_app.py::test_suma")
    (raiz / "tests").mkdir()
    editar(raiz, temporal)
    r = correr("revisar_al_terminar.py", {"session_id": "s1"}, raiz, temporal)
    assert r.returncode == 2
    assert "pytest falló" in r.stderr and "test_suma" in r.stderr
    assert marca(temporal, "s1").exists()


def test_tras_corregir_vuelve_a_verificar(proyecto):
    raiz, temporal = proyecto
    herramienta_falsa(raiz, "ruff", 0)
    registro = herramienta_falsa(raiz, "pytest", 1, "FAILED tests/test_app.py::test_suma")
    (raiz / "tests").mkdir()
    editar(raiz, temporal)
    assert correr("revisar_al_terminar.py", {"session_id": "s1"}, raiz, temporal).returncode == 2

    herramienta_falsa(raiz, "pytest", 0)  # Claude corrigió el bug
    r = correr("revisar_al_terminar.py", {"session_id": "s1", "stop_hook_active": True}, raiz, temporal)
    assert r.returncode == 0
    assert len(registro.read_text().splitlines()) == 2  # pytest corrió también al reintentar
    assert not marca(temporal, "s1").exists()


def test_si_sigue_fallando_bloquea_dos_veces_y_despues_avisa(proyecto):
    raiz, temporal = proyecto
    herramienta_falsa(raiz, "ruff", 0)
    herramienta_falsa(raiz, "pytest", 1, "FAILED tests/test_app.py::test_suma")
    (raiz / "tests").mkdir()
    editar(raiz, temporal)
    assert correr("revisar_al_terminar.py", {"session_id": "s1"}, raiz, temporal).returncode == 2
    continuar = {"session_id": "s1", "stop_hook_active": True}
    assert correr("revisar_al_terminar.py", continuar, raiz, temporal).returncode == 2

    r = correr("revisar_al_terminar.py", continuar, raiz, temporal)
    assert r.returncode == 0
    assert "pytest" in json.loads(r.stdout)["systemMessage"]
    assert not marca(temporal, "s1").exists()


def test_el_bloqueo_de_otro_plugin_no_salta_la_revision(proyecto):
    """stop_hook_active también es True cuando bloqueó otro plugin: igual hay que revisar."""
    raiz, temporal = proyecto
    herramienta_falsa(raiz, "ruff", 0)
    herramienta_falsa(raiz, "pytest", 1)
    (raiz / "tests").mkdir()
    editar(raiz, temporal)
    r = correr("revisar_al_terminar.py", {"session_id": "s1", "stop_hook_active": True}, raiz, temporal)
    assert r.returncode == 2


def test_un_mensaje_nuevo_de_la_persona_reinicia_las_oportunidades(proyecto):
    raiz, temporal = proyecto
    herramienta_falsa(raiz, "ruff", 0)
    herramienta_falsa(raiz, "pytest", 1)
    (raiz / "tests").mkdir()
    editar(raiz, temporal)
    assert correr("revisar_al_terminar.py", {"session_id": "s1"}, raiz, temporal).returncode == 2
    continuar = {"session_id": "s1", "stop_hook_active": True}
    assert correr("revisar_al_terminar.py", continuar, raiz, temporal).returncode == 2
    # La persona escribe de nuevo (stop_hook_active=False): empieza otra ronda.
    assert correr("revisar_al_terminar.py", {"session_id": "s1"}, raiz, temporal).returncode == 2


def test_sin_pruebas_recolectadas_no_es_fallo(proyecto):
    raiz, temporal = proyecto
    herramienta_falsa(raiz, "ruff", 0)
    herramienta_falsa(raiz, "pytest", 5)
    (raiz / "tests").mkdir()
    editar(raiz, temporal)
    r = correr("revisar_al_terminar.py", {"session_id": "s1"}, raiz, temporal)
    assert r.returncode == 0
    assert not marca(temporal, "s1").exists()


def test_usa_el_verificador_de_tipos_configurado_sobre_los_archivos_editados(proyecto):
    raiz, temporal = proyecto
    (raiz / "pyproject.toml").write_text("[tool.mypy]\nstrict = true\n")
    herramienta_falsa(raiz, "ruff", 0)
    ty = herramienta_falsa(raiz, "ty", 0)
    mypy = herramienta_falsa(raiz, "mypy", 1, "app.py:1: error: tipo incorrecto")
    editar(raiz, temporal)
    r = correr("revisar_al_terminar.py", {"session_id": "s1"}, raiz, temporal)
    assert r.returncode == 2
    assert "mypy falló" in r.stderr
    assert str(raiz / "app.py") in mypy.read_text()
    assert not ty.exists()


def test_import_linter_solo_si_esta_configurado(proyecto):
    raiz, temporal = proyecto
    herramienta_falsa(raiz, "ruff", 0)
    lint = herramienta_falsa(raiz, "lint-imports", 1, "Contrato roto")
    editar(raiz, temporal)
    assert correr("revisar_al_terminar.py", {"session_id": "s1"}, raiz, temporal).returncode == 0
    assert not lint.exists()

    (raiz / "pyproject.toml").write_text("[tool.importlinter]\nroot_package = 'app'\n")
    editar(raiz, temporal, sesion="s2")
    r = correr("revisar_al_terminar.py", {"session_id": "s2"}, raiz, temporal)
    assert r.returncode == 2 and "import-linter falló" in r.stderr


def test_herramienta_configurada_sin_instalar_no_pasa_en_silencio(proyecto):
    """Con [tool.ty] y tests/ pero sin ty ni pytest en el .venv, salía con 0 sin revisar nada."""
    raiz, temporal = proyecto
    (raiz / "pyproject.toml").write_text("[tool.ty]\n")
    (raiz / "tests").mkdir()
    herramienta_falsa(raiz, "ruff", 0)
    editar(raiz, temporal)
    r = correr("revisar_al_terminar.py", {"session_id": "s1"}, raiz, temporal, path_minimo=True)
    assert r.returncode == 2
    assert "ty: está configurado pero no instalado" in r.stderr
    assert "pytest: está configurado pero no instalado" in r.stderr
    assert "uv sync" in r.stderr


def test_sin_herramientas_tras_dos_intentos_avisa_que_no_se_reviso(proyecto):
    raiz, temporal = proyecto
    (raiz / "tests").mkdir()
    herramienta_falsa(raiz, "ruff", 0)
    editar(raiz, temporal)
    continuar = {"session_id": "s1", "stop_hook_active": True}
    assert correr("revisar_al_terminar.py", {"session_id": "s1"}, raiz, temporal, path_minimo=True).returncode == 2
    assert correr("revisar_al_terminar.py", continuar, raiz, temporal, path_minimo=True).returncode == 2
    r = correr("revisar_al_terminar.py", continuar, raiz, temporal, path_minimo=True)
    assert r.returncode == 0
    aviso = json.loads(r.stdout)["systemMessage"]
    assert "pytest" in aviso and "sin poder revisarse" in aviso


def test_tool_typos_no_cuenta_como_ty(proyecto):
    """`[tool.typos]` empieza igual que `[tool.ty`: el hook bloqueaba pidiendo instalar ty en un repo sin ty."""
    raiz, temporal = proyecto
    (raiz / "pyproject.toml").write_text("[tool.typos]\n")
    herramienta_falsa(raiz, "ruff", 0)
    editar(raiz, temporal)
    r = correr("revisar_al_terminar.py", {"session_id": "s1"}, raiz, temporal, path_minimo=True)
    assert r.returncode == 0, r.stderr


def test_una_subtabla_de_ty_cuenta_como_configurado(proyecto):
    raiz, temporal = proyecto
    (raiz / "pyproject.toml").write_text("[tool.ty.environment]\npython-version = '3.12'\n")
    herramienta_falsa(raiz, "ruff", 0)
    editar(raiz, temporal)
    r = correr("revisar_al_terminar.py", {"session_id": "s1"}, raiz, temporal, path_minimo=True)
    assert r.returncode == 2
    assert "ty: está configurado pero no instalado" in r.stderr


# --- no_silenciar.py ---


def silenciar(herramienta: str, entrada: dict, raiz: Path, temporal: Path):
    return correr("no_silenciar.py", {"tool_name": herramienta, "tool_input": entrada}, raiz, temporal)


def editar_codigo(raiz: Path, temporal: Path, viejo: str, nuevo: str):
    entrada = {"file_path": str(raiz / "app.py"), "old_string": viejo, "new_string": nuevo}
    return silenciar("Edit", entrada, raiz, temporal)


def bloqueado(r) -> bool:
    return r.returncode == 2 and "solo la persona" in r.stderr


def test_esta_conectado_antes_de_editar_y_de_correr_comandos():
    entradas = json.loads((HOOKS / "hooks.json").read_text())["hooks"]["PreToolUse"]
    entrada = next(e for e in entradas if any("no_silenciar.py" in h["command"] for h in e["hooks"]))
    assert set(entrada["matcher"].split("|")) >= {"Edit", "Write", "MultiEdit", "Bash"}


def test_claude_no_puede_agregar_un_noqa(proyecto):
    raiz, temporal = proyecto
    r = editar_codigo(raiz, temporal, "x = 1", "x = 1  # noqa: F841")
    assert bloqueado(r)
    assert "# noqa: F841" in r.stderr


@pytest.mark.parametrize(
    "comentario",
    [
        "# noqa",
        "#noqa:E501",
        "# NOQA",
        "# noqa: complexipy",
        "# ruff: noqa: F401",
        "# flake8: noqa",
        "# ruff: disable[F401]",
        "# type: ignore",
        "# type: ignore[attr-defined]",
        "# ty: ignore[invalid-assignment]",
        "# pyright: ignore[reportAttributeAccessIssue]",
        "# pyright: basic",
        "# mypy: ignore-errors",
        '# mypy: disable-error-code="attr-defined"',
        "# pragma: no cover",
        "# pragma: no branch",
        "# pragma: no mutate",
        "# nosec B101",
        "# nosemgrep",
        "# pylint: disable=unused-import",
    ],
)
def test_reconoce_los_comentarios_que_silencian(proyecto, comentario):
    raiz, temporal = proyecto
    entrada = {"file_path": str(raiz / "nuevo.py"), "content": f"x = 1  {comentario}\n"}
    assert bloqueado(silenciar("Write", entrada, raiz, temporal))


@pytest.mark.parametrize("comentario", ["# fmt: off", "# isort: skip", "# pyright: strict", "# no hace falta"])
def test_deja_los_comentarios_que_no_silencian(proyecto, comentario):
    raiz, temporal = proyecto
    entrada = {"file_path": str(raiz / "nuevo.py"), "content": f"x = 1  {comentario}\n"}
    assert silenciar("Write", entrada, raiz, temporal).returncode == 0


def test_solo_mira_archivos_de_python(proyecto):
    raiz, temporal = proyecto
    notas = {"file_path": str(raiz / "notas.md"), "content": "Usa `# noqa` lo menos posible.\n"}
    assert silenciar("Write", notas, raiz, temporal).returncode == 0
    stub = {"file_path": str(raiz / "app.pyi"), "content": "x: int  # type: ignore\n"}
    assert bloqueado(silenciar("Write", stub, raiz, temporal))


def test_quitar_o_conservar_una_excepcion_si_se_puede(proyecto):
    raiz, temporal = proyecto
    (raiz / "app.py").write_text("import os  # noqa: F401\nx = 1\n")
    assert editar_codigo(raiz, temporal, "x = 1", "x = 2").returncode == 0
    assert editar_codigo(raiz, temporal, "import os  # noqa: F401", "import os, sys  # noqa: F401").returncode == 0
    assert editar_codigo(raiz, temporal, "import os  # noqa: F401\n", "").returncode == 0
    movido = {"file_path": str(raiz / "app.py"), "content": "x = 2\nimport os  # noqa: F401\n"}
    assert silenciar("Write", movido, raiz, temporal).returncode == 0


def test_ampliar_una_excepcion_cuenta_como_agregarla(proyecto):
    raiz, temporal = proyecto
    (raiz / "app.py").write_text("import os  # noqa: F401\n")
    assert bloqueado(editar_codigo(raiz, temporal, "# noqa: F401", "# noqa: F401, E501"))
    assert bloqueado(editar_codigo(raiz, temporal, "# noqa: F401", "# noqa"))


def test_multiedit_se_revisa_entero(proyecto):
    raiz, temporal = proyecto
    (raiz / "app.py").write_text("x = 1\ny = 2\n")
    edits = [
        {"old_string": "x = 1", "new_string": "x = 3"},
        {"old_string": "y = 2", "new_string": "y = 2  # type: ignore"},
    ]
    assert bloqueado(silenciar("MultiEdit", {"file_path": str(raiz / "app.py"), "edits": edits}, raiz, temporal))


@pytest.mark.parametrize(
    "comando",
    [
        "ruff check . --add-noqa",
        "uv run ruff check --add-noqa='código heredado'",
        "uv run ty check --add-ignore",
        "ty check --update-baseline",
        "uv run complexipy . --snapshot-create",
        "vulture src --make-whitelist > lista_blanca.py",
    ],
)
def test_por_terminal_bloquea_lo_que_silencia_en_bloque(proyecto, comando):
    raiz, temporal = proyecto
    assert bloqueado(silenciar("Bash", {"command": comando}, raiz, temporal))


@pytest.mark.parametrize(
    "comando",
    [
        "sed -i '' 's/$/  # noqa/' app.py",
        "perl -pi -e 's/$/  # type: ignore/' app.py",
        "echo 'y = 2  # type: ignore' >> app.py",
        "printf '# ruff: noqa\\n' | tee -a app.py",
        "cat > nuevo.py <<'EOF'\nx = 1  # pragma: no cover\nEOF",
    ],
)
def test_por_terminal_bloquea_escribir_una_excepcion_en_un_py(proyecto, comando):
    raiz, temporal = proyecto
    assert bloqueado(silenciar("Bash", {"command": comando}, raiz, temporal))


@pytest.mark.parametrize(
    "comando",
    [
        "grep -rn '# noqa' . 2>&1 | head",
        "rg 'type: ignore' -g '*.py' > lista.txt",
        "git commit -m 'no usar --add-noqa ni # noqa'",
        "ruff check --fix app.py",
        "sed -i '' 's/viejo/nuevo/' app.py",
    ],
)
def test_por_terminal_deja_buscar_y_mencionar_excepciones(proyecto, comando):
    raiz, temporal = proyecto
    assert silenciar("Bash", {"command": comando}, raiz, temporal).returncode == 0


def prueba_con(raiz: Path, contenido: str) -> dict:
    return {"file_path": str(raiz / "tests" / "test_x.py"), "content": contenido}


@pytest.mark.parametrize(
    "linea",
    [
        '@pytest.mark.skip(reason="falla en CI")',
        "@pytest.mark.xfail(strict=True)",
        "pytestmark = pytest.mark.skip",
        "@mark.xfail",
        '@pytest.mark.skipif(True, reason="x")',
        '    pytest.skip("todavía no")',
        '    pytest.xfail("se arregla después")',
        '@unittest.skip("lento")',
        "@unittest.expectedFailure",
        '    raise unittest.SkipTest("sin datos")',
        '        self.skipTest("sin datos")',
        '    pytest.exit("listo", returncode=0)',
        "    os._exit(0)",
        '    reporte.outcome = "passed"',
    ],
)
def test_claude_no_puede_saltar_pruebas(proyecto, linea):
    raiz, temporal = proyecto
    r = silenciar("Write", prueba_con(raiz, f"{linea}\ndef test_x():\n    pass\n"), raiz, temporal)
    assert bloqueado(r)


@pytest.mark.parametrize(
    "linea",
    [
        '@pytest.mark.skipif(not torch.cuda.is_available(), reason="requiere GPU")',
        '@unittest.skipIf(sys.platform == "win32", "solo Unix")',
    ],
)
def test_saltar_segun_el_entorno_lo_confirma_la_persona(proyecto, linea):
    raiz, temporal = proyecto
    r = silenciar("Write", prueba_con(raiz, f"{linea}\ndef test_x():\n    pass\n"), raiz, temporal)
    assert r.returncode == 0
    salida = json.loads(r.stdout)["hookSpecificOutput"]
    assert salida["permissionDecision"] == "ask" and "skip" in salida["permissionDecisionReason"]


@pytest.mark.parametrize(
    "contenido",
    [
        'torch = pytest.importorskip("torch")\n',
        "@saltar_sin_gpu\ndef test_x():\n    pass\n",
        "def test_skip_de_lineas_vacias():\n    assert recortar('') == ''\n",
    ],
)
def test_deja_lo_que_no_salta_pruebas(proyecto, contenido):
    raiz, temporal = proyecto
    r = silenciar("Write", prueba_con(raiz, contenido), raiz, temporal)
    assert r.returncode == 0 and r.stdout == ""


def test_una_prueba_ya_saltada_se_puede_editar(proyecto):
    raiz, temporal = proyecto
    (raiz / "app.py").write_text('@pytest.mark.skip(reason="x")\ndef test_x():\n    assert 1\n')
    assert editar_codigo(raiz, temporal, "assert 1", "assert 2").returncode == 0


def test_por_terminal_tampoco_se_saltan_pruebas(proyecto):
    raiz, temporal = proyecto
    comando = "sed -i '' 's/^def test_x/@pytest.mark.skip\\ndef test_x/' tests/test_a.py"
    assert bloqueado(silenciar("Bash", {"command": comando}, raiz, temporal))


def test_la_persona_puede_permitirlo_en_una_sesion(proyecto, monkeypatch):
    raiz, temporal = proyecto
    monkeypatch.setenv("CALIDAD_PYTHON_PERMITIR_SILENCIAR", "1")
    assert editar_codigo(raiz, temporal, "x = 1", "x = 1  # noqa: F841").returncode == 0
    assert silenciar("Bash", {"command": "ruff check --add-noqa"}, raiz, temporal).returncode == 0


def test_entrada_rara_no_bloquea(proyecto):
    raiz, temporal = proyecto
    assert correr("no_silenciar.py", {}, raiz, temporal).returncode == 0
    assert correr("no_silenciar.py", {"tool_name": "Edit", "tool_input": None}, raiz, temporal).returncode == 0
    r = subprocess.run(
        [sys.executable, "-I", str(HOOKS / "no_silenciar.py")], input="no es json", capture_output=True, text=True
    )
    assert r.returncode == 0


# --- notificar.py ---


def test_notificacion_pasa_el_texto_como_argumento(proyecto, tmp_path):
    raiz, temporal = proyecto
    bin_falso = tmp_path / "bin"
    bin_falso.mkdir()
    registro = tmp_path / "osascript.args"
    script = bin_falso / "osascript"
    script.write_text(f'#!/bin/sh\nfor a in "$@"; do echo "$a" >> "{registro}"; done\n')
    script.chmod(0o755)
    datos = {"message": 'Hola" & do shell script "rm', "title": "Permiso"}
    r = correr("notificar.py", datos, raiz, temporal, path_extra=str(bin_falso))
    assert r.returncode == 0
    if sys.platform == "darwin":
        lineas = registro.read_text().splitlines()
        assert lineas[-2:] == ['Hola" & do shell script "rm', "Permiso"]
