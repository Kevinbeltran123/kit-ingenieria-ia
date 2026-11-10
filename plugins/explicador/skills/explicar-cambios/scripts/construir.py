"""Valida las explicaciones y arma el HTML del cambio: el código a un lado y una terminal que lo explica.

Uso, desde la raíz del repo:
    python3 construir.py            # usa .explicaciones/<rama actual>/
    python3 construir.py --abrir    # además lo abre en el navegador

Si falta la explicación de un paso o la nota de una línea, dice cuál y sale con 1: no se arma
un informe a medias. El HTML no carga nada de internet (la fuente va incrustada): el código no
sale de la máquina.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import html
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
CARPETA = ".explicaciones"
RESUMEN_OBLIGATORIO = ("problema", "solucion", "como_se_probo")
TIPOS_ALERTA = ("bug", "riesgo", "duda")
ESTADOS_ALERTA = ("abierta", "resuelta", "descartada")
RANGO = re.compile(r"^\s*(\d+)\s*(?:-\s*(\d+))?\s*$")
FUENTES = (
    ("400", "normal", "IBMPlexMono-400.woff2"),
    ("500", "normal", "IBMPlexMono-500.woff2"),
    ("600", "normal", "IBMPlexMono-600.woff2"),
    ("400", "italic", "IBMPlexMono-400-italic.woff2"),
)
MARCADORES = re.compile(r"/\*__FUENTES__\*/|__TITULO__|__DATOS__")


def git(raiz: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=raiz, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"git {' '.join(args)} falló: {r.stderr.strip()}")
    return r.stdout.strip()


def carpeta_de_rama(rama: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", rama) or "sin-rama"


def leer_rango(clave: str) -> tuple[int, int] | None:
    m = RANGO.match(clave)
    if not m:
        return None
    a, b = int(m.group(1)), int(m.group(2) or m.group(1))
    return (a, b) if a <= b else None


def compactar(numeros: list[int]) -> str:
    """[61, 62, 63, 70] -> '61-63, 70'."""
    partes, inicio = [], None
    for i, n in enumerate(numeros):
        if inicio is None:
            inicio = n
        if i + 1 == len(numeros) or numeros[i + 1] != n + 1:
            partes.append(str(inicio) if inicio == n else f"{inicio}-{n}")
            inicio = None
    return ", ".join(partes)


def validar(datos: dict, textos: dict) -> list[str]:
    errores = []
    if not str(textos.get("titulo", "")).strip():
        errores.append("falta el título del cambio ('titulo')")
    resumen = textos.get("resumen") or {}
    errores += [f"falta 'resumen.{c}'" for c in RESUMEN_OBLIGATORIO if not str(resumen.get(c, "")).strip()]
    por_id = {p.get("id"): p for p in textos.get("pasos", [])}
    for paso in datos["pasos"]:
        archivo = datos["archivos"][paso["archivo"]]
        donde = f"paso {paso['id']} ({archivo['ruta']})"
        t = por_id.get(paso["id"])
        if t is None:
            errores.append(f"{donde}: no está en textos.json")
            continue
        errores += [f"{donde}: falta '{c}'" for c in ("titulo", "explicacion") if not str(t.get(c, "")).strip()]
        filas = archivo["lineas"][paso["i0"] : paso["i1"] + 1]
        for campo, tipo, clave, nombre in (
            ("notas", "+", "n", "la línea"),
            ("notas_borradas", "-", "o", "la línea borrada"),
        ):
            validos = {f[clave] for f in filas if clave in f and (f["t"] == tipo or (tipo == "+" and f["t"] == " "))}
            requeridas = [f[clave] for f in filas if f["t"] == tipo and f["c"].strip()]
            cubiertas: set[int] = set()
            for llave, texto in (t.get(campo) or {}).items():
                rango = leer_rango(str(llave))
                if rango is None:
                    errores.append(
                        f"{donde}: '{llave}' no es un número ni un rango (usa \"61\" o \"61-64\") en '{campo}'"
                    )
                    continue
                numeros = set(range(rango[0], rango[1] + 1))
                if not str(texto).strip():
                    errores.append(f"{donde}: la nota '{llave}' de '{campo}' está vacía")
                if numeros - validos:
                    errores.append(
                        f"{donde}: la nota '{llave}' de '{campo}' apunta fuera del paso "
                        f"({compactar(sorted(numeros - validos))})"
                    )
                cubiertas |= numeros
            faltan = [n for n in requeridas if n not in cubiertas]
            if faltan:
                errores.append(f"{donde}: falta nota para {nombre} {compactar(faltan)} en '{campo}'")
        alerta = t.get("alerta")
        if alerta is not None:
            if (
                not isinstance(alerta, dict)
                or alerta.get("tipo") not in TIPOS_ALERTA
                or alerta.get("estado") not in ESTADOS_ALERTA
                or not str(alerta.get("texto", "")).strip()
            ):
                errores.append(
                    f"{donde}: 'alerta' debe ser null o tener tipo ({'/'.join(TIPOS_ALERTA)}), "
                    f"estado ({'/'.join(ESTADOS_ALERTA)}) y texto"
                )
            elif alerta["estado"] == "descartada" and not str(alerta.get("motivo", "")).strip():
                errores.append(f"{donde}: una alerta descartada necesita 'motivo'")
    return errores


def modelo(datos: dict, textos: dict) -> dict:
    """Lo que necesita la plantilla: las líneas de git y las notas ya convertidas a filas."""
    por_id = {p["id"]: p for p in textos["pasos"]}
    pasos = []
    for paso in datos["pasos"]:
        t = por_id[paso["id"]]
        lineas = datos["archivos"][paso["archivo"]]["lineas"]
        fila_de: dict[tuple[str, int], int] = {}
        for i in range(paso["i0"], paso["i1"] + 1):
            fila = lineas[i]
            if fila["t"] == "-":
                fila_de[("-", fila["o"])] = i
            else:
                fila_de[("+", fila["n"])] = i
        notas = []
        for campo, tipo in (("notas", "+"), ("notas_borradas", "-")):
            for llave, texto in (t.get(campo) or {}).items():
                a, b = leer_rango(str(llave))
                filas = [fila_de[(tipo, x)] for x in range(a, b + 1) if (tipo, x) in fila_de]
                etiqueta = str(a) if a == b else f"{a}–{b}"
                notas.append(
                    {"filas": filas, "etiqueta": ("−" if tipo == "-" else "") + etiqueta, "texto": str(texto).strip()}
                )
        notas.sort(key=lambda nota: min(nota["filas"]) if nota["filas"] else 0)
        nuevas = [lineas[i]["n"] for i in range(paso["i0"], paso["i1"] + 1) if lineas[i]["t"] != "-"]
        viejas = [lineas[i]["o"] for i in range(paso["i0"], paso["i1"] + 1) if lineas[i]["t"] == "-"]
        pasos.append(
            {
                "archivo": paso["archivo"],
                "i0": paso["i0"],
                "i1": paso["i1"],
                "contexto": paso["contexto"],
                "desde": nuevas[0] if nuevas else None,
                "hasta": nuevas[-1] if nuevas else None,
                "borradas": [viejas[0], viejas[-1]] if viejas and not nuevas else None,
                "titulo": str(t["titulo"]).strip(),
                "explicacion": str(t["explicacion"]).strip(),
                "notas": notas,
                "alerta": t.get("alerta"),
            }
        )
    resumen = {c: str(v).strip() for c, v in (textos.get("resumen") or {}).items() if str(v).strip()}
    commit = datos.get("commit")
    return {
        "repo": datos["repo"],
        "rama": f"commit {commit['sha'][:7]}" if commit else datos["rama"],
        "base": datos["base"],
        "hasta": datos["hasta"],
        "generado": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "titulo": str(textos["titulo"]).strip(),
        "resumen": resumen,
        "omitidos": datos["omitidos"],
        "pasos": pasos,
        "archivos": [
            {c: a[c] for c in ("ruta", "anterior", "estado", "mas", "menos", "lineas")} for a in datos["archivos"]
        ],
    }


def fuentes_css() -> str:
    reglas = []
    for peso, estilo, archivo in FUENTES:
        b64 = base64.b64encode((AQUI / "fuentes" / archivo).read_bytes()).decode()
        reglas.append(
            f'@font-face{{font-family:"IBM Plex Mono";font-style:{estilo};font-weight:{peso};'
            f'font-display:swap;src:url(data:font/woff2;base64,{b64}) format("woff2")}}'
        )
    return "\n".join(reglas)


def armar_html(m: dict) -> str:
    valores = {
        "/*__FUENTES__*/": fuentes_css(),
        "__TITULO__": html.escape(f"{m['titulo']} · {m['repo']}"),
        "__DATOS__": json.dumps(m, ensure_ascii=False).replace("</", "<\\/"),
    }
    # Un solo pase: lo que se inserta no se vuelve a revisar (el código explicado puede contener los marcadores).
    return MARCADORES.sub(lambda c: valores[c.group(0)], (AQUI / "plantilla.html").read_text())


def armar_indice(raiz: Path) -> Path:
    entradas = []
    for ultimo in (raiz / CARPETA).glob("**/ultimo.json"):
        try:
            entradas.append(json.loads(ultimo.read_text()))
        except ValueError:
            continue
    entradas.sort(key=lambda e: e.get("generado", ""), reverse=True)
    filas = []
    for e in entradas:
        abiertas = sum(1 for a in e.get("alertas", []) if a.get("estado") == "abierta")
        aviso = (
            f" · <b>{abiertas} alerta{'s' if abiertas != 1 else ''} abierta{'s' if abiertas != 1 else ''}</b>"
            if abiertas
            else ""
        )
        filas.append(
            f'<li><a href="{html.escape(e["html"])}">{html.escape(e["titulo"])}</a>'
            f"<span>{html.escape(e['rama'])} · {html.escape(e['generado'])}{aviso}</span></li>"
        )
    pagina = (
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1"><title>Explicaciones · '
        f"{html.escape(raiz.name)}</title><style>{fuentes_css()}"
        ":root{--bg:#0f1114;--fg:#e1e5ea;--muted:#959eaa;--accent:#8fb3ff;--warn:#eabf66;--line:#2a3038;color-scheme:dark}"
        "@media (prefers-color-scheme:light){:root{--bg:#eceef1;--fg:#1a1f26;--muted:#535d69;--accent:#2c5bd0;"
        "--warn:#8a5800;--line:#d8dce2;color-scheme:light}}"
        'body{margin:0;background:var(--bg);color:var(--fg);font:13px/1.6 "IBM Plex Mono",ui-monospace,Menlo,monospace}'
        "main{max-width:900px;margin:0 auto;padding:32px max(16px,env(safe-area-inset-left,0px))}"
        "h1{font-size:24px;font-weight:600;margin:0 0 20px}ul{list-style:none;margin:0;padding:0}"
        "li{display:grid;gap:2px;padding:12px 0;border-top:1px solid var(--line)}a{color:var(--accent)}"
        "span{color:var(--muted)}b{color:var(--warn);font-weight:500}</style></head><body><main>"
        f"<h1>Explicaciones · {html.escape(raiz.name)}</h1><ul>{''.join(filas)}</ul></main></body></html>"
    )
    indice = raiz / CARPETA / "index.html"
    indice.write_text(pagina)
    return indice


def abrir(ruta: Path) -> None:
    comando = ["open"] if sys.platform == "darwin" else ["xdg-open"]
    with contextlib.suppress(OSError):
        subprocess.run([*comando, str(ruta)], check=False, capture_output=True)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Valida las explicaciones y arma el HTML del cambio.")
    p.add_argument(
        "carpeta", nargs="?", help="carpeta con datos.json y textos.json (por defecto, la de la rama actual)"
    )
    p.add_argument("--abrir", action="store_true", help="abrir el HTML en el navegador al terminar")
    args = p.parse_args(argv)

    raiz = Path(git(Path.cwd(), "rev-parse", "--show-toplevel"))
    carpeta = (
        Path(args.carpeta).resolve()
        if args.carpeta
        else raiz / CARPETA / carpeta_de_rama(git(raiz, "rev-parse", "--abbrev-ref", "HEAD"))
    )
    if not (carpeta / "datos.json").is_file():
        sys.exit(f"No hay {carpeta / 'datos.json'}: corre primero recolectar.py.")
    datos = json.loads((carpeta / "datos.json").read_text())
    try:
        textos = json.loads((carpeta / "textos.json").read_text())
    except ValueError as error:
        sys.exit(f"textos.json no es JSON válido: {error}")

    errores = []
    if datos.get("commit"):
        existe = subprocess.run(
            ["git", "cat-file", "-e", f"{datos['hasta']}^{{commit}}"], cwd=raiz, capture_output=True
        )
        if existe.returncode != 0:
            errores.append(f"el commit {datos['hasta'][:7]} ya no existe en el repo")
    elif not datos["sin_commit"]:
        head = git(raiz, "rev-parse", "HEAD")
        if head != datos["hasta"]:
            errores.append(
                f"desde que se recolectó hubo commits nuevos (HEAD era {datos['hasta'][:7]}, ahora es "
                f"{head[:7]}): corre recolectar.py otra vez; tus textos quedan en textos.anterior.json"
            )
    errores += validar(datos, textos)
    if errores:
        print("No se armó el informe. Falta esto:\n" + "\n".join(f"- {e}" for e in errores), file=sys.stderr)
        return 1

    m = modelo(datos, textos)
    sello = datetime.now().strftime("%Y%m%d-%H%M")
    destino = carpeta / f"{sello}-{(datos['hasta'] or 'sin-commit')[:7]}.html"
    destino.write_text(armar_html(m))
    alertas = []
    for k, paso in enumerate(m["pasos"], 1):
        if paso["alerta"]:
            ruta = m["archivos"][paso["archivo"]]["ruta"]
            lineas = f"{paso['desde']}-{paso['hasta']}" if paso["desde"] is not None else "líneas borradas"
            alertas.append({**paso["alerta"], "donde": f"{ruta}:{lineas} (paso {k})"})
    ultimo = {
        "rama": m["rama"],
        "titulo": m["titulo"],
        "hasta": datos["hasta"],
        "base": datos["base"],
        "generado": m["generado"],
        "html": str(destino.relative_to(raiz / CARPETA)),
        "alertas": alertas,
    }
    (carpeta / "ultimo.json").write_text(json.dumps(ultimo, ensure_ascii=False, indent=1))
    indice = armar_indice(raiz)

    notas = sum(len(paso["notas"]) for paso in m["pasos"])
    print(f"OK: {destino.relative_to(raiz)} ({len(m['pasos'])} pasos, {notas} notas)")
    print(f"Ábrelo: {destino.as_uri()}")
    print(f"Todas las explicaciones del repo: {indice.as_uri()}")
    errores_abiertos = [a for a in alertas if a["tipo"] == "bug" and a["estado"] == "abierta"]
    if errores_abiertos:
        print(
            f"Ojo: {len(errores_abiertos)} posible(s) error(es) abierto(s). El PR queda bloqueado hasta "
            "corregirlos o descartarlos con motivo."
        )
    if args.abrir:
        abrir(destino)
    return 0


if __name__ == "__main__":
    sys.exit(main())
