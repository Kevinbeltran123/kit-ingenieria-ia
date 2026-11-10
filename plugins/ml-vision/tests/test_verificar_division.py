"""Pruebas de scripts/verificar_division.py."""

import csv
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "skills" / "division-sin-fuga" / "scripts" / "verificar_division.py"
COLUMNAS = ["imagen", "split", "palma_id", "lote", "finca", "fecha"]


def manifiesto(tmp_path: Path, filas: list[dict], columnas=COLUMNAS) -> Path:
    ruta = tmp_path / "manifest.csv"
    with ruta.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columnas)
        w.writeheader()
        for fila in filas:
            w.writerow({c: fila.get(c, "") for c in columnas})
    return ruta


def correr(*args):
    return subprocess.run([sys.executable, "-I", str(SCRIPT), *map(str, args)], capture_output=True, text=True)


def fila(img, split, palma, lote="L1", finca="F1", fecha="2026-01-10"):
    return {"imagen": img, "split": split, "palma_id": palma, "lote": lote, "finca": finca, "fecha": fecha}


def division_limpia():
    return [
        fila("a.jpg", "train", "P1", "L1", "F1", "2026-01-10"),
        fila("b.jpg", "train", "P2", "L1", "F1", "2026-01-11"),
        fila("c.jpg", "val", "P3", "L2", "F2", "2026-02-01"),
        fila("d.jpg", "test", "P4", "L3", "F3", "2026-03-01"),
    ]


def test_division_limpia_pasa(tmp_path):
    r = correr(manifiesto(tmp_path, division_limpia()), "--temporal")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "sin fugas" in r.stdout
    assert "train=2" in r.stdout and "test=1" in r.stdout


def test_misma_palma_en_dos_splits_falla(tmp_path):
    filas = [*division_limpia(), fila("e.jpg", "test", "P1", "L3", "F3", "2026-03-02")]
    r = correr(manifiesto(tmp_path, filas))
    assert r.returncode == 1
    assert "FALLA [palma_id]" in r.stdout and "P1: test, train" in r.stdout


def test_mismo_lote_en_dos_splits_falla_aunque_las_palmas_sean_distintas(tmp_path):
    filas = [*division_limpia(), fila("e.jpg", "test", "P9", "L1", "F3", "2026-03-02")]
    r = correr(manifiesto(tmp_path, filas))
    assert r.returncode == 1
    assert "FALLA [lote]" in r.stdout
    assert "OK    [palma_id]" in r.stdout


def test_misma_finca_en_dos_splits_falla(tmp_path):
    filas = [*division_limpia(), fila("e.jpg", "test", "P9", "L9", "F1", "2026-03-02")]
    r = correr(manifiesto(tmp_path, filas))
    assert r.returncode == 1 and "FALLA [finca]" in r.stdout


def test_misma_imagen_en_dos_splits_falla(tmp_path):
    filas = [*division_limpia(), fila("a.jpg", "test", "P8", "L8", "F8", "2026-03-02")]
    r = correr(manifiesto(tmp_path, filas), "--grupos", "palma_id")
    assert r.returncode == 1 and "FALLA [imagen]" in r.stdout


def test_grupos_configurables_solo_palma(tmp_path):
    # Mismo lote en train y test, pero solo se pide verificar por palma: pasa.
    filas = [fila("a.jpg", "train", "P1", "L1"), fila("b.jpg", "test", "P2", "L1")]
    r = correr(manifiesto(tmp_path, filas), "--grupos", "palma_id")
    assert r.returncode == 0, r.stdout


def test_columnas_con_otros_nombres(tmp_path):
    cols = ["path", "subset", "tree", "block"]
    filas = [
        {"path": "a.jpg", "subset": "train", "tree": "T1", "block": "B1"},
        {"path": "b.jpg", "subset": "test", "tree": "T1", "block": "B2"},
    ]
    r = correr(
        manifiesto(tmp_path, filas, cols), "--col-imagen", "path", "--col-split", "subset", "--grupos", "tree,block"
    )
    assert r.returncode == 1 and "FALLA [tree]" in r.stdout


def test_columna_inexistente_es_error_de_uso(tmp_path):
    cols = ["imagen", "split", "palma_id"]
    r = correr(manifiesto(tmp_path, [{"imagen": "a.jpg", "split": "train", "palma_id": "P1"}], cols))
    assert r.returncode == 2
    assert "lote" in r.stderr and "finca" in r.stderr


def test_manifiesto_vacio_es_error_de_uso(tmp_path):
    r = correr(manifiesto(tmp_path, []))
    assert r.returncode == 2


def test_valores_vacios_se_avisan_pero_no_fallan(tmp_path):
    filas = [*division_limpia(), fila("e.jpg", "test", "", "L3", "F3", "2026-03-05")]
    r = correr(manifiesto(tmp_path, filas))
    assert r.returncode == 0
    assert "AVISO [palma_id] 1 fila(s) sin valor" in r.stdout


def test_temporal_prueba_anterior_falla(tmp_path):
    filas = division_limpia()
    filas[0]["fecha"] = "2026-04-01"  # train posterior al inicio de test
    r = correr(manifiesto(tmp_path, filas), "--temporal")
    assert r.returncode == 1
    assert "FALLA [temporal] 'train'" in r.stdout


def test_temporal_misma_fecha_de_borde_falla(tmp_path):
    filas = division_limpia()
    filas[2]["fecha"] = "2026-03-01"  # val termina el mismo día que empieza test
    r = correr(manifiesto(tmp_path, filas), "--temporal")
    assert r.returncode == 1 and "FALLA [temporal] 'val'" in r.stdout


def test_temporal_sin_flag_no_se_revisa(tmp_path):
    filas = division_limpia()
    filas[0]["fecha"] = "2027-01-01"
    assert correr(manifiesto(tmp_path, filas)).returncode == 0


def test_temporal_acepta_fecha_hora(tmp_path):
    filas = division_limpia()
    filas[3]["fecha"] = "2026-03-01T08:30:00"
    assert correr(manifiesto(tmp_path, filas), "--temporal").returncode == 0


def test_temporal_fecha_ilegible_es_error(tmp_path):
    filas = division_limpia()
    filas[1]["fecha"] = "11/01/2026"
    r = correr(manifiesto(tmp_path, filas), "--temporal")
    assert r.returncode == 2 and "ilegible" in r.stderr


def test_temporal_sin_split_de_prueba_falla(tmp_path):
    filas = [f for f in division_limpia() if f["split"] != "test"]
    r = correr(manifiesto(tmp_path, filas), "--temporal")
    assert r.returncode == 1 and "no tiene fechas" in r.stdout


def test_split_de_prueba_con_otro_nombre(tmp_path):
    filas = division_limpia()
    filas[3]["split"] = "holdout"
    r = correr(manifiesto(tmp_path, filas), "--temporal", "--split-prueba", "holdout")
    assert r.returncode == 0, r.stdout


def test_duplicado_por_hash_entre_splits_falla(tmp_path):
    imgs = tmp_path / "imgs"
    imgs.mkdir()
    for nombre, contenido in [("a.jpg", b"AAA"), ("b.jpg", b"BBB"), ("c.jpg", b"CCC"), ("d.jpg", b"AAA")]:
        (imgs / nombre).write_bytes(contenido)
    r = correr(manifiesto(tmp_path, division_limpia()), "--imagenes", imgs)
    assert r.returncode == 1 and "FALLA [hash]" in r.stdout


def test_duplicado_por_hash_dentro_del_mismo_split_no_falla(tmp_path):
    imgs = tmp_path / "imgs"
    imgs.mkdir()
    for nombre, contenido in [("a.jpg", b"AAA"), ("b.jpg", b"AAA"), ("c.jpg", b"CCC"), ("d.jpg", b"DDD")]:
        (imgs / nombre).write_bytes(contenido)
    r = correr(manifiesto(tmp_path, division_limpia()), "--imagenes", imgs)
    assert r.returncode == 0 and "OK    [hash]" in r.stdout


def test_imagenes_ausentes_se_avisan(tmp_path):
    imgs = tmp_path / "imgs"
    imgs.mkdir()
    (imgs / "a.jpg").write_bytes(b"AAA")
    r = correr(manifiesto(tmp_path, division_limpia()), "--imagenes", imgs)
    assert r.returncode == 0 and "AVISO [hash] 3 imagen(es)" in r.stdout


def test_ninguna_imagen_encontrada_es_error_de_uso(tmp_path):
    """Sin imágenes (por ejemplo en CI, donde DVC no las baja) el chequeo por hash no corre: no puede decir OK."""
    (tmp_path / "imgs").mkdir()
    r = correr(manifiesto(tmp_path, division_limpia()), "--imagenes", tmp_path / "imgs")
    assert r.returncode == 2
    assert "no se encontró ninguna imagen" in r.stdout


def test_columna_sha256_detecta_duplicados_sin_las_imagenes(tmp_path):
    filas = division_limpia()
    for f, h in zip(filas, ["h1", "h2", "h3", "h1"]):
        f["sha256"] = h
    r = correr(manifiesto(tmp_path, filas, columnas=[*COLUMNAS, "sha256"]), "--grupos", "palma_id,lote,finca,sha256")
    assert r.returncode == 1 and "FALLA [sha256]" in r.stdout


def test_reporte_limita_ejemplos(tmp_path):
    filas = [fila(f"t{i}.jpg", "train", f"P{i}", f"L{i}", "F1") for i in range(15)]
    filas += [fila(f"x{i}.jpg", "test", f"P{i}", f"M{i}", "F2") for i in range(15)]
    r = correr(manifiesto(tmp_path, filas), "--grupos", "palma_id")
    assert r.returncode == 1 and "... y 5 más" in r.stdout
