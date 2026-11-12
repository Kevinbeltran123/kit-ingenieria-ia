"""Pruebas de skills/explicar-resultado/scripts/resultado.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "skills" / "explicar-resultado" / "scripts" / "resultado.py"

RESULTADO = {"auc": {"media": 0.87, "por_lote": {"3-2008": 0.83}}, "n_lotes": 11, "nota": "texto", "ok": True}


def explicacion_valida() -> dict:
    return {
        "titulo": "Separabilidad de copas afectadas",
        "pregunta": "¿La imagen distingue copas afectadas de normales?",
        "como_se_hizo": "Un vuelo por lote; modelo congelado y regresión logística; validación por lote.",
        "afirmaciones": [
            {
                "texto": "El AUC medio por lote es {valor}.",
                "clave": "auc.media",
                "referencia": "etiqueta_historica",
                "alcance": {"unidades": 8980, "grupos": 11, "descripcion": "8.980 palmas de 11 lotes"},
                "no_comprobado": ["Los otros 17 lotes"],
            }
        ],
        "alertas": [],
        "siguiente": "Medir contra verificación de campo.",
    }


def preparar(carpeta: Path, explicacion: dict | None = None, resultado: object = RESULTADO) -> None:
    (carpeta / "resultado.json").write_text(json.dumps(resultado), encoding="utf-8")
    if explicacion is not None:
        (carpeta / "explicacion.json").write_text(json.dumps(explicacion), encoding="utf-8")


def correr(orden: str, carpeta: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), orden, str(carpeta)], capture_output=True, text=True, check=False
    )


def test_plantilla_lista_solo_las_cifras(tmp_path):
    preparar(tmp_path)
    assert correr("plantilla", tmp_path).returncode == 0
    creada = json.loads((tmp_path / "explicacion.json").read_text(encoding="utf-8"))
    assert creada["claves_disponibles"] == ["auc.media", "auc.por_lote.3-2008", "n_lotes"]


def test_plantilla_no_sobrescribe(tmp_path):
    preparar(tmp_path, explicacion_valida())
    assert correr("plantilla", tmp_path).returncode == 1
    assert json.loads((tmp_path / "explicacion.json").read_text(encoding="utf-8"))["titulo"]


def test_construir_pone_la_cifra_del_resultado(tmp_path):
    preparar(tmp_path, explicacion_valida())
    salida = correr("construir", tmp_path)
    assert salida.returncode == 0, salida.stderr
    texto = (tmp_path / "explicacion.md").read_text(encoding="utf-8")
    assert "El AUC medio por lote es 0.87." in texto
    assert "Los otros 17 lotes" in texto


def test_avisa_cuando_la_referencia_es_historica(tmp_path):
    preparar(tmp_path, explicacion_valida())
    correr("construir", tmp_path)
    assert "no desempeño" in (tmp_path / "explicacion.md").read_text(encoding="utf-8")


def test_rechaza_cifra_escrita_a_mano(tmp_path):
    explicacion = explicacion_valida()
    explicacion["afirmaciones"][0]["texto"] = "El AUC es 0.95, es decir {valor}."
    preparar(tmp_path, explicacion)
    salida = correr("construir", tmp_path)
    assert salida.returncode == 1
    assert "cifra escrita a mano" in salida.stderr
    assert not (tmp_path / "explicacion.md").exists()


def test_rechaza_clave_que_no_existe(tmp_path):
    explicacion = explicacion_valida()
    explicacion["afirmaciones"][0]["clave"] = "auc.maxima"
    preparar(tmp_path, explicacion)
    salida = correr("construir", tmp_path)
    assert salida.returncode == 1
    assert "no está en resultado.json" in salida.stderr


def test_rechaza_no_comprobado_vacio(tmp_path):
    explicacion = explicacion_valida()
    explicacion["afirmaciones"][0]["no_comprobado"] = ["  "]
    preparar(tmp_path, explicacion)
    salida = correr("construir", tmp_path)
    assert salida.returncode == 1
    assert "no_comprobado" in salida.stderr


def test_rechaza_referencia_y_alcance_invalidos(tmp_path):
    explicacion = explicacion_valida()
    explicacion["afirmaciones"][0]["referencia"] = "censo"
    explicacion["afirmaciones"][0]["alcance"]["grupos"] = None
    preparar(tmp_path, explicacion)
    salida = correr("construir", tmp_path)
    assert salida.returncode == 1
    assert "referencia debe ser" in salida.stderr
    assert "alcance.grupos" in salida.stderr


def test_error_abierto_sale_con_2_y_deja_la_explicacion(tmp_path):
    explicacion = explicacion_valida()
    explicacion["alertas"] = [{"tipo": "bug", "estado": "abierta", "texto": "Etiquetas corridas una línea en un lote."}]
    preparar(tmp_path, explicacion)
    salida = correr("construir", tmp_path)
    assert salida.returncode == 2
    assert "Etiquetas corridas" in (tmp_path / "explicacion.md").read_text(encoding="utf-8")


def test_alerta_descartada_necesita_motivo(tmp_path):
    explicacion = explicacion_valida()
    explicacion["alertas"] = [{"tipo": "riesgo", "estado": "descartada", "texto": "Pocos lotes."}]
    preparar(tmp_path, explicacion)
    salida = correr("construir", tmp_path)
    assert salida.returncode == 1
    assert "motivo" in salida.stderr


def test_resultado_sin_cifras_o_roto(tmp_path):
    preparar(tmp_path, resultado={"nota": "nada"})
    assert correr("plantilla", tmp_path).returncode == 1
    (tmp_path / "resultado.json").write_text("{", encoding="utf-8")
    assert correr("construir", tmp_path).returncode == 1
