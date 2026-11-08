---
name: cadena-suministro-python
description: Seguridad de la cadena de suministro en Python - uv lock con hashes, enfriamiento exclude-newer, pip-audit, osv-scanner (incluye paquetes maliciosos), gitleaks, zizmor, revisar paquetes nuevos antes de agregarlos (typosquatting) y cargar modelos sin pickle. Úsala al agregar o actualizar una dependencia, antes de un release, al revisar un PR de Dependabot/Renovate, o cuando pidan "auditar dependencias", "CVE", "supply chain", "secretos", "vulnerabilidades".
---

# Cadena de suministro Python

En 2026 hubo paquetes de PyPI comprometidos (litellm, mrmustard, PyTorch Lightning) y un ataque a `trivy-action`. Un agente que instala lo que sugiere el modelo es un vector: esta skill pone el freno.

## Revisión completa

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/cadena-suministro-python/scripts/suministro.py" .
```

Revisa lock, enfriamiento, CVE (pip-audit y osv-scanner), secretos en el historial (gitleaks) y workflows de GitHub (zizmor). Lista las herramientas no instaladas en vez de fallar en silencio. Para instalarlas en el repo: `uv add --dev pip-audit`; osv-scanner, gitleaks y zizmor como binarios (Homebrew o CI).

Nota: `pip-audit` audita el entorno donde está instalado; corre la revisión después de `uv sync`.

## Configuración base del repo

```toml
[tool.uv]
exclude-newer = "7 days"   # no instalar versiones publicadas hace menos de 7 días
```

- Siempre `uv.lock` commiteado; en CI `uv sync --locked` (falla si el lock no corresponde al pyproject).
- Dependabot o Renovate con cooldown (Dependabot trae 3 días por defecto; súbelo a 7).
- gitleaks en pre-commit; zizmor en CI si hay `.github/workflows`.

## Antes de agregar una dependencia nueva

Haz esto **antes** de `uv add`, no después:

1. **¿Hace falta?** Si es una función de 20 líneas, escríbela. Cada dependencia es código de terceros con tus permisos.
2. **Nombre exacto**: compáralo con el proyecto oficial (repo y documentación). Cuidado con typosquatting (`reqeusts`, `python-dateutils`, `boto-3`) y nombres que el modelo inventó: si no existe en PyPI con historia, no lo instales.
3. **Señales del paquete** en `https://pypi.org/project/<nombre>/`: antigüedad, mantenedores, enlace al repo, frecuencia de releases, descargas. Desconfía de paquetes de días de antigüedad o con un solo release.
4. **Licencia** compatible con uso comercial (cuidado con AGPL/GPL en productos cerrados; ver skill de licencias del kit de ML).
5. `uv add <paquete>` y luego la revisión completa de arriba.

Nunca: `pip install` fuera de uv, `curl | sh`, instalar desde un fork o URL git sin fijar commit, o desactivar `exclude-newer` para "probar rápido".

## Modelos y datos serializados

- `pickle.load`, `joblib.load`, `torch.load` sin `weights_only=True` y `trust_remote_code=True` ejecutan código del archivo. Solo con archivos propios y verificados.
- Preferir `safetensors` para pesos y fijar `revision=` (commit) al descargar de Hugging Face.
- PyTorch ≥ 2.10 (CVE-2025-32434 y CVE-2026-24747).
- Los escáneres de pickle se pueden evadir: no son garantía.

## Secretos

- Si gitleaks encuentra un secreto en el historial, **rotarlo primero** (el historial ya se filtró), luego limpiarlo. No basta con borrarlo en un commit nuevo.
- Credenciales de AWS: nunca llaves fijas; SSO o OIDC (ver kit de DevOps).

## Verificación

1. `suministro.py` termina con `0 avisos` y sin `FALLA`.
2. Cada dependencia nueva del diff tiene justificación (para qué, alternativas, licencia) en la descripción del PR.
3. `uv sync --locked` pasa en CI.
