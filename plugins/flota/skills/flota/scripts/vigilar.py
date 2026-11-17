"""Despierta al coordinador cuando un carril entrega, una revisión termina, la puerta avanza o un carril se detiene.

Uso: vigilar.py --run DIR [--sesion S] [--timeout SEGUNDOS] [--intervalo SEGUNDOS]
Correrlo en segundo plano (una sola instancia por corrida) y volver a armarlo cada vez que sale. Imprime una de:
  BASELINE:  primera vez; guarda lo que ya había y sale (vuelve a correrlo)
  CHANGED:   líneas READY / REVIEW-READY / Done nuevas
  STOPPED:   un carril que estaba trabajando paró sin entregar (suele ser una pregunta o un error: lee su pantalla)
  TIMEOUT:   nada nuevo en el tiempo pedido
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import agentes, cargar_carriles, lineas_listo, puerta


def firma(run: Path) -> list[str]:
    lineas = [f"{x['tipo']}:{x['carril']} {x['resto']}".rstrip() for x in lineas_listo(run)]
    lineas += [f"done:{linea}" for linea in puerta(run).get("Done", [])]
    return sorted(set(lineas))


def trabajando(sesion: str | None, nombres: set[str]) -> dict[str, str]:
    if not sesion:
        return {}
    return {ag["name"]: ag.get("agent_status", "") for ag in agentes(sesion) if ag.get("name") in nombres}


def vigilar(run: Path, sesion: str | None, timeout: float, intervalo: float) -> str:
    visto = run / ".vigilar-visto"
    ahora = firma(run)
    if not visto.exists():
        visto.write_text("\n".join(ahora), encoding="utf-8")
        return "BASELINE:\n" + "\n".join(ahora)
    previo = set(visto.read_text(encoding="utf-8").splitlines())
    fin = time.time() + timeout
    ocupados: set[str] = set()
    while True:
        nuevas = [linea for linea in ahora if linea not in previo]
        if nuevas:
            visto.write_text("\n".join(ahora), encoding="utf-8")
            return "CHANGED:\n" + "\n".join(nuevas)
        nombres = set(cargar_carriles(run)) or set()
        estados = trabajando(sesion, nombres)
        for nombre in sorted(ocupados):
            estado = estados.get(nombre, "desaparecido")
            if estado != "working":
                return f"STOPPED: {nombre} quedó {estado} sin línea READY nueva (lee su pantalla)"
        ocupados = {n for n, e in estados.items() if e == "working"}
        if time.time() >= fin:
            return "TIMEOUT: nada nuevo"
        time.sleep(intervalo)
        ahora = firma(run)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run", required=True)
    p.add_argument("--sesion")
    p.add_argument("--timeout", type=float, default=3600)
    p.add_argument("--intervalo", type=float, default=20)
    a = p.parse_args(argv)
    print(vigilar(Path(a.run).expanduser().resolve(), a.sesion, a.timeout, a.intervalo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
