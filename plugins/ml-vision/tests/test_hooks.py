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


def evaluador(raiz, herramienta, cwd=None, **entrada):
    datos = {"tool_name": herramienta, "tool_input": entrada}
    if cwd is not None:
        datos["cwd"] = str(cwd)
    return hook("evaluador_bloqueado.py", datos, raiz)


def bash(raiz, comando, cwd=None):
    return evaluador(raiz, "Bash", cwd=cwd, command=comando)


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


def config(repo, rutas):
    (repo / ".claude").mkdir(exist_ok=True)
    archivo = repo / ".claude" / "ml-vision.json"
    archivo.write_text(json.dumps({"rutas_protegidas": rutas}))
    return archivo


def test_la_configuracion_no_la_cambia_el_agente(repo):
    """Si pudiera editarla, el agente vaciaría rutas_protegidas y después escribiría en eval/."""
    archivo = config(repo, ["eval/"])
    r = evaluador(repo, "Write", file_path=str(archivo), content='{"rutas_protegidas": []}')
    assert r.returncode == 2 and "configuración" in r.stderr
    assert evaluador(repo, "Edit", file_path=str(archivo), old_string="eval/", new_string="x/").returncode == 2


def test_tampoco_puede_crear_una_que_desproteja_los_defaults(repo):
    archivo = repo / ".claude" / "ml-vision.json"  # no existe; eval/ está protegido por defecto
    assert evaluador(repo, "Write", file_path=str(archivo), content='{"rutas_protegidas": []}').returncode == 2


@pytest.mark.parametrize("comando", [
    "echo '{\"rutas_protegidas\": []}' > .claude/ml-vision.json",
    "rm .claude/ml-vision.json",
    "mv .claude/ml-vision.json /tmp/x",
    "sed -i '' 's/eval//' .claude/ml-vision.json",
])
def test_bash_que_cambia_la_configuracion_se_bloquea(repo, comando):
    config(repo, ["eval/"])
    assert bash(repo, comando).returncode == 2, comando


def test_leer_la_configuracion_se_permite(repo):
    config(repo, ["eval/"])
    assert bash(repo, "cat .claude/ml-vision.json").returncode == 0


def test_sin_nada_protegido_se_puede_crear_la_configuracion(tmp_path):
    raiz = tmp_path / "vacio"
    raiz.mkdir()
    archivo = raiz / ".claude" / "ml-vision.json"
    r = evaluador(raiz, "Write", file_path=str(archivo), content='{"rutas_protegidas": ["eval/"]}')
    assert r.returncode == 0


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


@pytest.mark.parametrize("comando", [
    "echo listo\nrm eval/metricas.py",              # cada línea es un comando
    "make &&\nrm eval/metricas.py",
    "echo hola # nota\nrm eval/metricas.py",        # el comentario no se come la línea siguiente
    "rm -f \\\n  eval/metricas.py",                # línea continuada con barra invertida
    "(echo a);rm eval/metricas.py",                 # shlex junta ");" en un solo token
    "true&&(rm eval/metricas.py)",
    "echo `rm eval/metricas.py`",
    "echo $(rm eval/metricas.py)",
    'bash -c "rm eval/metricas.py"',
    "sh -c 'echo x > eval/metricas.py'",
    'bash -lc "cd eval && rm metricas.py"',
    "eval 'rm eval/metricas.py'",
    "time rm eval/metricas.py",
    "cd eval && rm metricas.py",
    "cd eval; echo hack > metricas.py",
    "cd src && cd ../eval && rm metricas.py",
    "(cd /tmp); rm eval/metricas.py",               # el cd del subshell no cambia el de afuera
    'cd "$(git rev-parse --show-toplevel)" && rm eval/metricas.py',  # destino desconocido: no mueve
])
def test_bash_que_escribe_en_eval_por_caminos_indirectos_se_bloquea(repo, comando):
    assert bash(repo, comando).returncode == 2, comando


@pytest.mark.parametrize("comando", [
    "cd src && rm -rf build",
    "(cd eval && ls) && rm -rf build",              # al cerrar el subshell vuelve a la raíz
    "cd eval && cat metricas.py",
    'bash -c "cat eval/metricas.py"',
    "cat eval/metricas.py\nls eval",
    "python eval/metricas.py 2>&1 | tee resultados/log.txt",
    "cat > notas.md <<'EOF'\nno tocar eval/metricas.py\nEOF",
    'cd "$(git rev-parse --show-toplevel)" && python eval/metricas.py',
])
def test_bash_indirecto_que_no_escribe_en_eval_se_permite(repo, comando):
    r = bash(repo, comando)
    assert r.returncode == 0, f"{comando}: {r.stderr}"


def test_bash_resuelve_rutas_desde_el_cwd_de_la_sesion(repo):
    """El cwd de la sesión cambia con los `cd` de comandos anteriores: las rutas relativas parten de ahí."""
    assert bash(repo, "rm ../eval/metricas.py", cwd=repo / "src").returncode == 2
    assert bash(repo, "rm eval/metricas.py", cwd=repo / "src").returncode == 0  # sería src/eval, que no existe


def test_eval_de_un_worktree_tambien_se_protege(repo):
    def git(*args):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)

    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    git("add", ".")
    git("commit", "-qm", "base")
    wt = repo / ".claude" / "worktrees" / "rama"
    git("worktree", "add", "-q", "-b", "rama", str(wt))
    assert evaluador(repo, "Edit", file_path=str(wt / "eval" / "metricas.py"), old_string="a", new_string="b").returncode == 2
    assert bash(repo, "rm eval/metricas.py", cwd=wt).returncode == 2
    assert evaluador(repo, "Write", file_path=str(wt / "src" / "train.py"), content="").returncode == 0
    # y la configuración propia del worktree
    assert evaluador(repo, "Write", file_path=str(wt / ".claude" / "ml-vision.json"), content="{}").returncode == 2


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


@pytest.mark.parametrize("comando", [
    "uv run --with ultralytics python train.py",
    "uv run --with=ultralytics python train.py",
    "uvx ultralytics settings",
    "uvx --from ultralytics yolo train data=palmas.yaml",
    "uv tool install ultralytics",
    "pipx install ultralytics",
    "pipx run --spec ultralytics yolo",
    "python -m pip install ultralytics",
    "sudo -H pip install ultralytics",
    'bash -c "pip install ultralytics"',
    "docker run --rm img pip install ultralytics",
    "uv run pip install ultralytics",
    "echo listo\npip install ultralytics",
    "ssh gpu 'pip install ultralytics'",
])
def test_instalar_o_ejecutar_por_otras_vias_se_bloquea(repo, comando):
    assert lic(repo, "Bash", command=comando).returncode == 2, comando


@pytest.mark.parametrize("comando", [
    'grep -rn "pip install ultralytics" docs/',
    'git commit -m "docs: no usar uv add ultralytics (AGPL)"',
    'gh pr create --title x --body "Se evita pip install ultralytics; usamos rfdetr"',
    "uv run python scripts/ultralytics/convertir.py",   # uv run solo instala lo de --with
    "uvx ruff check ultralytics/",                       # lo que va después de la herramienta es suyo
])
def test_texto_que_menciona_una_instalacion_se_permite(repo, comando):
    r = lic(repo, "Bash", command=comando)
    assert r.returncode == 0, f"{comando}: {r.stderr}"


def test_requirements_en_carpeta_se_revisa(repo):
    r = lic(repo, "Write", file_path=str(repo / "requirements" / "base.txt"), content="torch\nultralytics\n")
    assert r.returncode == 2


PEP723 = '# /// script\n# dependencies = [\n#   "numpy",\n# ]\n# ///\nimport numpy\n'


def test_script_con_bloque_pep723_se_revisa(repo):
    contenido = PEP723.replace('"numpy",', '"numpy",\n#   "ultralytics",')
    assert lic(repo, "Write", file_path=str(repo / "tools" / "entrenar.py"), content=contenido).returncode == 2


def test_editar_el_bloque_pep723_se_revisa(repo):
    script = repo / "entrenar.py"
    script.write_text(PEP723)
    r = lic(repo, "Edit", file_path=str(script), old_string='#   "numpy",\n', new_string='#   "numpy",\n#   "ultralytics",\n')
    assert r.returncode == 2


def test_importar_en_codigo_sin_declararlo_se_permite(repo):
    r = lic(repo, "Write", file_path=str(repo / "src" / "detectar.py"), content="from ultralytics import YOLO\n")
    assert r.returncode == 0


def test_setup_py_sigue_revisandose(repo):
    r = lic(repo, "Edit", file_path=str(repo / "setup.py"), old_string="", new_string='install_requires=["ultralytics"]')
    assert r.returncode == 2


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


@pytest.mark.parametrize("nombre, contenido", [
    ("Dockerfile", "FROM python:3.12-slim\nRUN pip install ultralytics\n"),
    ("Dockerfile.gpu", "FROM python:3.12\nRUN --mount=type=cache,target=/root/.cache/uv \\\n"
                       "    uv pip install --system ultralytics\n"),
    ("api.Dockerfile", 'FROM python:3.12\nRUN ["pip", "install", "rfdetr[plus]"]\n'),
    ("Containerfile", "FROM python:3.12\nRUN <<EOF\npip install ultralytics\nEOF\n"),
    ("Dockerfile", "FROM ultralytics/ultralytics:8.3.0\nCOPY . /app\n"),
])
def test_dockerfile_que_trae_un_paquete_restringido_se_bloquea(repo, nombre, contenido):
    r = lic(repo, "Write", file_path=str(repo / nombre), content=contenido)
    assert r.returncode == 2 and "aprobación de licencia" in r.stderr


def test_dockerfile_sin_paquetes_restringidos_se_permite(repo):
    contenido = ("# syntax=docker/dockerfile:1\n# no instalamos ultralytics: es AGPL\nFROM python:3.12-slim\n"
                 'RUN uv sync --locked\nLABEL nota="pip install ultralytics"\n')
    assert lic(repo, "Write", file_path=str(repo / "Dockerfile"), content=contenido).returncode == 0


def test_dockerfile_que_ya_lo_tenia_se_puede_editar(repo):
    (repo / "Dockerfile").write_text("FROM python:3.12\nRUN pip install ultralytics\nRUN echo hola\n")
    r = lic(repo, "Edit", file_path=str(repo / "Dockerfile"), old_string="RUN echo hola", new_string="RUN echo chao")
    assert r.returncode == 0


def test_dockerfile_aprobado_en_licenses_se_permite(repo):
    (repo / "LICENSES.md").write_text("APROBADO: ultralytics — licencia Enterprise n.º 1, legal (2026-11-08)\n")
    r = lic(repo, "Write", file_path=str(repo / "Dockerfile"), content="FROM python:3.12\nRUN pip install ultralytics\n")
    assert r.returncode == 0


def test_licencias_json_invalido_no_bloquea(repo):
    assert hook("licencias.py", None, repo, crudo="basura").returncode == 0
