---
name: verify
description: Corre todos los sensores de calidad del repo Python (ruff, formato, tipos, import-linter, pytest, deptry) y resume qué pasó. Úsala antes de cada commit o PR, al terminar una tarea, o cuando pidan "verificar", "correr checks", "run the checks", "¿está listo?".
---

# verify

Antes de decir que algo está terminado, demuéstralo corriendo los sensores.

## Pasos

1. Desde la raíz del repo:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/verify/scripts/verify.py" .
   ```
   Corre lo que el repo tenga configurado, empezando por `uv lock --check` (lo mismo que exige `uv sync --locked`
   en CI). Busca cada herramienta primero en `.venv/bin` y después en el PATH. Una herramienta configurada que no
   está instalada sale como "sin revisar" y el script sale con 1: corre `uv sync` y repite.

2. Si algo dice `FALLA`, arréglalo y vuelve a correr el script. No desactives reglas, no agregues `# noqa` / `# type: ignore` ni borres pruebas para que pase. Si una regla es un falso positivo, explica por qué y dile a la persona qué comentario agregar y en qué línea: la excepción la agrega ella (el hook `no_silenciar.py` no te deja).

3. Reporta el resultado tal cual: `N/M pasos OK, K sin revisar` y, si quedó algo sin resolver, qué y por qué.

## Si el repo no tiene herramientas configuradas

El script dice "Nada que verificar" y sale con 1. No lo reportes como éxito: di que el repo no tiene sensores y sugiere la plantilla de calidad del kit (`plantillas/` en el marketplace).

## Relación con el resto del kit

- El hook de Stop de `calidad-python` corre una versión reducida (tipos, import-linter y pytest) solo sobre lo editado. Esta skill corre todo el repo.
- Para fallos de pruebas débiles o mutantes, ver la skill `calidad-pruebas`.
