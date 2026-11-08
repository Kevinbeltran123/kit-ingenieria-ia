# calidad-python

Hooks de calidad para repos Python. Sin dependencias: solo `python3` de la biblioteca estándar.

| Momento | Qué hace |
|---|---|
| Al editar un `.py` (PostToolUse) | `ruff check --fix` + `ruff format` sobre ese archivo. Si quedan errores, Claude los ve y los corrige. |
| Al terminar el turno (Stop) | Si se editaron `.py` en la sesión: verificador de tipos, import-linter y pytest. Si algo falla, Claude no puede terminar hasta corregirlo (un solo reintento). |
| Cuando Claude te necesita (Notification) | Aviso de macOS. |

Skill `verify`: corre todos los sensores sobre el repo completo (ruff, formato, tipos, import-linter, pytest, deptry) antes de un commit o PR.

## Solo corre lo que el repo usa
- Herramientas: primero `.venv/bin/<herramienta>`, si no, la del PATH. Si no existe, se salta.
- Tipos: el primero configurado entre `ty` (`[tool.ty]`/`ty.toml`), `mypy` (`[tool.mypy]`/`mypy.ini`) y `pyright` (`[tool.pyright]`/`pyrightconfig.json`), solo sobre los archivos editados.
- import-linter: solo con `[tool.importlinter]` o `.importlinter`.
- pytest: con `[tool.pytest...]`, `pytest.ini` o carpeta `tests/`. "Sin pruebas" (código 5) no cuenta como fallo.

## Límites
- No ve archivos que Claude cambie con comandos de terminal (sed, scripts). Pre-commit y CI siguen siendo la red final.
- pytest corre la suite completa: en repos con pruebas lentas conviene acotarla (pendiente).
- No es una barrera de seguridad; eso va en reglas `deny` y permisos.

## Probar
    python3 -m pytest tests -q                     # pruebas de los hooks
    claude --plugin-dir ./plugins/calidad-python   # sesión con el plugin cargado
