# calidad-python

Hooks de calidad para repos Python. Sin dependencias: solo `python3` de la biblioteca estándar.

| Momento | Qué hace |
|---|---|
| Antes de editar o de correr un comando (PreToolUse) | Solo tú silencias reglas: bloquea que Claude agregue `# noqa`, `# type: ignore`, `# pragma: no cover` y similares, o que corra opciones que silencian todo de una vez (`ruff --add-noqa`, `ty --add-ignore`). Si un falso positivo merece la excepción, Claude te dice cuál y en qué línea, y la agregas tú. |
| Al editar un `.py` (PostToolUse) | `ruff check --fix` + `ruff format` sobre ese archivo. Si quedan errores, Claude los ve y los corrige. |
| Al terminar el turno (Stop) | Si se editaron `.py` en la sesión: verificador de tipos, import-linter y pytest. Si algo falla, Claude no puede terminar hasta corregirlo, y se vuelve a revisar después de cada corrección. Una herramienta configurada pero no instalada cuenta como sin revisar, no como aprobada: pide instalarla (`uv sync`). Si tras 2 intentos sigue fallando, termina y te avisa. |
| Cuando Claude te necesita (Notification) | Aviso de macOS. |

Skill `verify`: corre todos los sensores sobre el repo completo (ruff, formato, tipos, import-linter, pytest, deptry) antes de un commit o PR.

## Solo corre lo que el repo usa
- Herramientas: primero `.venv/bin/<herramienta>`, si no, la del PATH. Si no existe, se salta.
- Tipos: el primero configurado entre `ty` (`[tool.ty]`/`ty.toml`), `mypy` (`[tool.mypy]`/`mypy.ini`) y `pyright` (`[tool.pyright]`/`pyrightconfig.json`), solo sobre los archivos editados.
- import-linter: solo con `[tool.importlinter]` o `.importlinter`.
- pytest: con `[tool.pytest...]`, `pytest.ini` o carpeta `tests/`. "Sin pruebas" (código 5) no cuenta como fallo.

## Solo la persona silencia reglas (`no_silenciar.py`)
- Cuenta todo comentario que apaga un sensor en un `.py` o `.pyi`: `# noqa`, `# ruff: noqa`, `# ruff: disable[...]`,
  `# type: ignore`, `# ty: ignore`, `# pyright: ...` y `# mypy: ...` (salvo `strict`), `# pragma: no cover`, `no branch`
  y `no mutate`, `# nosec`, `# nosemgrep` y `# pylint: disable`. `# fmt:` e `# isort:` no cuentan: son de formato.
- Compara el archivo entero antes y después: quitar una excepción, o editar o mover una línea que ya la tenía, pasa.
  Agregar una o cambiar su texto (sumarle una regla, volverla general) se bloquea.
- Por terminal: `ruff --add-noqa`, `ty --add-ignore`, `ty --update-baseline`, `complexipy --snapshot-create`,
  `vulture --make-whitelist`, y escribir una excepción en un `.py` con `>`, `tee`, `sed -i` o `perl -i`. Lo que va entre
  comillas es texto: mencionarlo en un mensaje de commit no lo bloquea.
- Para una sesión en la que sí quieres que Claude las agregue (la línea base al adoptar ruff en un repo viejo, por
  ejemplo): `CALIDAD_PYTHON_PERMITIR_SILENCIAR=1 claude`.

## Límites
- No ve archivos que Claude cambie con comandos de terminal (sed, scripts). Pre-commit y CI siguen siendo la red final.
- `no_silenciar.py` no vigila las excepciones en la configuración (`ignore` y `per-file-ignores` de ruff, `exclude_also`
  de coverage, `ignore_imports` de import-linter), en notebooks ni las que escribe un script: eso se revisa en el PR.
- pytest corre la suite completa: en repos con pruebas lentas conviene acotarla (pendiente).
- No es una barrera de seguridad; eso va en reglas `deny` y permisos.

## Probar
    python3 -m pytest tests -q                     # pruebas de los hooks
    claude --plugin-dir ./plugins/calidad-python   # sesión con el plugin cargado
