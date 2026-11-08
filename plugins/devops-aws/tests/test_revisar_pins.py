import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "skills" / "gha-seguro" / "scripts" / "revisar_pins.py"
SHA = "a" * 40


def correr(*rutas):
    return subprocess.run([sys.executable, "-I", str(SCRIPT), *map(str, rutas)], capture_output=True, text=True)


def workflow(tmp_path, cuerpo: str) -> Path:
    carpeta = tmp_path / ".github" / "workflows"
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = carpeta / "ci.yml"
    archivo.write_text(cuerpo)
    return tmp_path / ".github"


def test_workflow_bien_fijado_pasa(tmp_path):
    gh = workflow(tmp_path, f"""on: push
permissions:
  contents: read
jobs:
  t:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{SHA} # v5
      - uses: ./acciones/local
      - uses: docker://alpine@sha256:{'b' * 64}
""")
    r = correr(gh)
    assert r.returncode == 0, r.stdout


def test_tag_sin_sha_falla(tmp_path):
    gh = workflow(tmp_path, "permissions: {}\njobs:\n  t:\n    steps:\n      - uses: actions/checkout@v5\n")
    r = correr(gh)
    assert r.returncode == 1
    assert "actions/checkout@v5" in r.stdout


def test_comillas_y_rama_fallan(tmp_path):
    gh = workflow(tmp_path, "permissions: {}\nsteps:\n  - uses: 'aquasecurity/trivy-action@master'\n")
    r = correr(gh)
    assert r.returncode == 1 and "trivy-action@master" in r.stdout


def test_imagen_docker_sin_digest_falla(tmp_path):
    gh = workflow(tmp_path, "permissions: {}\nsteps:\n  - uses: docker://alpine:3.20\n")
    assert correr(gh).returncode == 1


def test_falta_permissions_falla(tmp_path):
    gh = workflow(tmp_path, f"on: push\njobs:\n  t:\n    steps:\n      - uses: actions/checkout@{SHA}\n")
    r = correr(gh)
    assert r.returncode == 1 and "permissions" in r.stdout


def test_action_compuesta_no_exige_permissions(tmp_path):
    accion = tmp_path / ".github" / "actions" / "x"
    accion.mkdir(parents=True)
    (accion / "action.yml").write_text(f"runs:\n  steps:\n    - uses: actions/setup-python@{SHA}\n")
    assert correr(tmp_path / ".github").returncode == 0
