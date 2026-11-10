# devops-aws

Instalar en un repo: `/plugin install devops-aws --marketplace Kevinbeltran123/kit-ingenieria-ia` (registra el marketplace si hace falta; con `bin/adoptar.py` ya queda en `.claude/settings.json`).

Skills de DevOps para Python + GitHub + AWS. Solo prompts y un script de revisión; no trae hooks ni MCP.

| Skill | Cuándo |
|---|---|
| `aws-acceso-agente` | Antes de que el agente toque AWS: SSO, perfil de solo lectura, Deny de secretos, `aws:ViaAWSMCPService`, reglas deny |
| `gha-seguro` | Al crear o revisar `.github/workflows`: permisos, pin por SHA, zizmor, OIDC, Dependabot, claude-code-action |
| `dockerfile-python-uv` | Dockerfiles de servicios Python con uv |
| `iac-plan-no-apply` | Terraform, OpenTofu, CDK: el agente llega hasta plan o diff; apply solo en CI |
| `observabilidad-python` | structlog, OpenTelemetry, métricas, qué no loguear |

## Se complementa con
- Plugin `aws-core` (aws/agent-toolkit-for-aws): skills de servicios de AWS y MCP de 8 herramientas.
- Plugin `barreras` del kit: bloqueo determinista de apply, deploy y destroy.
- `plantillas/` del kit: workflows, Dockerfile y dependabot listos para copiar.

## Script
`skills/gha-seguro/scripts/revisar_pins.py [.github]`: falla si un `uses:` no está fijado por SHA (o una imagen `docker://` sin digest) o si un workflow no declara `permissions:`.

## Límites
- Las políticas IAM de `references/` son punto de partida: validarlas con IAM Access Analyzer y ajustarlas a la cuenta.
- `revisar_pins.py` lee YAML línea por línea, sin parser completo: complementa a zizmor, no lo reemplaza.

## Probar
    python3 -m pytest tests -q
