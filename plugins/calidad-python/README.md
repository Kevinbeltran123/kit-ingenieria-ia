# calidad-python

Instalar en un repo: `/plugin install calidad-python --marketplace Kevinbeltran123/kit-ingenieria-ia` (registra el marketplace si hace falta; con `bin/adoptar.py` ya queda en `.claude/settings.json`).

Hooks de calidad para repos Python. Sin dependencias: solo `python3` de la biblioteca estándar.

| Momento | Qué hace |
|---|---|
| Antes de editar o de correr un comando (PreToolUse) | Solo tú silencias reglas: bloquea que Claude agregue `# noqa`, `# type: ignore`, `# pragma: no cover` y similares, o que corra opciones que silencian todo de una vez (`ruff --add-noqa`, `ty --add-ignore`), y que salte pruebas (`skip`, `xfail`; un `skipif` nuevo te lo pregunta). Si un falso positivo merece la excepción, Claude te dice cuál y en qué línea, y la agregas tú. |
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
- Pruebas, en cualquier `.py`: bloquea skip y xfail (también `xfail(strict=True)`: con la prueba fallando, la suite
  queda en verde), `skipif(True)`, `pytest.skip()`, `SkipTest`, `pytest.exit(returncode=0)`, `os._exit(0)` y
  `outcome = "passed"`: los trucos documentados de agentes que hacen pasar pruebas sin arreglarlas (ImpossibleBench,
  2025; Baker et al., OpenAI, 2025; Anthropic, 2025). Un `skipif` o un `unittest.skipIf/skipUnless` nuevo te lo
  pregunta: es legítimo sin GPU o en otro sistema, pero deja código sin probar ahí. `pytest.importorskip` pasa.
- Por terminal: `ruff --add-noqa`, `ty --add-ignore`, `ty --update-baseline`, `complexipy --snapshot-create`,
  `vulture --make-whitelist`, y escribir una excepción en un `.py` con `>`, `tee`, `sed -i` o `perl -i`. Lo que va entre
  comillas es texto: mencionarlo en un mensaje de commit no lo bloquea.
- Para una sesión en la que sí quieres que Claude las agregue (la línea base al adoptar ruff en un repo viejo, por
  ejemplo): `CALIDAD_PYTHON_PERMITIR_SILENCIAR=1 claude`.

## Límites
- No ve archivos que Claude cambie con comandos de terminal (sed, scripts). Pre-commit y CI siguen siendo la red final.
- `no_silenciar.py` no vigila las excepciones en la configuración (`ignore` y `per-file-ignores` de ruff, `exclude_also`
  de coverage, `ignore_imports` de import-linter), en notebooks ni las que escribe un script; tampoco ve pruebas
  borradas. Eso se revisa en el PR.
- pytest corre la suite completa: en repos con pruebas lentas conviene acotarla (pendiente).
- No es una barrera de seguridad; eso va en reglas `deny` y permisos.

## Probar
    python3 -m pytest tests -q                     # pruebas de los hooks
    claude --plugin-dir ./plugins/calidad-python   # sesión con el plugin cargado
