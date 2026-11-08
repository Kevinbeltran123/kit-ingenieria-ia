"""Prepara la explicación de un cambio: saca de git las líneas reales y las agrupa en pasos.

Uso, desde la raíz del repo:
    python3 recolectar.py                 # commits de la rama actual frente a la rama base
    python3 recolectar.py --base develop  # otra rama o commit como base
    python3 recolectar.py --sin-commit    # incluye lo que todavía no tiene commit
    python3 recolectar.py --commit abc123 # un solo commit, frente al anterior

Escribe en .explicaciones/<rama>/ (con --commit, en .explicaciones/commits/<commit>/):
    datos.json   lo que sale de git: archivos, líneas, números y pasos. No se edita.
    textos.json  lo que Claude completa: título, resumen y, en cada paso, la explicación del
                 bloque o método y una nota por cada línea cambiada.
Así el código y los números de línea nunca los escribe Claude: solo las explicaciones.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

CARPETA = ".explicaciones"
NO_EXPLICAR = {  # los cambia una herramienta, no una persona
    "uv.lock", "poetry.lock", "Pipfile.lock", "pdm.lock", "package-lock.json", "pnpm-lock.yaml",
    "yarn.lock", "bun.lockb", "Cargo.lock",
}
MAX_LINEAS_PASO = 40
MAX_HUECO = 3  # dos bloques del mismo método separados por hasta 3 líneas iguales forman un paso
CABECERA_HUNK = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def git(raiz: Path, *args: str, permitir_error: bool = False) -> str:
    r = subprocess.run(["git", *args], cwd=raiz, capture_output=True, text=True)
    if r.returncode != 0 and not permitir_error:
        sys.exit(f"git {' '.join(args)} falló: {r.stderr.strip()}")
    return r.stdout if r.returncode == 0 else ""


def rama_base(raiz: Path) -> str:
    origen = git(raiz, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD", permitir_error=True).strip()
    if origen:
        return origen
    for candidata in ("origin/main", "origin/master", "main", "master"):
        if git(raiz, "rev-parse", "--verify", "--quiet", candidata, permitir_error=True).strip():
            return candidata
    sys.exit("No encontré la rama base. Pásala con --base <rama o commit>.")


def carpeta_de_rama(rama: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", rama) or "sin-rama"


def excluir_de_git(raiz: Path) -> None:
    """Agrega .explicaciones/ a .git/info/exclude: queda fuera de git sin tocar el .gitignore del equipo."""
    comun = Path(git(raiz, "rev-parse", "--git-common-dir").strip())
    exclude = (comun if comun.is_absolute() else raiz / comun) / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    actual = exclude.read_text() if exclude.exists() else ""
    if f"{CARPETA}/" not in actual.split():
        exclude.write_text(actual + ("" if actual.endswith("\n") or not actual else "\n") + f"{CARPETA}/\n")


def lineas_del_diff(texto: str) -> list[dict] | None:
    """Convierte el diff de un archivo (con contexto completo) en filas. None si es binario."""
    salida, en_hunk, viejo, nuevo = [], False, 0, 0
    for linea in texto.splitlines():
        if not en_hunk and linea.startswith("Binary files "):
            return None
        m = CABECERA_HUNK.match(linea)
        if m:
            en_hunk, viejo, nuevo = True, int(m.group(1)), int(m.group(2))
            continue
        if not en_hunk or linea.startswith("\\"):
            continue
        tipo, contenido = linea[:1], linea[1:]
        if tipo == " ":
            salida.append({"t": " ", "o": viejo, "n": nuevo, "c": contenido})
            viejo += 1
            nuevo += 1
        elif tipo == "-":
            salida.append({"t": "-", "o": viejo, "c": contenido})
            viejo += 1
        elif tipo == "+":
            salida.append({"t": "+", "n": nuevo, "c": contenido})
            nuevo += 1
    return salida


def definiciones(fuente: str) -> list[tuple[int, int, str]]:
    """(inicio, fin, nombre) de cada def y class de un archivo Python, para ubicar cada paso."""
    try:
        arbol = ast.parse(fuente)
    except (SyntaxError, ValueError):
        return []
    salida: list[tuple[int, int, str]] = []

    def visitar(nodo: ast.AST, prefijo: str) -> None:
        for hijo in ast.iter_child_nodes(nodo):
            if isinstance(hijo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                es_clase = isinstance(hijo, ast.ClassDef)
                nombre = f"{prefijo}{hijo.name}"
                inicio = min([hijo.lineno] + [d.lineno for d in hijo.decorator_list])
                salida.append((inicio, hijo.end_lineno or hijo.lineno,
                               f"class {nombre}" if es_clase else f"def {nombre}()"))
                visitar(hijo, f"{nombre}.")
            else:
                visitar(hijo, prefijo)

    visitar(arbol, "")
    return salida


def contexto(defs: list[tuple[int, int, str]], numero: int | None) -> str:
    if numero is None:
        return ""
    dentro = [d for d in defs if d[0] <= numero <= d[1]]
    return max(dentro)[2] if dentro else ""


def bloques(lineas: list[dict]) -> list[list[int]]:
    """Rangos [i0, i1] de filas cambiadas seguidas."""
    rangos, inicio = [], None
    for i, linea in enumerate(lineas):
        if linea["t"] in "+-":
            if inicio is None:
                inicio = i
        elif inicio is not None:
            rangos.append([inicio, i - 1])
            inicio = None
    if inicio is not None:
        rangos.append([inicio, len(lineas) - 1])
    return rangos


def primera_cambiada(lineas: list[dict], i0: int, i1: int) -> dict | None:
    """La primera línea agregada con texto; si el trozo solo borra, la primera borrada con texto."""
    for tipo in "+-":
        for i in range(i0, i1 + 1):
            if lineas[i]["t"] == tipo and lineas[i]["c"].strip():
                return lineas[i]
    return None


def pasos_de_archivo(lineas: list[dict], es_python: bool) -> list[dict]:
    nuevo = "\n".join(l["c"] for l in lineas if l["t"] in " +")
    viejo = "\n".join(l["c"] for l in lineas if l["t"] in " -")
    defs_nuevo = definiciones(nuevo) if es_python else []
    defs_viejo = definiciones(viejo) if es_python else []
    inicios = {d[0] for d in defs_nuevo}

    def ubicar(i0: int, i1: int) -> str:
        primera = primera_cambiada(lineas, i0, i1)
        if primera is None:
            return ""
        if primera["t"] == "+":
            return contexto(defs_nuevo, primera.get("n"))
        return contexto(defs_viejo, primera.get("o"))

    def en_blanco(i: int) -> bool:
        return lineas[i]["t"] == "+" and not lineas[i]["c"].strip()

    # 1. Partir los bloques donde empieza un def/class y, si un trozo sigue largo, cada MAX líneas.
    #    Lo que está justo antes del def nuevo va con él: líneas en blanco y líneas borradas
    #    (si cambió la firma, la versión vieja se explica junto a la nueva).
    piezas: list[list[int]] = []
    for i0, i1 in bloques(lineas):
        cortes = set()
        for i in range(i0 + 1, i1 + 1):
            if lineas[i]["t"] == "+" and lineas[i].get("n") in inicios:
                while i - 1 >= i0 and (en_blanco(i - 1) or lineas[i - 1]["t"] == "-"):
                    i -= 1
                cortes.add(i)
        cortes = sorted(cortes)
        inicio = i0
        for corte in [*cortes, i1 + 1]:
            if corte > inicio:
                for a in range(inicio, corte, MAX_LINEAS_PASO):
                    piezas.append([a, min(a + MAX_LINEAS_PASO, corte) - 1])
            inicio = corte
    # 2. Juntar piezas cercanas del mismo método, sin pasar de MAX líneas. Un trozo que solo tiene
    #    líneas en blanco no es un paso: se pega al anterior si está al lado, o se deja sin explicar.
    pasos: list[dict] = []
    for i0, i1 in piezas:
        if all(not lineas[i]["c"].strip() for i in range(i0, i1 + 1) if lineas[i]["t"] in "+-"):
            if pasos and pasos[-1]["i1"] == i0 - 1:
                pasos[-1]["i1"] = i1
            continue
        ctx = ubicar(i0, i1)
        if pasos:
            previo = pasos[-1]
            hueco = i0 - previo["i1"] - 1
            if hueco <= MAX_HUECO and previo["contexto"] == ctx and i1 - previo["i0"] < MAX_LINEAS_PASO \
                    and not any(lineas[i].get("n") in inicios for i in range(previo["i1"] + 1, i0 + 1)):
                previo["i1"] = i1
                continue
        pasos.append({"i0": i0, "i1": i1, "contexto": ctx})
    return pasos


def numeros(lineas: list[dict], paso: dict, tipo: str) -> list[int]:
    clave = "n" if tipo == "+" else "o"
    return [lineas[i][clave] for i in range(paso["i0"], paso["i1"] + 1)
            if lineas[i]["t"] == tipo and lineas[i]["c"].strip()]


def codigo_para_leer(lineas: list[dict], paso: dict) -> list[str]:
    filas = []
    for i in range(paso["i0"], paso["i1"] + 1):
        l = lineas[i]
        numero = l["o"] if l["t"] == "-" else l["n"]
        filas.append(f"{l['t']} {numero:>5} | {l['c']}")
    return filas


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Prepara la explicación de un cambio a partir de git.")
    modo = p.add_mutually_exclusive_group()
    modo.add_argument("--base", help="rama o commit de comparación (por defecto, la rama principal)")
    modo.add_argument("--sin-commit", action="store_true", help="incluir cambios que aún no tienen commit")
    modo.add_argument("--commit", metavar="REF", help="explicar solo ese commit, frente al anterior")
    args = p.parse_args(argv)

    raiz = Path(git(Path.cwd(), "rev-parse", "--show-toplevel").strip())
    rama = git(raiz, "rev-parse", "--abbrev-ref", "HEAD").strip()
    commit = None
    if args.commit:
        hasta_sha = git(raiz, "rev-parse", "--verify", f"{args.commit}^{{commit}}").strip()
        padre = git(raiz, "rev-parse", "--verify", "--quiet", f"{hasta_sha}^", permitir_error=True).strip()
        base_sha = padre or git(raiz, "hash-object", "-t", "tree", "/dev/null").strip()  # primer commit: árbol vacío
        base_ref = f"{hasta_sha[:7]}^" if padre else "(sin commit anterior)"
        commit = {"sha": hasta_sha, "asunto": git(raiz, "log", "-1", "--format=%s", hasta_sha).strip()}
    else:
        base_ref = args.base or rama_base(raiz)
        base_sha = git(raiz, "merge-base", base_ref, "HEAD").strip()
        hasta_sha = None if args.sin_commit else git(raiz, "rev-parse", "HEAD").strip()
    rango = [base_sha] if args.sin_commit else [base_sha, hasta_sha]

    entradas = []
    for linea in git(raiz, "diff", "--name-status", "-M", *rango).splitlines():
        partes = linea.split("\t")
        estado = partes[0][:1]
        anterior, ruta = (partes[1], partes[2]) if estado in "RC" else (partes[1], partes[1])
        entradas.append((estado, ruta, anterior))
    if args.sin_commit:
        for ruta in git(raiz, "ls-files", "--others", "--exclude-standard").splitlines():
            entradas.append(("A", ruta, None))

    archivos, pasos, omitidos = [], [], []
    for estado, ruta, anterior in entradas:
        if Path(ruta).name in NO_EXPLICAR:
            omitidos.append({"ruta": ruta, "motivo": "lo cambia el gestor de paquetes, no una persona"})
            continue
        if anterior is None:
            texto = subprocess.run(["git", "diff", "--no-index", "-U1000000", "--", "/dev/null", ruta],
                                   cwd=raiz, capture_output=True, text=True).stdout
        else:
            rutas = [anterior, ruta] if anterior != ruta else [ruta]
            texto = git(raiz, "diff", "-M", "-U1000000", *rango, "--", *rutas)
        lineas = lineas_del_diff(texto)
        if lineas is None:
            omitidos.append({"ruta": ruta, "motivo": "archivo binario"})
            continue
        if not any(l["t"] in "+-" for l in lineas):
            continue
        indice = len(archivos)
        archivos.append({
            "ruta": ruta, "anterior": anterior if anterior != ruta else None, "estado": estado,
            "mas": sum(l["t"] == "+" for l in lineas), "menos": sum(l["t"] == "-" for l in lineas),
            "lineas": lineas,
        })
        for paso in pasos_de_archivo(lineas, ruta.endswith((".py", ".pyi"))):
            pasos.append({"id": len(pasos) + 1, "archivo": indice, **paso})

    if not pasos:
        sys.exit(f"No hay cambios para explicar entre {base_ref} y {'el árbol de trabajo' if args.sin_commit else 'HEAD'}.")

    carpeta = raiz / CARPETA / ("commits/" + hasta_sha[:7] if commit else carpeta_de_rama(rama))
    carpeta.mkdir(parents=True, exist_ok=True)
    excluir_de_git(raiz)
    datos = {
        "version": 1, "repo": raiz.name, "rama": rama, "commit": commit,
        "base": {"ref": base_ref, "sha": base_sha}, "hasta": hasta_sha, "sin_commit": args.sin_commit,
        "recolectado": datetime.now().isoformat(timespec="seconds"),
        "archivos": archivos, "pasos": pasos, "omitidos": omitidos,
    }
    (carpeta / "datos.json").write_text(json.dumps(datos, ensure_ascii=False))

    textos = {
        "_instrucciones": ("Completa cada campo vacío (ver la skill explicar-cambios). En cada paso: "
                           "'explicacion' del bloque o método, una nota en 'notas' por cada número de "
                           "'lineas_nuevas' y en 'notas_borradas' por cada número de 'lineas_borradas' "
                           "(se aceptan rangos como \"61-64\"). 'codigo' es solo para leer."),
        "titulo": "",
        "resumen": {"problema": "", "solucion": "", "como_se_probo": "", "decisiones": "", "pendiente": ""},
        "pasos": [],
    }
    if commit:
        textos["_commit"] = f"{commit['sha'][:7]} {commit['asunto']}"
    for paso in pasos:
        a = archivos[paso["archivo"]]
        es_python = a["ruta"].endswith((".py", ".pyi"))
        textos["pasos"].append({
            "id": paso["id"], "archivo": a["ruta"], "contexto": paso["contexto"] or ("(nivel de módulo)" if es_python else ""),
            "codigo": codigo_para_leer(a["lineas"], paso),
            "lineas_nuevas": numeros(a["lineas"], paso, "+"),
            "lineas_borradas": numeros(a["lineas"], paso, "-"),
            "titulo": "", "explicacion": "", "notas": {}, "notas_borradas": {}, "alerta": None,
        })
    destino = carpeta / "textos.json"
    if destino.exists():
        destino.replace(carpeta / "textos.anterior.json")
    destino.write_text(json.dumps(textos, ensure_ascii=False, indent=1))

    total = sum(len(p["lineas_nuevas"]) + len(p["lineas_borradas"]) for p in textos["pasos"])
    print(f"{len(archivos)} archivos, {len(pasos)} pasos, {total} líneas para explicar"
          + (f"; sin explicar: {', '.join(o['ruta'] for o in omitidos)}" if omitidos else ""))
    siguiente = f"construir.py {carpeta.relative_to(raiz)}" if commit else "construir.py"
    print(f"Completa {destino.relative_to(raiz)} y después corre {siguiente}.")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("GIT_OPTIONAL_LOCKS", "0")
    sys.exit(main())
