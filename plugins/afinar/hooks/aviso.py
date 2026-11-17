"""Hook UserPromptSubmit: recuerda al agente pedir una comprobación o confirmar lo delicado cuando el pedido no lo dice.

No bloquea ni llama a ningún modelo: agrega una nota al contexto para que el agente proponga una comprobación (o haga
una sola pregunta) antes de empezar, y confirme antes de lo irreversible. Se apaga con AFINAR_AVISO=0.
Falla abierto: ante cualquier error, sale con 0 sin decir nada.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "afinar" / "scripts"))

from revisar import revisar

MINIMO_PALABRAS = 8


def nota(prompt: str) -> str | None:
    resultado = revisar(prompt)
    if not resultado["tarea"] or resultado["palabras"] < MINIMO_PALABRAS:
        return None
    claves = {h["clave"]: h["mensaje"] for h in resultado["hallazgos"]}
    partes = []
    if "comprobacion" in claves:
        partes.append(
            "El pedido no dice cómo se comprueba que quedó bien. Antes de cambiar nada, di en una línea la "
            "comprobación que vas a usar (comando y resultado esperado), deducida del repo; si no puedes deducirla, "
            "haz una sola pregunta."
        )
    if "riesgo" in claves:
        partes.append(f"Ojo: {claves['riesgo']}. Confirma con la persona antes de cualquier acción irreversible.")
    if not partes:
        return None
    partes.append("(Aviso del plugin afinar; la persona puede pulir el pedido con /afinar.)")
    return " ".join(partes)


def main() -> int:
    if os.environ.get("AFINAR_AVISO", "1") == "0":
        return 0
    try:
        datos = json.load(sys.stdin)
        texto = nota(str(datos.get("prompt", "")))
    except Exception:  # un aviso nunca debe estorbar
        return 0
    if texto:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": texto}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
