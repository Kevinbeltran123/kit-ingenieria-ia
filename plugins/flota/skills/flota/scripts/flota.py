"""Panel principal del espacio «Flota» de cmux: prepara la sesión de herdr y se conecta a ella.

Lo corre el comando «Flota» de cmux (y cmux al reabrir la app, si apruebas el comando en Settings > Terminal >
Resume Commands). Hace, en orden:
1. Registra en cmux cómo reanudar este panel (`cmux surface resume set`).
2. En segundo plano, cuando el servidor de herdr responde: un espacio por proyecto (`carril.py espacios`) y el servidor
   del tablero dentro de herdr (`carril.py tablero`), que sobrevive a cerrar cmux.
3. Se convierte en el cliente de herdr de la sesión (`herdr --session flota`).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SESION = os.environ.get("FLOTA_SESION", "flota")
REGISTRO = Path.home() / ".local" / "state" / "flota"


def main() -> int:
    REGISTRO.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("FLOTA_MODELO_CODEX", "gpt-6-luna")
    if shutil.which("cmux") and os.environ.get("CMUX_SURFACE_ID"):
        subprocess.run(
            ["cmux", "surface", "resume", "set", "--name", "flota", "--shell", f"python3 -I {AQUI / 'flota.py'}"],
            capture_output=True, timeout=10, check=False,
        )  # fmt: skip
    carril = AQUI / "carril.py"
    with (REGISTRO / "arranque.log").open("a", encoding="utf-8") as log:
        orden = (f"{sys.executable} -I {carril} espacios --sesion {SESION} --espera 30; "
                 f"{sys.executable} -I {carril} tablero --sesion {SESION} --espera 30")  # fmt: skip
        subprocess.Popen(["sh", "-c", orden], stdout=log, stderr=log, start_new_session=True)
    herdr = shutil.which("herdr")
    if not herdr:
        print("no se encontró herdr en PATH (brew install herdr)", file=sys.stderr)
        return 1
    env = {k: v for k, v in os.environ.items() if k != "HERDR_SESSION"}
    os.execve(herdr, [herdr, "--session", SESION], env)
    return 0


if __name__ == "__main__":
    sys.exit(main())
