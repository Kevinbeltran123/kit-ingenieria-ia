---
name: gha-seguro
description: Escribe y revisa workflows de GitHub Actions seguros — permisos mínimos, actions fijadas por SHA (pinact), zizmor, OIDC a AWS con trust policy limitada a repo y rama, sin pull_request_target con checkout del PR, manejo de secretos, cooldown de Dependabot y claude-code-action configurado con herramientas mínimas. Úsala al crear o modificar archivos en .github/workflows, al configurar CI/CD, deploy a AWS desde GitHub, Dependabot, o revisión con Claude en PRs.
---

# GitHub Actions seguras

En marzo de 2026 envenenaron 76 de 77 tags de `trivy-action`; quien fijaba por SHA no se vio afectado. Los workflows son código que corre con secretos: se revisan como tal.

## Reglas para cada workflow
1. **Permisos mínimos.** `permissions: {}` (o `contents: read`) arriba del archivo y, en cada job, solo lo que ese job necesita.
2. **Todo `uses:` fijado por SHA de 40 caracteres**, con la versión en un comentario:
   `uses: actions/checkout@<sha40> # v5.0.0`. Para fijarlos: `pinact run`. Imágenes `docker://` por `@sha256:`.
3. **`actions/checkout` con `persist-credentials: false`**, salvo que el job haga push.
4. **Nunca `pull_request_target` con checkout del código del PR** (`ref: ${{ github.event.pull_request.head.sha }}`): ejecuta código ajeno con secretos. Para PRs de forks, usar `pull_request`.
5. **Sin inyección de plantillas:** no poner `${{ github.event.* }}` (títulos, ramas, cuerpos) dentro de `run:`. Pasarlo por `env:` y usar la variable entre comillas.
6. **Secretos:** solo en el job que los usa, mejor en un `environment` con reglas de protección. Nada de `echo` de secretos ni `set -x` en jobs con secretos.
7. **AWS por OIDC, nunca llaves guardadas** (ver abajo).
8. **Timeouts** (`timeout-minutes`) y `concurrency` para no dejar jobs colgados.

## OIDC a AWS
```yaml
permissions:
  id-token: write
  contents: read
steps:
  - uses: aws-actions/configure-aws-credentials@<sha40> # v6.x
    with:
      role-to-assume: arn:aws:iam::111111111111:role/gha-deploy-mi-repo
      aws-region: us-east-1
```
Trust policy del rol: `references/trust-policy-oidc.json`. La condición `sub` es obligatoria: sin ella cualquier repo de GitHub puede asumir el rol. Limitarla a `repo:ORG/REPO:ref:refs/heads/main` o a `repo:ORG/REPO:environment:produccion`.

## Dependabot
`dependabot.yml` con ecosistemas `uv`, `github-actions` y `docker`; `cooldown` de varios días (por defecto son 3) alineado con `exclude-newer` de uv; agrupar parches; auto-merge solo de parches con CI en verde. Plantilla en `plantillas/` del kit.

## claude-code-action (revisión con Claude en PRs)
- Fijada por SHA. Autenticación con la GitHub App o el token efímero, **no con un PAT**.
- `--allowedTools` mínimo (por ejemplo, solo lectura y comentar). No activar `allowed_non_write_users`.
- Disparar solo en `pull_request` de colaboradores o por comentario `@claude` de usuarios con permiso de escritura.
- Tratar el contenido del PR como entrada hostil: puede traer inyección de prompts. El job de Claude no debe tener secretos de deploy.
- Con Bedrock, autenticar por OIDC igual que arriba.

## Verificación
Con el script `scripts/revisar_pins.py` de esta skill (ruta relativa a la carpeta de la skill):
```bash
python3 <carpeta-de-esta-skill>/scripts/revisar_pins.py .github
zizmor .github/workflows
```
- `revisar_pins.py` falla si algún `uses:` no está fijado por SHA o si un workflow no declara `permissions:` arriba.
- `zizmor` sin hallazgos de severidad media o alta (o justificados con comentario `# zizmor: ignore[...]`).
- Ambos van también en pre-commit y en CI. `actionlint` es complemento opcional de sintaxis.
