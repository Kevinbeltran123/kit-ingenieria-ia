# flota

Coordinador de varios trabajadores (Claude Code y Codex) que corren en carriles de [herdr](https://herdr.dev), con un
tablero interactivo y avisos en cmux. Adaptado de la skill «coordinator» de copybook.page (contrato de líneas READY,
puerta por tandas, reglas de permiso) y reescrito con lo que se comprobó en este Mac.

## Qué trae
| Pieza | Qué hace |
| --- | --- |
| Skill `flota` | El rol de coordinador: partir la meta en carriles, briefs, modelos, permisos, puerta, envío, informe |
| `scripts/carril.py` | Prepara la corrida, inicia un carril (worktree + agente + diálogos de confianza + brief), le escribe, hace el commit de Codex, cierra |
| `scripts/vigilar.py` | Sale cuando hay una entrega READY nueva, la puerta avanza o un carril para sin entregar |
| `scripts/pesado.py` | Turnos compartidos para builds y suites pesadas |
| `scripts/tablero.py` + `tablero.html` | Tablero web local (columnas de flujo, línea de tiempo, pantalla en vivo de cada carril, escribirle, responder diálogos, enfocar en herdr, paleta Alt+F) y vista de terminal |
| `herdr/` | Plugin de herdr `kit.flota.puente`: registra cada cambio de estado (para la línea de tiempo) y lo refleja en cmux |

## Requisitos
- herdr 0.9 o más (`brew install herdr`), Claude Code y, si usas carriles Codex, Codex CLI con sesión iniciada.
- cmux es opcional: sin él, el tablero se abre en el navegador y no hay avisos en la barra.

## Instalar
1. El plugin del kit, en el repo donde coordinas (alcance de proyecto), o para una sola sesión:
   `claude --plugin-dir <kit>/plugins/flota`.
2. El puente de herdr, una vez por usuario: `herdr plugin link <kit>/plugins/flota/herdr`. Opcional:
   `<config del plugin>/config.json` con `{"avisos": "sin-claude"}` si cmux ya te avisa de Claude por sus hooks.
3. Si Claude Code corre con sandbox en el repo, agrega el socket de la sesión en `.claude/settings.local.json`:
   `"sandbox": {"network": {"allowUnixSockets": ["~/.config/herdr/sessions/<sesión>/herdr.sock"]}}`.

## Usar
Abre la sesión de herdr (`herdr --session <sesión>`) y, en otra terminal, el tablero:
`python3 -I <kit>/plugins/flota/skills/flota/scripts/tablero.py --run ../<repo>-flota --sesion <sesión> --repo . --abrir`.
Luego pídele a Claude: «Eres el coordinador de esta corrida. Meta: <qué es terminar y cómo se comprueba>. Usa la flota
con la sesión <sesión>». Empieza con un carril Claude y uno Codex con una tarea de una línea.

## Límites
- Codex en el nivel `auto` no puede hacer commit (su sandbox protege `.git`): el commit lo hace el coordinador.
- herdr detecta el estado leyendo la pantalla; un diálogo desconocido puede verse como `idle`. Por eso el contrato es la
  línea READY en un archivo, no el estado.
- El tablero escucha solo en 127.0.0.1 y pide el token de la URL; no lo expongas por otra vía.
- No reemplaza la revisión: una entrega es una afirmación hasta que el coordinador revisa el diff y la evidencia.

/plugin install flota --marketplace Kevinbeltran123/kit-ingenieria-ia
