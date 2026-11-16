"""Pruebas de skills/explicar-resultado/scripts/resultado.py."""

from __future__ import annotations

import hashlib
import json
import re
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
    assert "El AUC medio por lote es 0.87 (medida contra una etiqueta histórica" in texto
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


HIPOTESIS = {"hipotesis": {"texto": "El AUC medio por lote supera el umbral fijado", "umbrales": {"auc.media": 0.8}}}


def explicacion_con_veredicto(carpeta: Path, estado: str = "no_aplica", texto: str = "No había hipótesis.") -> dict:
    """Explicación con veredicto y ancla, sobre el resultado ya escrito en la carpeta."""
    explicacion = explicacion_valida()
    explicacion["veredicto"] = {"estado": estado, "texto": texto}
    explicacion["resultado_sha256"] = hashlib.sha256((carpeta / "resultado.json").read_bytes()).hexdigest()
    return explicacion


def preparar_con_veredicto(carpeta: Path, estado: str, texto: str, referencia: str = "campo", config=HIPOTESIS) -> None:
    preparar(carpeta)
    explicacion = explicacion_con_veredicto(carpeta, estado, texto)
    explicacion["afirmaciones"][0]["referencia"] = referencia
    (carpeta / "explicacion.json").write_text(json.dumps(explicacion), encoding="utf-8")
    if config is not None:
        (carpeta / "config.json").write_text(json.dumps(config), encoding="utf-8")


def test_explicacion_antigua_valida_con_aviso(tmp_path):
    preparar(tmp_path, explicacion_valida())
    salida = correr("construir", tmp_path)
    assert salida.returncode == 0, salida.stderr
    assert "AVISO" in salida.stderr
    assert "veredicto" in salida.stderr
    assert "resultado_sha256" in salida.stderr


def test_plantilla_ancla_el_resultado_y_pide_veredicto(tmp_path):
    preparar(tmp_path)
    correr("plantilla", tmp_path)
    creada = json.loads((tmp_path / "explicacion.json").read_text(encoding="utf-8"))
    assert creada["resultado_sha256"] == hashlib.sha256((tmp_path / "resultado.json").read_bytes()).hexdigest()
    assert creada["veredicto"] == {"estado": "", "texto": ""}


def test_veredicto_no_aplica_sin_avisos(tmp_path):
    preparar(tmp_path)
    (tmp_path / "explicacion.json").write_text(json.dumps(explicacion_con_veredicto(tmp_path)), encoding="utf-8")
    salida = correr("construir", tmp_path)
    assert salida.returncode == 0, salida.stderr
    assert "AVISO" not in salida.stderr
    texto = (tmp_path / "explicacion.md").read_text(encoding="utf-8")
    assert "## Veredicto" in texto
    assert "no_aplica" in texto


def test_rechaza_explicacion_de_otro_resultado(tmp_path):
    preparar(tmp_path)
    (tmp_path / "explicacion.json").write_text(json.dumps(explicacion_con_veredicto(tmp_path)), encoding="utf-8")
    (tmp_path / "resultado.json").write_text(json.dumps({**RESULTADO, "n_lotes": 12}), encoding="utf-8")
    salida = correr("construir", tmp_path)
    assert salida.returncode == 1
    assert "la explicación es de otro resultado: vuelve a explicar" in salida.stderr
    assert not (tmp_path / "explicacion.md").exists()


def test_anclar_reescribe_la_huella(tmp_path):
    preparar(tmp_path)
    (tmp_path / "explicacion.json").write_text(json.dumps(explicacion_con_veredicto(tmp_path)), encoding="utf-8")
    (tmp_path / "resultado.json").write_text(json.dumps({**RESULTADO, "n_lotes": 12}), encoding="utf-8")
    assert correr("anclar", tmp_path).returncode == 0
    salida = correr("construir", tmp_path)
    assert salida.returncode == 0, salida.stderr


def test_veredicto_apoyado_cita_la_cifra(tmp_path):
    preparar_con_veredicto(tmp_path, "se_apoya", "Se apoya: el AUC medio es {a1}, sobre el umbral fijado.")
    salida = correr("construir", tmp_path)
    assert salida.returncode == 0, salida.stderr
    texto = (tmp_path / "explicacion.md").read_text(encoding="utf-8")
    assert "Se apoya: el AUC medio es 0.87, sobre el umbral fijado." in texto


def test_rechaza_estado_y_texto_invalidos(tmp_path):
    preparar_con_veredicto(tmp_path, "confirmada", "")
    salida = correr("construir", tmp_path)
    assert salida.returncode == 1
    assert "veredicto.estado" in salida.stderr
    assert "veredicto.texto" in salida.stderr


def test_veredicto_sin_hipotesis_en_config(tmp_path):
    preparar_con_veredicto(tmp_path, "se_refuta", "Se refuta: el AUC es {a1}.", config=None)
    salida = correr("construir", tmp_path)
    assert salida.returncode == 1
    assert "config.json" in salida.stderr
    preparar_con_veredicto(tmp_path, "se_refuta", "Se refuta: el AUC es {a1}.", config={"hipotesis": {"texto": "x"}})
    salida = correr("construir", tmp_path)
    assert salida.returncode == 1
    assert "umbrales" in salida.stderr


def test_veredicto_debe_citar_una_afirmacion(tmp_path):
    preparar_con_veredicto(tmp_path, "se_apoya", "Se apoya la hipótesis.")
    salida = correr("construir", tmp_path)
    assert salida.returncode == 1
    assert "{a1}" in salida.stderr
    preparar_con_veredicto(tmp_path, "se_apoya", "Se apoya: {a2}.")
    salida = correr("construir", tmp_path)
    assert salida.returncode == 1
    assert "afirmación 2" in salida.stderr


def test_veredicto_rechaza_cifra_escrita_a_mano(tmp_path):
    preparar_con_veredicto(tmp_path, "intermedio", "El AUC es {a1}, apenas sobre 0.8.")
    salida = correr("construir", tmp_path)
    assert salida.returncode == 1
    assert "cifra escrita a mano" in salida.stderr


def test_etiqueta_historica_no_apoya_ni_refuta(tmp_path):
    for estado in ("se_apoya", "se_refuta"):
        preparar_con_veredicto(tmp_path, estado, "El AUC es {a1}.", referencia="etiqueta_historica")
        salida = correr("construir", tmp_path)
        assert salida.returncode == 1
        assert "etiqueta_historica" in salida.stderr
    preparar_con_veredicto(tmp_path, "intermedio", "El AUC es {a1}.", referencia="etiqueta_historica")
    assert correr("construir", tmp_path).returncode == 0


def test_error_abierto_exige_veredicto_no_aplica(tmp_path):
    preparar_con_veredicto(tmp_path, "se_apoya", "El AUC es {a1}.")
    explicacion = json.loads((tmp_path / "explicacion.json").read_text(encoding="utf-8"))
    explicacion["alertas"] = [{"tipo": "bug", "estado": "abierta", "texto": "Etiquetas corridas."}]
    (tmp_path / "explicacion.json").write_text(json.dumps(explicacion), encoding="utf-8")
    salida = correr("construir", tmp_path)
    assert salida.returncode == 1
    assert "no_aplica" in salida.stderr
    explicacion["veredicto"] = {"estado": "no_aplica", "texto": "Hay un error abierto."}
    (tmp_path / "explicacion.json").write_text(json.dumps(explicacion), encoding="utf-8")
    assert correr("construir", tmp_path).returncode == 2


def preparar_dos_afirmaciones(carpeta: Path, estado: str, texto: str, umbrales: dict) -> None:
    """a1 = auc.media contra el censo; a2 = n_lotes contra campo."""
    preparar(carpeta)
    explicacion = explicacion_con_veredicto(carpeta, estado, texto)
    segunda = {**explicacion["afirmaciones"][0], "texto": "Se usaron {valor} lotes.", "clave": "n_lotes"}
    explicacion["afirmaciones"].append({**segunda, "referencia": "campo"})
    (carpeta / "explicacion.json").write_text(json.dumps(explicacion), encoding="utf-8")
    config = {"hipotesis": {"texto": "El AUC medio supera el umbral", "umbrales": umbrales}}
    (carpeta / "config.json").write_text(json.dumps(config), encoding="utf-8")


def test_umbral_sobre_el_censo_no_apoya_aunque_no_se_cite(tmp_path):
    for estado in ("se_apoya", "se_refuta"):
        preparar_dos_afirmaciones(tmp_path, estado, "Con {a2} lotes.", {"auc.media": 0.8})
        salida = correr("construir", tmp_path)
        assert salida.returncode == 1
        assert "umbral auc.media" in salida.stderr
        assert "etiqueta_historica" in salida.stderr
    preparar_dos_afirmaciones(tmp_path, "intermedio", "Con {a2} lotes.", {"auc.media": 0.8})
    assert correr("construir", tmp_path).returncode == 0
    preparar_dos_afirmaciones(tmp_path, "se_apoya", "Con {a2} lotes.", {"n_lotes": 10})
    salida = correr("construir", tmp_path)
    assert salida.returncode == 0, salida.stderr


def test_umbral_con_clave_que_no_existe(tmp_path):
    preparar_dos_afirmaciones(tmp_path, "intermedio", "Con {a2} lotes.", {"auc.maxima": 0.8})
    salida = correr("construir", tmp_path)
    assert salida.returncode == 1
    assert "auc.maxima" in salida.stderr
    assert "no está en resultado.json" in salida.stderr


def test_aviso_del_censo_en_cada_cifra_historica_del_md(tmp_path):
    preparar_dos_afirmaciones(tmp_path, "intermedio", "El AUC es {a1} con {a2} lotes.", {"auc.media": 0.8})
    assert correr("construir", tmp_path).returncode == 0
    explicacion = json.loads((tmp_path / "explicacion.json").read_text(encoding="utf-8"))
    lineas = (tmp_path / "explicacion.md").read_text(encoding="utf-8").splitlines()
    historicas = [a for a in explicacion["afirmaciones"] if a["referencia"] == "etiqueta_historica"]
    assert historicas
    for afirmacion in historicas:
        valor = RESULTADO
        for parte in afirmacion["clave"].split("."):
            valor = valor[parte]
        cifra = re.compile(rf"(?<![\d.]){re.escape(str(valor))}(?![\d])")
        con_cifra = [linea for linea in lineas if cifra.search(linea)]
        assert len(con_cifra) == 2, con_cifra
        assert all("no desempeño" in linea for linea in con_cifra), con_cifra


def test_huella_vacia_es_otro_resultado(tmp_path):
    preparar(tmp_path)
    explicacion = explicacion_con_veredicto(tmp_path)
    explicacion["resultado_sha256"] = ""
    (tmp_path / "explicacion.json").write_text(json.dumps(explicacion), encoding="utf-8")
    salida = correr("construir", tmp_path)
    assert salida.returncode == 1
    assert "otro resultado" in salida.stderr


def test_anclar_no_ancla_una_explicacion_invalida(tmp_path):
    preparar(tmp_path)
    explicacion = explicacion_con_veredicto(tmp_path)
    explicacion["afirmaciones"][0]["clave"] = "auc.maxima"
    explicacion["resultado_sha256"] = "viejo"
    (tmp_path / "explicacion.json").write_text(json.dumps(explicacion), encoding="utf-8")
    salida = correr("anclar", tmp_path)
    assert salida.returncode == 1
    assert "no está en resultado.json" in salida.stderr
    assert json.loads((tmp_path / "explicacion.json").read_text(encoding="utf-8"))["resultado_sha256"] == "viejo"


def test_umbral_sin_afirmacion_no_apoya_ni_refuta(tmp_path):
    for estado in ("se_apoya", "se_refuta"):
        preparar_dos_afirmaciones(tmp_path, estado, "Con {a2} lotes.", {"auc.por_lote.3-2008": 0.8})
        salida = correr("construir", tmp_path)
        assert salida.returncode == 1
        assert "el umbral auc.por_lote.3-2008 no lo explica ninguna afirmación" in salida.stderr
    preparar_dos_afirmaciones(tmp_path, "intermedio", "Con {a2} lotes.", {"auc.por_lote.3-2008": 0.8})
    salida = correr("construir", tmp_path)
    assert salida.returncode == 0, salida.stderr
