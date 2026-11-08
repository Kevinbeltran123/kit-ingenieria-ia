# Terceros

- `marketplace-entradas.json`: entradas listas para `plugins[]` del `marketplace.json` del kit, cada una fijada por `sha` de 40 caracteres.
- `AUDITORIA.md`: qué ejecuta cada una, hallazgos y veredicto.

## Actualizar un plugin a un commit nuevo
1. Ver qué cambió entre el SHA fijado y el nuevo, solo en la carpeta del plugin:
   ```bash
   git clone --filter=blob:none <url> /tmp/x && cd /tmp/x
   git diff <SHA_VIEJO> <SHA_NUEVO> --stat -- <path>
   git diff <SHA_VIEJO> <SHA_NUEVO> -- <path>/hooks <path>/.mcp.json <path>/bin <path>/**/*.py <path>/**/*.sh
   ```
2. Repetir la checklist de `AUDITORIA.md` sobre lo que cambió (hooks, MCP, scripts, red, `~/.aws`, `~/.claude`, instalaciones).
3. Cambiar el `sha` (y `ref` si aplica) en `marketplace-entradas.json` y en `.claude-plugin/marketplace.json`.
   Si es `pr-review-toolkit`, también en `plantillas/github/workflows/claude-review.yml` (una prueba lo exige).
   Si el plugin declara `version` en su propio `plugin.json` y el diff no la cambia, el commit nuevo no le llega
   a nadie: Claude Code ve la misma versión y deja la copia en caché. Anótalo en `AUDITORIA.md` y pide
   reinstalarlo (`claude plugin uninstall <plugin>` y `claude plugin install <plugin>@kit-ingenieria-ia`).
4. Anotar en `AUDITORIA.md` la fecha, el SHA nuevo y el veredicto.
5. `claude plugin validate .` desde la raíz del kit.

Nunca subir un SHA sin mirar el diff: el objetivo de fijarlo es que nada cambie sin revisión.

## Copias (no entradas)
`plugins/flujo` es una copia editada de obra/superpowers. Para actualizarla: mismo diff, solo en `skills/<skill>` de las 5 skills; reaplicar los cambios listados en `plugins/flujo/ORIGEN.md`. No lleva `version`: el commit nuevo ya es la versión nueva.
