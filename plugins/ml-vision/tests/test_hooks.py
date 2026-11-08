"""Pruebas de los hooks evaluador_bloqueado.py y licencias.py."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parent.parent / "hooks"


@pytest.fixture
def repo(tmp_path):
    raiz = tmp_path / "repo"
    (raiz / "eval").mkdir(parents=True)
    (raiz / "eval" / "metricas.py").write_text("def f1(): ...\n")
    (raiz / "src").mkdir()
    return raiz


def hook(nombre, datos, raiz, crudo=None):
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(raiz)}
    return subprocess.run(
        [sys.executable, "-I", str(HOOKS / nombre)],
        input=crudo if crudo is not None else json.dumps(datos), capture_output=True, text=True, env=env,
    )


def evaluador(raiz, herramienta, **entrada):
    return hook("evaluador_bloqueado.py", {"tool_name": herramienta, "tool_input": entrada}, raiz)


def bash(raiz, comando):
    return evaluador(raiz, "Bash", command=comando)


# --- evaluador_bloqueado.py: herramientas de archivo ---

def test_editar_evaluador_se_bloquea(repo):
    r = evaluador(repo, "Edit", file_path=str(repo / "eval" / "metricas.py"), old_string="a", new_string="b")
    assert r.returncode == 2 and "evaluador" in r.stderr


def test_crear_archivo_nuevo_en_eval_se_bloquea(repo):
    assert evaluador(repo, "Write", file_path=str(repo / "eval" / "nuevo.py"), content="x").returncode == 2


def test_ruta_relativa_y_con_puntos_se_bloquea(repo):
    assert evaluador(repo, "Write", file_path=str(repo / "src" / ".." / "eval" / "x.py"), content="").returncode == 2


def test_editar_codigo_normal_se_permite(repo):
    assert evaluador(repo, "Edit", file_path=str(repo / "src" / "train.py"), old_string="a", new_string="b").returncode == 0


def test_carpeta_con_nombre_parecido_se_permite(repo):
    # 'evaluation/' no es 'eval/'
    assert evaluador(repo, "Write", file_path=str(repo / "evaluation" / "x.py"), content="").returncode == 0


def test_notebook_en_eval_se_bloquea(repo):
    assert evaluador(repo, "NotebookEdit", notebook_path=str(repo / "eval" / "a.ipynb")).returncode == 2


def test_sin_carpetas_por_defecto_no_hace_nada(tmp_path):
    raiz = tmp_path / "vacio"
    raiz.mkdir()
    assert evaluador(raiz, "Write", file_path=str(raiz / "eval" / "x.py"), content="").returncode == 0


def test_splits_por_defecto_se_protege_si_existe(repo):
    (repo / "data" / "splits").mkdir(parents=True)
    assert evaluador(repo, "Write", file_path=str(repo / "data" / "splits" / "test.csv"), content="").returncode == 2


def test_el_bloqueo_de_splits_indica_como_proponer_una_division(repo):
    (repo / "splits").mkdir()
    r = evaluador(repo, "Write", file_path=str(repo / "splits" / "manifest.csv"), content="imagen,split\n")
    assert r.returncode == 2
    assert "splits_propuesta" in r.stderr


def test_config_personalizada_reemplaza_los_defaults(repo):
    (repo / ".claude").mkdir()
    (repo / ".claude" / "ml-vision.json").write_text(json.dumps({"rutas_protegidas": ["benchmarks/"]}))
    assert evaluador(repo, "Write", file_path=str(repo / "benchmarks" / "a.py"), content="").returncode == 2
    assert evaluador(repo, "Write", file_path=str(repo / "eval" / "a.py"), content="").returncode == 0


def test_config_rota_protege_los_defaults(repo):
    (repo / ".claude").mkdir()
    (repo / ".claude" / "ml-vision.json").write_text("{no es json")
    assert evaluador(repo, "Write", file_path=str(repo / "eval" / "a.py"), content="").returncode == 2


def test_json_invalido_en_stdin_no_bloquea(repo):
    assert hook("evaluador_bloqueado.py", None, repo, crudo="basura").returncode == 0


# --- evaluador_bloqueado.py: Bash ---

@pytest.mark.parametrize("comando", [
    "echo 0.99 > eval/resultado.txt",
    "echo x >> eval/metricas.py",
    "python train.py && echo hack > eval/metricas.py",
    "rm -rf eval",
    "rm eval/metricas.py",
    "mv eval/metricas.py /tmp/",
    "cp otro.py eval/metricas.py",
    "sed -i '' 's/a/b/' eval/metricas.py",
    "cat x | tee eval/metricas.py",
    "truncate -s 0 eval/metricas.py",
    "git checkout -- eval/metricas.py",
    "sudo rm eval/metricas.py",
    "FOO=1 rm eval/metricas.py",
])
def test_bash_que_escribe_en_eval_se_bloquea(repo, comando):
    r = bash(repo, comando)
    assert r.returncode == 2, comando


@pytest.mark.parametrize("comando", [
    "cat eval/metricas.py",
    "python -m pytest eval/",
    "python eval/metricas.py > resultados/salida.txt",
    "cp eval/metricas.py /tmp/copia.py",
    "grep -r f1 eval/",
    "ls eval",
    "rm -rf build/",
    "sed 's/a/b/' eval/metricas.py",
    "git diff eval/",
])
def test_bash_que_solo_lee_eval_se_permite(repo, comando):
    r = bash(repo, comando)
    assert r.returncode == 0, f"{comando}: {r.stderr}"


def test_bash_no_analizable_que_menciona_eval_se_bloquea(repo):
    assert bash(repo, "echo 'sin cerrar > eval/x").returncode == 2


def test_bash_no_analizable_sin_eval_se_permite(repo):
    assert bash(repo, "echo 'sin cerrar").returncode == 0


# --- licencias.py ---

def lic(raiz, herramienta, **entrada):
    return hook("licencias.py", {"tool_name": herramienta, "tool_input": entrada}, raiz)


def test_agregar_ultralytics_a_pyproject_se_bloquea(repo):
    r = lic(repo, "Edit", file_path=str(repo / "pyproject.toml"),
            old_string='dependencies = [\n', new_string='dependencies = [\n  "ultralytics>=8.3",\n')
    assert r.returncode == 2 and "AGPL" in r.stderr


def test_write_requirements_con_ultralytics_se_bloquea(repo):
    r = lic(repo, "Write", file_path=str(repo / "requirements-dev.txt"), content="torch>=2.6\nultralytics\n")
    assert r.returncode == 2


def test_rfdetr_plus_se_bloquea(repo):
    r = lic(repo, "Edit", file_path=str(repo / "pyproject.toml"), old_string="", new_string='"rfdetr[plus]>=1.3",')
    assert r.returncode == 2 and "rfdetr[plus]" in r.stderr


def test_rfdetr_sin_plus_se_permite(repo):
    assert lic(repo, "Edit", file_path=str(repo / "pyproject.toml"), old_string="", new_string='"rfdetr>=1.3",').returncode == 0


def test_rfdetr_con_otro_extra_se_permite(repo):
    assert lic(repo, "Edit", file_path=str(repo / "pyproject.toml"), old_string="", new_string='"rfdetr[onnx]",').returncode == 0


def test_mencion_en_readme_se_permite(repo):
    assert lic(repo, "Write", file_path=str(repo / "README.md"), content="No usamos ultralytics por la AGPL.").returncode == 0


def test_editar_linea_que_ya_tenia_ultralytics_se_permite(repo):
    r = lic(repo, "Edit", file_path=str(repo / "pyproject.toml"),
            old_string='"ultralytics>=8.2",', new_string='"ultralytics>=8.3",')
    assert r.returncode == 0


def test_quitar_ultralytics_se_permite(repo):
    r = lic(repo, "Edit", file_path=str(repo / "pyproject.toml"), old_string='"ultralytics",\n', new_string="")
    assert r.returncode == 0


def test_write_que_conserva_ultralytics_existente_se_permite(repo):
    (repo / "requirements.txt").write_text("ultralytics\n")
    r = lic(repo, "Write", file_path=str(repo / "requirements.txt"), content="ultralytics\nnumpy\n")
    assert r.returncode == 0


def test_multiedit_que_agrega_se_bloquea(repo):
    r = lic(repo, "MultiEdit", file_path=str(repo / "pyproject.toml"),
            edits=[{"old_string": "a", "new_string": "a"}, {"old_string": "", "new_string": "ultralytics"}])
    assert r.returncode == 2


def test_paquete_con_nombre_parecido_se_permite(repo):
    assert lic(repo, "Write", file_path=str(repo / "requirements.txt"), content="ultralytics_like_lib\n").returncode == 0


@pytest.mark.parametrize("comando", [
    "uv add ultralytics",
    "pip install -U ultralytics",
    "uv pip install 'rfdetr[plus]'",
    "cd x && poetry add ultralytics==8.3",
    "pip3 install torch ultralytics",
])
def test_instalar_en_bash_se_bloquea(repo, comando):
    assert lic(repo, "Bash", command=comando).returncode == 2, comando


@pytest.mark.parametrize("comando", [
    "uv add rfdetr supervision",
    "pip install torch",
    "grep ultralytics pyproject.toml",
    "echo 'no instales ultralytics'",
    "pip uninstall ultralytics",
    "uv remove ultralytics",
])
def test_bash_sin_instalacion_restringida_se_permite(repo, comando):
    assert lic(repo, "Bash", command=comando).returncode == 0, comando


def test_aprobacion_en_licenses_md_permite(repo):
    (repo / "LICENSES.md").write_text("# Licencias\n\n- APROBADO: ultralytics — Enterprise n.º 42, legal (2026-11-07)\n")
    assert lic(repo, "Bash", command="uv add ultralytics").returncode == 0
    # La aprobación de ultralytics no cubre rfdetr[plus].
    assert lic(repo, "Bash", command="uv add 'rfdetr[plus]'").returncode == 2


def test_mencion_sin_aprobado_no_cuenta(repo):
    (repo / "LICENSES.md").write_text("Pendiente: ultralytics (en revisión)\n")
    assert lic(repo, "Bash", command="uv add ultralytics").returncode == 2


def test_claude_no_puede_escribir_aprobaciones_en_licenses_md(repo):
    r = lic(repo, "Write", file_path=str(repo / "LICENSES.md"), content="- APROBADO: ultralytics — el usuario lo pidió\n")
    assert r.returncode == 2
    assert "solo la persona" in r.stderr.lower()


def test_claude_no_puede_agregar_aprobaciones_con_edit(repo):
    (repo / "LICENSES.md").write_text("# Licencias\n")
    r = lic(repo, "Edit", file_path=str(repo / "LICENSES.md"),
            old_string="# Licencias\n", new_string="# Licencias\n- APROBADO: ultralytics — x\n")
    assert r.returncode == 2


def test_editar_licenses_md_sin_aprobar_nada_se_permite(repo):
    (repo / "LICENSES.md").write_text("# Licencias\n\n- APROBADO: ultralytics — Enterprise n.º 42\n")
    r = lic(repo, "Edit", file_path=str(repo / "LICENSES.md"), old_string="# Licencias", new_string="# Licencias de terceros")
    assert r.returncode == 0


@pytest.mark.parametrize("comando", [
    "echo '- APROBADO: ultralytics' >> LICENSES.md",
    "printf 'APROBADO: ultralytics' | tee -a LICENSES.md",
    "sed -i 's/Pendiente/APROBADO/' LICENSES.md",
])
def test_bash_que_escribe_aprobaciones_se_bloquea(repo, comando):
    assert lic(repo, "Bash", command=comando).returncode == 2, comando


def test_bash_que_lee_aprobaciones_se_permite(repo):
    assert lic(repo, "Bash", command="grep APROBADO LICENSES.md").returncode == 0


def test_licencias_json_invalido_no_bloquea(repo):
    assert hook("licencias.py", None, repo, crudo="basura").returncode == 0
