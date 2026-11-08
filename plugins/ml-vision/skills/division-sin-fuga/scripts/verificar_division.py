"""Verifica que una división train/val/test no tenga fugas.

Lee un manifiesto CSV (una fila por imagen) y falla con código 1 si:
- una misma imagen, palma, lote o finca aparece en más de un split;
- (con --imagenes) dos archivos idénticos (mismo SHA-256) quedan en splits distintos;
- (con --temporal) el split de prueba tiene fechas iguales o anteriores a las de otro split.

Código 2 = error de uso (columna inexistente, fecha ilegible, CSV vacío).

Ejemplo:
    python3 verificar_division.py splits/manifest.csv \
        --grupos palma_id,lote,finca --col-fecha fecha --temporal --imagenes data/raw
"""

import argparse
import csv
import hashlib
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

MAX_EJEMPLOS = 10


def leer_fecha(texto: str) -> date:
    texto = texto.strip()
    try:
        return datetime.fromisoformat(texto).date()
    except ValueError:
        return date.fromisoformat(texto)


def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def cruces(filas, columna, col_split):
    """Valores de `columna` que aparecen en más de un split: {valor: {splits}}."""
    splits_por_valor = defaultdict(set)
    vacios = 0
    for fila in filas:
        valor = (fila.get(columna) or "").strip()
        if not valor:
            vacios += 1
            continue
        splits_por_valor[valor].add(fila[col_split])
    return {v: s for v, s in splits_por_valor.items() if len(s) > 1}, vacios


def formatear(cruzados: dict) -> str:
    lineas = [f"    {v}: {', '.join(sorted(s))}" for v, s in sorted(cruzados.items())[:MAX_EJEMPLOS]]
    if len(cruzados) > MAX_EJEMPLOS:
        lineas.append(f"    ... y {len(cruzados) - MAX_EJEMPLOS} más")
    return "\n".join(lineas)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("manifiesto", type=Path)
    p.add_argument("--col-imagen", default="imagen")
    p.add_argument("--col-split", default="split")
    p.add_argument("--grupos", default="palma_id,lote,finca",
                   help="columnas de agrupación separadas por coma; las que no existan se reportan como error")
    p.add_argument("--col-fecha", default="fecha")
    p.add_argument("--temporal", action="store_true", help="exige que el split de prueba sea posterior a los demás")
    p.add_argument("--split-prueba", default="test")
    p.add_argument("--imagenes", type=Path, help="carpeta base de las imágenes para buscar duplicados por hash")
    args = p.parse_args(argv)

    with open(args.manifiesto, newline="", encoding="utf-8") as f:
        lector = csv.DictReader(f)
        columnas = lector.fieldnames or []
        filas = list(lector)
    if not filas:
        print("ERROR: el manifiesto no tiene filas.", file=sys.stderr)
        return 2

    grupos = [g.strip() for g in args.grupos.split(",") if g.strip()]
    requeridas = [args.col_imagen, args.col_split, *grupos]
    if args.temporal:
        requeridas.append(args.col_fecha)
    faltantes = [c for c in requeridas if c not in columnas]
    if faltantes:
        print(f"ERROR: columnas inexistentes en el manifiesto: {', '.join(faltantes)}. "
              f"Columnas disponibles: {', '.join(columnas)}", file=sys.stderr)
        return 2

    conteo = defaultdict(int)
    for fila in filas:
        conteo[fila[args.col_split]] += 1
    print("Filas por split: " + ", ".join(f"{s}={n}" for s, n in sorted(conteo.items())))

    fallas = 0

    for columna in [args.col_imagen, *grupos]:
        cruzados, vacios = cruces(filas, columna, args.col_split)
        if cruzados:
            fallas += 1
            print(f"FALLA [{columna}] {len(cruzados)} valor(es) en más de un split:\n{formatear(cruzados)}")
        else:
            print(f"OK    [{columna}] ningún valor se repite entre splits")
        if vacios:
            print(f"AVISO [{columna}] {vacios} fila(s) sin valor: no se pudieron verificar")

    if args.imagenes:
        por_hash = defaultdict(set)
        ausentes = 0
        for fila in filas:
            ruta = args.imagenes / fila[args.col_imagen]
            if not ruta.is_file():
                ausentes += 1
                continue
            por_hash[sha256(ruta)].add(fila[args.col_split])
        dup = {h[:12]: s for h, s in por_hash.items() if len(s) > 1}
        if dup:
            fallas += 1
            print(f"FALLA [hash] {len(dup)} archivo(s) idéntico(s) en splits distintos:\n{formatear(dup)}")
        else:
            print("OK    [hash] no hay archivos idénticos entre splits")
        if ausentes:
            print(f"AVISO [hash] {ausentes} imagen(es) no encontradas en {args.imagenes}")

    if args.temporal:
        fechas = defaultdict(list)
        for fila in filas:
            texto = (fila.get(args.col_fecha) or "").strip()
            if not texto:
                continue
            try:
                fechas[fila[args.col_split]].append(leer_fecha(texto))
            except ValueError:
                print(f"ERROR: fecha ilegible '{texto}' (usa ISO, p. ej. 2026-03-15)", file=sys.stderr)
                return 2
        if args.split_prueba not in fechas:
            fallas += 1
            print(f"FALLA [temporal] el split '{args.split_prueba}' no tiene fechas")
        else:
            inicio_prueba = min(fechas[args.split_prueba])
            for split, lista in sorted(fechas.items()):
                if split == args.split_prueba:
                    continue
                if max(lista) >= inicio_prueba:
                    fallas += 1
                    print(f"FALLA [temporal] '{split}' llega hasta {max(lista)} y "
                          f"'{args.split_prueba}' empieza el {inicio_prueba}: la prueba debe ser posterior")
                else:
                    print(f"OK    [temporal] '{split}' termina ({max(lista)}) antes de que empiece "
                          f"'{args.split_prueba}' ({inicio_prueba})")

    if fallas:
        print(f"\nResultado: {fallas} problema(s) de fuga. La división NO es válida.")
        return 1
    print("\nResultado: sin fugas detectadas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
