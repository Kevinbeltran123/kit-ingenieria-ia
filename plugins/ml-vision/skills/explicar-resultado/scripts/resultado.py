"""Plantilla y validación de la explicación de un resultado.

Uso:
    resultado.py plantilla <carpeta del run>
    resultado.py construir <carpeta del run>

Lee `resultado.json` (lo escribe el experimento) y `explicacion.json` (lo completa quien explica).
Las cifras de `explicacion.md` salen siempre de `resultado.json`.

Códigos de salida: 0 bien, 1 falta o sobra algo, 2 hay un error (`bug`) abierto.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REFERENCIAS = ("campo", "experto", "etiqueta_historica", "ninguna")
TIPOS = ("bug", "riesgo", "duda")
ESTADOS = ("abierta", "resuelta", "descartada")
AVISO_HISTORICA = "medida contra una etiqueta histórica: es coincidencia con un registro, no desempeño"
NUMERO = re.compile(r"\d")


def claves(datos: object, prefijo: str = "") -> dict[str, float]:
    """Aplana el JSON del resultado: {"auc": {"media": 0.8}} -> {"auc.media": 0.8}."""
    if isinstance(datos, bool):
        return {}
    if isinstance(datos, (int, float)):
        return {prefijo: datos}
    if isinstance(datos, dict):
        planas: dict[str, float] = {}
        for nombre, valor in datos.items():
            planas.update(claves(valor, f"{prefijo}.{nombre}" if prefijo else str(nombre)))
        return planas
    return {}


def formato(valor: float) -> str:
    """Escribe la cifra sin inventar decimales: enteros tal cual, el resto con hasta 4 significativos."""
    if isinstance(valor, int):
        return str(valor)
    return f"{valor:.4g}"


def plantilla(disponibles: dict[str, float]) -> dict:
    """Devuelve la explicación vacía, con las claves que se pueden citar."""
    return {
        "titulo": "",
        "pregunta": "",
        "como_se_hizo": "",
        "claves_disponibles": sorted(disponibles),
        "afirmaciones": [
            {
                "texto": "",
                "clave": "",
                "referencia": "",
                "alcance": {"unidades": None, "grupos": None, "descripcion": ""},
                "no_comprobado": [],
            }
        ],
        "alertas": [],
        "siguiente": "",
    }


def revisar_afirmacion(numero: int, afirmacion: dict, disponibles: dict[str, float]) -> list[str]:
    """Lista lo que le falta a una afirmación."""
    faltas = []
    donde = f"afirmación {numero}"
    texto = afirmacion.get("texto") or ""
    if "{valor}" not in texto:
        faltas.append(f"{donde}: el texto no tiene {{valor}}")
    if NUMERO.search(texto.replace("{valor}", "")):
        faltas.append(f"{donde}: el texto trae una cifra escrita a mano; usa {{valor}} y la clave")
    if afirmacion.get("clave") not in disponibles:
        faltas.append(f"{donde}: la clave {afirmacion.get('clave')!r} no está en resultado.json")
    if afirmacion.get("referencia") not in REFERENCIAS:
        faltas.append(f"{donde}: referencia debe ser una de {', '.join(REFERENCIAS)}")
    alcance = afirmacion.get("alcance") or {}
    faltas += [
        f"{donde}: alcance.{campo} debe ser un número entero"
        for campo in ("unidades", "grupos")
        if not isinstance(alcance.get(campo), int) or isinstance(alcance.get(campo), bool)
    ]
    if not alcance.get("descripcion"):
        faltas.append(f"{donde}: falta alcance.descripcion")
    if not [linea for linea in afirmacion.get("no_comprobado") or [] if str(linea).strip()]:
        faltas.append(f"{donde}: no_comprobado está vacío; siempre hay algo fuera")
    return faltas


def revisar_alerta(numero: int, alerta: dict) -> list[str]:
    """Lista lo que le falta a una alerta."""
    faltas = []
    donde = f"alerta {numero}"
    if alerta.get("tipo") not in TIPOS:
        faltas.append(f"{donde}: tipo debe ser uno de {', '.join(TIPOS)}")
    if alerta.get("estado") not in ESTADOS:
        faltas.append(f"{donde}: estado debe ser uno de {', '.join(ESTADOS)}")
    if not alerta.get("texto"):
        faltas.append(f"{donde}: falta el texto")
    if alerta.get("estado") == "descartada" and not alerta.get("motivo"):
        faltas.append(f"{donde}: una alerta descartada necesita motivo (quién lo decidió y por qué)")
    return faltas


def revisar(explicacion: dict, disponibles: dict[str, float]) -> list[str]:
    """Lista todo lo que falta en la explicación."""
    obligatorios = ("titulo", "pregunta", "como_se_hizo", "siguiente")
    faltas = [f"falta {campo}" for campo in obligatorios if not explicacion.get(campo)]
    afirmaciones = explicacion.get("afirmaciones") or []
    if not afirmaciones:
        faltas.append("no hay afirmaciones")
    for numero, afirmacion in enumerate(afirmaciones, 1):
        faltas += revisar_afirmacion(numero, afirmacion, disponibles)
    for numero, alerta in enumerate(explicacion.get("alertas") or [], 1):
        faltas += revisar_alerta(numero, alerta)
    return faltas


def markdown(explicacion: dict, disponibles: dict[str, float]) -> str:
    """Arma la explicación con las cifras de resultado.json."""
    lineas = [f"# {explicacion['titulo']}", "", f"**Pregunta:** {explicacion['pregunta']}", ""]
    lineas += ["## Cómo se hizo", "", explicacion["como_se_hizo"], "", "## Qué se puede afirmar", ""]
    for afirmacion in explicacion["afirmaciones"]:
        texto = afirmacion["texto"].replace("{valor}", formato(disponibles[afirmacion["clave"]]))
        lineas.append(f"- {texto}")
        lineas.append(f"  - Cifra: `{afirmacion['clave']}`. Referencia: {afirmacion['referencia']}.")
        lineas.append(f"  - Alcance: {afirmacion['alcance']['descripcion']}.")
        if afirmacion["referencia"] == "etiqueta_historica":
            lineas.append(f"  - Aviso: {AVISO_HISTORICA}.")
    lineas += ["", "## Lo que no se comprobó", ""]
    for afirmacion in explicacion["afirmaciones"]:
        lineas += [f"- {linea}" for linea in afirmacion["no_comprobado"] if str(linea).strip()]
    alertas = explicacion.get("alertas") or []
    lineas += ["", "## Alertas", ""]
    if not alertas:
        lineas.append("Ninguna.")
    for alerta in alertas:
        motivo = f" Motivo: {alerta['motivo']}" if alerta.get("motivo") else ""
        lineas.append(f"- **{alerta['tipo']}** ({alerta['estado']}): {alerta['texto']}{motivo}")
    lineas += ["", "## Siguiente", "", explicacion["siguiente"], ""]
    return "\n".join(lineas)


def leer(ruta: Path) -> dict:
    """Lee un JSON que debe ser un objeto."""
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos, dict):
        raise ValueError(f"{ruta.name} debe ser un objeto JSON")
    return datos


def main(argumentos: list[str]) -> int:
    """Punto de entrada."""
    if len(argumentos) != 2 or argumentos[0] not in ("plantilla", "construir"):
        print(__doc__, file=sys.stderr)
        return 1
    carpeta = Path(argumentos[1])
    try:
        disponibles = claves(leer(carpeta / "resultado.json"))
    except (OSError, ValueError) as error:
        print(f"No se pudo leer resultado.json: {error}", file=sys.stderr)
        return 1
    if not disponibles:
        print("resultado.json no tiene ninguna cifra", file=sys.stderr)
        return 1
    destino = carpeta / "explicacion.json"
    if argumentos[0] == "plantilla":
        if destino.exists():
            print(f"Ya existe {destino}; no se sobrescribe", file=sys.stderr)
            return 1
        destino.write_text(json.dumps(plantilla(disponibles), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"OK: {destino}")
        return 0
    try:
        explicacion = leer(destino)
    except (OSError, ValueError) as error:
        print(f"No se pudo leer explicacion.json: {error}", file=sys.stderr)
        return 1
    faltas = revisar(explicacion, disponibles)
    if faltas:
        print("Falta:\n" + "\n".join(f"- {falta}" for falta in faltas), file=sys.stderr)
        return 1
    salida = carpeta / "explicacion.md"
    salida.write_text(markdown(explicacion, disponibles), encoding="utf-8")
    abiertos = [a for a in explicacion.get("alertas") or [] if a["tipo"] == "bug" and a["estado"] == "abierta"]
    if abiertos:
        aviso = f"Escrito {salida}, pero hay {len(abiertos)} error(es) abierto(s): corrige antes de reportar"
        print(aviso, file=sys.stderr)
        return 2
    print(f"OK: {salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
