"""Corre una comprobación pesada (build, suite completa) en uno de pocos turnos compartidos por toda la máquina.

Uso: pesado.py <comando> [args...]
FLOTA_TURNOS (por defecto 2) y FLOTA_TURNOS_DIR (por defecto ~/.local/state/flota/turnos) deben ser iguales para
todos los carriles. Un turno de un proceso muerto se libera solo.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path


def vivo(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def tomar_turno(directorio: Path, turnos: int) -> Path | None:
    for i in range(1, turnos + 1):
        turno = directorio / f"turno-{i}"
        try:
            turno.mkdir()
        except FileExistsError:
            try:
                pid = int((turno / "pid").read_text())
            except (OSError, ValueError):
                continue  # recién creado por otro proceso: todavía no escribe el pid
            if not vivo(pid):
                (turno / "pid").unlink(missing_ok=True)
                turno.rmdir()
            continue
        (turno / "pid").write_text(str(os.getpid()))
        return turno
    return None


def main(argv: list[str] | None = None) -> int:
    comando = sys.argv[1:] if argv is None else argv
    if not comando:
        print(__doc__, file=sys.stderr)
        return 2
    turnos = int(os.environ.get("FLOTA_TURNOS", "2"))
    directorio = Path(os.environ.get("FLOTA_TURNOS_DIR", Path.home() / ".local" / "state" / "flota" / "turnos"))
    directorio.mkdir(parents=True, exist_ok=True)
    espera = float(os.environ.get("FLOTA_TURNOS_ESPERA", "15"))
    while True:
        turno = tomar_turno(directorio, turnos)
        if turno:
            break
        print(f"pesado: los {turnos} turnos están ocupados, espero ({time.strftime('%H:%M:%S')})", file=sys.stderr)
        time.sleep(espera)
    try:
        print(f"pesado: {turno.name}: {' '.join(comando)}", file=sys.stderr)
        return subprocess.call(comando)
    finally:
        (turno / "pid").unlink(missing_ok=True)
        turno.rmdir()


if __name__ == "__main__":
    sys.exit(main())
