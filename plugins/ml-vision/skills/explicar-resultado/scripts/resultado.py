"""Plantilla y validación de la explicación de un resultado.

Uso:
    resultado.py plantilla <carpeta del run>
    resultado.py construir <carpeta del run>
    resultado.py anclar <carpeta del run>

Lee `resultado.json` (lo escribe el experimento), `explicacion.json` (lo completa quien explica) y, si el
veredicto apoya o refuta algo, la hipótesis de `config.json`. Las cifras de `explicacion.md` salen siempre
de `resultado.json`, y `resultado_sha256` ata la explicación a los bytes exactos de ese archivo.
`anclar` vuelve a escribir esa huella, solo si la explicación pasa las mismas revisiones que `construir`.

Códigos de salida: 0 bien, 1 falta o sobra algo, 2 hay un error (`bug`) abierto.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

REFERENCIAS = ("campo", "experto", "etiqueta_historica", "ninguna")
TIPOS = ("bug", "riesgo", "duda")
ESTADOS = ("abierta", "resuelta", "descartada")
AVISO_HISTORICA = "medida contra una etiqueta histórica: es coincidencia con un registro, no desempeño"
VEREDICTOS = ("se_apoya", "se_refuta", "intermedio", "no_aplica")
NUMERO = re.compile(r"\d")
CITA = re.compile(r"\{a(\d+)\}")


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


def huella(contenido: bytes) -> str:
    """SHA-256 de los bytes exactos de resultado.json."""
    return hashlib.sha256(contenido).hexdigest()


def plantilla(disponibles: dict[str, float], sha: str) -> dict:
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
        "veredicto": {"estado": "", "texto": ""},
        "siguiente": "",
        "resultado_sha256": sha,
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


def revisar_veredicto(explicacion: dict, disponibles: dict[str, float], hipotesis: object) -> list[str]:
    """Lista lo que le falta al veredicto sobre la hipótesis prerregistrada."""
    veredicto = explicacion["veredicto"]
    if not isinstance(veredicto, dict):
        return ["veredicto debe ser un objeto {estado, texto}"]
    faltas = []
    estado = veredicto.get("estado")
    texto = str(veredicto.get("texto") or "")
    if estado not in VEREDICTOS:
        faltas.append(f"veredicto.estado debe ser uno de {', '.join(VEREDICTOS)}")
    if not texto.strip():
        faltas.append("falta veredicto.texto (una frase)")
    if NUMERO.search(CITA.sub("", texto)):
        faltas.append("veredicto: el texto trae una cifra escrita a mano; cita la afirmación con {a1}, {a2}...")
    afirmaciones = explicacion.get("afirmaciones") or []
    citadas = [int(numero) for numero in CITA.findall(texto)]
    faltas += [f"veredicto: cita la afirmación {n}, que no existe" for n in citadas if not 1 <= n <= len(afirmaciones)]
    abiertos = [a for a in explicacion.get("alertas") or [] if a.get("tipo") == "bug" and a.get("estado") == "abierta"]
    if abiertos and estado != "no_aplica":
        faltas.append("veredicto: con un error (bug) abierto el estado debe ser no_aplica")
    if estado not in ("se_apoya", "se_refuta", "intermedio"):
        return faltas
    if not citadas:
        faltas.append("veredicto: el texto debe citar la cifra de al menos una afirmación con {a1}, {a2}...")
    umbrales = hipotesis.get("umbrales") if isinstance(hipotesis, dict) else None
    if not isinstance(hipotesis, dict) or not hipotesis.get("texto") or not isinstance(umbrales, dict) or not umbrales:
        faltas.append(
            f"veredicto {estado}: config.json debe traer la hipótesis fijada antes de correr, "
            '{"hipotesis": {"texto": "...", "umbrales": {...}}}; si no la hay, usa no_aplica'
        )
        umbrales = {}
    faltas += [
        f"hipótesis: el umbral {clave} no está en resultado.json" for clave in umbrales if clave not in disponibles
    ]
    if estado not in ("se_apoya", "se_refuta"):
        return faltas
    historicas = [
        n
        for n in citadas
        if 1 <= n <= len(afirmaciones) and afirmaciones[n - 1].get("referencia") == "etiqueta_historica"
    ]
    if historicas:
        faltas.append(
            f"veredicto {estado}: se apoya en la afirmación {historicas[0]}, medida contra etiqueta_historica; "
            "un registro no es verdad de campo: usa intermedio o no_aplica"
        )
    censo = {a.get("clave") for a in afirmaciones if a.get("referencia") == "etiqueta_historica"}
    faltas += [
        f"veredicto {estado}: el umbral {clave} es una cifra medida contra etiqueta_historica; "
        "un registro no es verdad de campo: usa intermedio o no_aplica"
        for clave in umbrales
        if clave in censo
    ]
    explicadas = {a.get("clave") for a in afirmaciones}
    faltas += [
        f"veredicto {estado}: el umbral {clave} no lo explica ninguna afirmación: no se sabe contra qué se midió"
        for clave in umbrales
        if clave not in explicadas
    ]
    return faltas


def revisar(explicacion: dict, disponibles: dict[str, float], sha: str, hipotesis: object = None) -> list[str]:
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
    if "veredicto" in explicacion:
        faltas += revisar_veredicto(explicacion, disponibles, hipotesis)
    if "resultado_sha256" in explicacion and explicacion["resultado_sha256"] != sha:
        faltas.append("la explicación es de otro resultado: vuelve a explicar (y luego `resultado.py anclar`)")
    return faltas


def avisos(explicacion: dict) -> list[str]:
    """Campos que una explicación anterior a la versión con veredicto no trae; no bloquean."""
    return [
        f"AVISO: explicacion.json no trae {campo}; {motivo}"
        for campo, motivo in (
            ("veredicto", "agrega el veredicto sobre la hipótesis (no_aplica si no la hay)"),
            ("resultado_sha256", "no se puede comprobar que explica este resultado; corre `resultado.py anclar`"),
        )
        if campo not in explicacion
    ]


def cifra(afirmacion: dict, disponibles: dict[str, float]) -> str:
    """La cifra de una afirmación tal como va en explicacion.md, con el aviso si se midió contra el censo."""
    valor = formato(disponibles[afirmacion["clave"]])
    return f"{valor} ({AVISO_HISTORICA})" if afirmacion["referencia"] == "etiqueta_historica" else valor


def markdown(explicacion: dict, disponibles: dict[str, float]) -> str:
    """Arma la explicación con las cifras de resultado.json."""
    afirmaciones = explicacion["afirmaciones"]
    lineas = [f"# {explicacion['titulo']}", "", f"**Pregunta:** {explicacion['pregunta']}", ""]
    lineas += ["## Cómo se hizo", "", explicacion["como_se_hizo"], "", "## Qué se puede afirmar", ""]
    for afirmacion in explicacion["afirmaciones"]:
        texto = afirmacion["texto"].replace("{valor}", cifra(afirmacion, disponibles))
        lineas.append(f"- {texto}")
        lineas.append(f"  - Cifra: `{afirmacion['clave']}`. Referencia: {afirmacion['referencia']}.")
        lineas.append(f"  - Alcance: {afirmacion['alcance']['descripcion']}.")
    veredicto = explicacion.get("veredicto")
    if veredicto:
        texto = CITA.sub(lambda cita: cifra(afirmaciones[int(cita.group(1)) - 1], disponibles), veredicto["texto"])
        lineas += ["", "## Veredicto", "", f"**{veredicto['estado']}**: {texto}"]
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


def leer(ruta: Path, contenido: bytes | None = None) -> dict:
    """Lee un JSON que debe ser un objeto (de `contenido` si ya se leyeron los bytes)."""
    datos = json.loads((ruta.read_bytes() if contenido is None else contenido).decode("utf-8"))
    if not isinstance(datos, dict):
        raise ValueError(f"{ruta.name} debe ser un objeto JSON")
    return datos


def hipotesis_de(carpeta: Path) -> object:
    """La hipótesis prerregistrada de config.json, o None si no hay archivo o no se puede leer."""
    try:
        return leer(carpeta / "config.json").get("hipotesis")
    except (OSError, ValueError):
        return None


def main(argumentos: list[str]) -> int:
    """Punto de entrada."""
    if len(argumentos) != 2 or argumentos[0] not in ("plantilla", "construir", "anclar"):
        print(__doc__, file=sys.stderr)
        return 1
    carpeta = Path(argumentos[1])
    try:
        contenido = (carpeta / "resultado.json").read_bytes()
        disponibles = claves(leer(carpeta / "resultado.json", contenido))
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
        texto = json.dumps(plantilla(disponibles, huella(contenido)), ensure_ascii=False, indent=2)
        destino.write_text(texto + "\n", encoding="utf-8")
        print(f"OK: {destino}")
        return 0
    try:
        explicacion = leer(destino)
    except (OSError, ValueError) as error:
        print(f"No se pudo leer explicacion.json: {error}", file=sys.stderr)
        return 1
    if argumentos[0] == "anclar":
        explicacion["resultado_sha256"] = huella(contenido)
        faltas = revisar(explicacion, disponibles, huella(contenido), hipotesis_de(carpeta))
        if faltas:
            print("No se ancla; falta:\n" + "\n".join(f"- {falta}" for falta in faltas), file=sys.stderr)
            return 1
        destino.write_text(json.dumps(explicacion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"OK: {destino} anclada a resultado.json")
        return 0
    for aviso in avisos(explicacion):
        print(aviso, file=sys.stderr)
    faltas = revisar(explicacion, disponibles, huella(contenido), hipotesis_de(carpeta))
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
