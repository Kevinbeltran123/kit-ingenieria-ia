---
name: iac-plan-no-apply
description: Flujo para cambios de infraestructura como código (Terraform, OpenTofu, AWS CDK, CloudFormation) en el que el agente solo llega hasta plan o diff — fmt, validate, tflint, checkov, plan/synth/diff en local, y apply o deploy únicamente desde CI tras un PR revisado. Incluye qué revisar en un plan (destroys, reemplazos, cambios de IAM y red). Úsala al tocar archivos .tf, stacks de CDK, plantillas de CloudFormation, o cuando pidan desplegar, aplicar o cambiar infraestructura.
---

# Infraestructura: el agente planea, CI aplica

Un `apply` mal revisado puede borrar una base de datos. Por eso el agente nunca aplica: prepara el cambio, muestra el plan, y la persona aprueba en un PR que CI aplica con OIDC.

## Flujo con Terraform / OpenTofu
1. `terraform fmt -recursive`
2. `terraform init -backend=false` (si solo se valida) y `terraform validate`
3. `tflint --recursive`
4. `checkov -d .` (o trivy config, no ambos)
5. `terraform plan -out=plan.tfplan` y `terraform show -no-color plan.tfplan` contra el entorno de dev, con el perfil de solo lectura del agente (ver skill `aws-acceso-agente`)
6. Abrir PR con el resumen del plan. CI vuelve a correr el plan, alguien lo revisa y CI hace `apply` del plan aprobado.

## Flujo con AWS CDK
1. Pruebas del stack (`pytest` con `aws_cdk.assertions.Template`)
2. `cdk synth` (falla si hay errores de construcción)
3. `checkov -d cdk.out` o cdk-nag en el stack
4. `cdk diff` contra dev
5. PR → CI ejecuta `cdk deploy` con OIDC.

## Qué revisar en un plan o diff (y resaltarlo en el PR)
| Señal | Por qué importa |
|---|---|
| `destroy` / `-` | Se borra un recurso. ¿Tiene datos? (RDS, S3, DynamoDB, EFS) |
| `-/+` o "requires replacement" | Se destruye y se crea de nuevo: pérdida de datos o de IP/endpoint |
| Cambios en IAM (políticas, roles, trust policies) | Escalada de privilegios; buscar `*` en Action o Resource |
| Security groups con `0.0.0.0/0` | Exposición a internet |
| Cambios en cifrado, backups, `deletion_protection`, `prevent_destroy` | Se debilitan protecciones |
| Recursos fuera del alcance del PR | Deriva (drift) o cambio accidental: investigar antes de seguir |

Si el plan tiene cualquier destroy o reemplazo de un recurso con estado, detenerse y pedir confirmación explícita aunque parezca esperado.

## Reglas
- El agente no ejecuta `apply`, `destroy`, `cdk deploy` ni `cdk destroy`, tampoco con `-auto-approve` "solo en dev". El plugin `barreras` del kit lo bloquea de forma determinista y las reglas deny de `aws-acceso-agente` lo refuerzan.
- Estado remoto con bloqueo (S3 + lock nativo o DynamoDB); nunca editar el state a mano; `terraform import` y `state mv` también van por PR.
- Versiones fijadas: `required_version` y providers con `~>` y `.terraform.lock.hcl` commiteado.
- Recursos con datos: `prevent_destroy` (Terraform) o `RemovalPolicy.RETAIN` (CDK).
- Si la empresa usa Terraform: MCP de HashiCorp solo con `--toolsets registry` (documentación, sin operaciones).

## Verificación
- fmt, validate, tflint y checkov sin errores (o hallazgos justificados con skip comentado).
- El PR incluye el resumen del plan: cuántos add / change / destroy y la lista de los destroy y reemplazos.
- Ningún comando de apply o deploy en el historial de la sesión.
