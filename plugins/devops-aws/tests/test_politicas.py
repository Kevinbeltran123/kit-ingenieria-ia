"""Las políticas de referencia de aws-acceso-agente usan la condición correcta para el MCP de AWS.

`aws:ViaAWSMCPService` es booleana («la llamada vino por un servidor MCP de AWS»).
`aws:CalledViaAWSMCP` es de texto (vale `aws-mcp.amazonaws.com`): con el operador Bool nunca coincide
y la política no deniega nada, sin avisar.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REFS = Path(__file__).resolve().parent.parent / "skills" / "aws-acceso-agente" / "references"


def condiciones_mcp(politica: dict) -> list[tuple[str, str, str]]:
    return [(operador, clave, valor)
            for st in politica["Statement"]
            for operador, claves in st.get("Condition", {}).items()
            for clave, valor in claves.items() if "MCP" in clave]


@pytest.mark.parametrize("archivo", ["scp-sin-escritura-via-mcp.json", "politica-agente-solo-lectura.json"])
def test_la_condicion_de_mcp_es_la_booleana(archivo):
    politica = json.loads((REFS / archivo).read_text())
    assert condiciones_mcp(politica) == [("Bool", "aws:ViaAWSMCPService", "true")]
