# Convenciones del kit

Reglas para todo lo que se agregue a este marketplace.

## Estructura de un plugin
```
plugins/<nombre>/
├── .claude-plugin/plugin.json   # name, version (semver), description, author {name: "Kevin Beltran"}, license MIT
├── skills/<skill>/SKILL.md      # + scripts/ y references/ si hacen falta
├── hooks/hooks.json             # + scripts de hooks
├── tests/                       # pytest para todo script o hook
└── README.md                    # qué trae, cuándo usarlo, límites
```
Ejemplo de referencia: `plugins/calidad-python/`.

## Skills
- Frontmatter portable: `name` (kebab-case, ≤64, sin "claude"/"anthropic"), `description` (qué hace + cuándo usarla, ≤1.000 caracteres, en español con términos de búsqueda en inglés si ayudan a activarla).
- `SKILL.md` < 500 líneas; detalle en `references/` a un solo nivel.
- Escritas en español, directas, con pasos verificables. Nada de MAYÚSCULAS ni "IMPORTANT".
- Cada skill dice **cómo verificar** que se cumplió (comando, script o checklist).
- Lo determinista va en scripts (`scripts/*.py`, solo biblioteca estándar o PEP 723 con `uv run`), no en prosa.
- No duplicar: si otra skill del kit cubre algo, referenciarla por nombre.
- Pragmatismo (KARPATHY.md): mínimo necesario, sin abstracciones especulativas; decir también cuándo NO aplicar algo.

## Hooks
- Python 3 de biblioteca estándar, invocado como `python3 -I "${CLAUDE_PLUGIN_ROOT}/hooks/<script>.py"`.
- Compatibles con Python 3.9, el `python3` de macOS y de Amazon Linux 2023: `from __future__ import annotations`
  después del docstring y nada de 3.10+ en tiempo de ejecución (`match`, `tomllib`...). Vale también para
  `scripts/` de las skills y `bin/`. Lo vigila `bin/tests/test_compatibilidad.py`.
- Exit 2 + stderr para bloquear o devolver el error a Claude; exit 0 si no aplica. Cualquier otro código
  (por ejemplo, un error al cargar el archivo) Claude Code lo trata como no bloqueante: la acción sigue.
- Fallar abierto (exit 0) ante entradas raras, salvo en barreras de seguridad, que fallan cerrado: además de
  salir con 2 ante un error interno, declaran `"onFailure": "block"` en hooks.json para que Claude Code
  bloquee si el hook ni siquiera arranca.
- Pruebas con pytest que alimentan JSON por stdin (ver `plugins/calidad-python/tests/test_hooks.py`).

## Verificación antes de dar algo por terminado
1. `python3 -m pytest plugins/<nombre>/tests -q` pasa.
2. `claude plugin validate .` pasa desde la raíz del kit.
3. Nada instalado globalmente, nada fuera de la carpeta del kit, sin operaciones de git.

## Terceros
- Siempre fijados por `sha` de 40 caracteres en `marketplace.json`.
- Auditados con la checklist de `investigacion/04-pruebas-revision-seguridad.md` antes de entrar; resultado en `terceros/AUDITORIA.md`.
