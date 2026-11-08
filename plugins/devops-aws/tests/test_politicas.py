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


def acciones_denegadas(politica: dict) -> dict[str, list[str]]:
    """Acción denegada -> recursos a los que aplica."""
    salida: dict[str, list[str]] = {}
    for st in politica["Statement"]:
        if st["Effect"] == "Deny":
            recursos = st["Resource"] if isinstance(st["Resource"], list) else [st["Resource"]]
            for accion in st["Action"]:
                salida.setdefault(accion, []).extend(recursos)
    return salida


def test_la_politica_de_lectura_no_deja_ver_secretos():
    denegadas = acciones_denegadas(json.loads((REFS / "politica-agente-solo-lectura.json").read_text()))
    for accion in ("secretsmanager:GetSecretValue", "ssm:GetParameter", "ssm:GetParameters",
                   "ssm:GetParametersByPath", "ssm:GetParameterHistory", "kms:Decrypt"):
        assert accion in denegadas, accion
    # El tfstate guarda secretos en texto plano y ReadOnlyAccess incluye s3:Get*.
    assert any("tfstate" in r for r in denegadas.get("s3:GetObject", []))


def test_los_permisos_de_referencia_cubren_env_en_cualquier_carpeta():
    reglas = json.loads((REFS / "settings-permisos-aws.json").read_text())["permissions"]["deny"]
    assert "Read(**/.env)" in reglas and "Read(**/.env.*)" in reglas
    assert not [r for r in reglas if r.startswith("Read(./")]


@pytest.mark.parametrize("archivo", ["scp-sin-escritura-via-mcp.json", "politica-agente-solo-lectura.json"])
def test_la_condicion_de_mcp_es_la_booleana(archivo):
    politica = json.loads((REFS / archivo).read_text())
    assert condiciones_mcp(politica) == [("Bool", "aws:ViaAWSMCPService", "true")]
