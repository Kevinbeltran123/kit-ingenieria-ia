"""Notification: aviso de macOS cuando Claude necesita permiso o espera respuesta."""

from __future__ import annotations

import json
import subprocess
import sys


def main() -> int:
    if sys.platform != "darwin":
        return 0
    datos = json.load(sys.stdin)
    mensaje = datos.get("message") or "Claude Code te necesita"
    titulo = datos.get("title") or "Claude Code"
    # El texto va como argumento, no dentro del script, para que no se pueda inyectar AppleScript.
    subprocess.run(
        ["osascript", "-e", "on run argv", "-e",
         "display notification (item 1 of argv) with title (item 2 of argv)",
         "-e", "end run", mensaje, titulo],
        capture_output=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
