# herdr en una corrida de la flota

Probado con herdr 0.9.5, Claude Code 2.1.326 y Codex 0.169.0 el 2026-11-17. El binario instalado manda: ante una duda de
sintaxis, `herdr <grupo>` sin subcomando imprime la ayuda (nunca corras un subcomando que muta sin argumentos).

## Comandos que usa la flota
| Para | Comando |
| --- | --- |
| Ver agentes y su estado | `herdr --session S agent list` |
| Leer un carril | `herdr --session S agent read N --source recent-unwrapped --lines 120` (`visible` para un diálogo) |
| Por qué herdr cree que está en ese estado | `herdr --session S agent explain N` |
| Esperar a que termine | `herdr --session S agent wait N --timeout 600000` |
| Escribirle | `carril.py enviar` (usa `agent prompt --wait --until working`) |
| Teclas | `carril.py teclas` (`agent send-keys`; enter, esc, up, down, tab, ctrl+c, 1, 2, 3, y, n) |
| Enfocar en la TUI | `herdr --session S agent focus N` |
| Sesiones | `herdr session list`, `herdr session stop S` (solo la de tu corrida) |

`agent prompt --wait` observa estados, no turnos: un `idle` no prueba que terminó tu tarea. La prueba es la línea READY
más tu propia revisión. Un tiempo agotado no cancela nada ni prueba que el texto no llegó: lee el pane antes de reenviar.

## Estados
`working`, `blocked` (herdr reconoció un diálogo o una pregunta), `idle`, `done` (terminó y nadie lo ha visto),
`unknown`. Claude lo detecta herdr leyendo la pantalla (manifiesto `claude.toml`); igual Codex.

## Diálogos de arranque (los responde `carril.py iniciar`)
| Diálogo | Cómo lo ve herdr | Respuesta |
| --- | --- | --- |
| Claude: «Is this a project you ... trust?» | `blocked` | abajo + Enter («Yes, I trust this folder») |
| Codex: «Trust this folder?» | `idle` (detección equivocada) | Enter («Trust and continue») |
| Claude con bypassPermissions: confirmación | `blocked` | ninguna: la confirma la persona en herdr |
| Codex: «N hooks need review» | variable | ninguna: que la persona revise los hooks y confíe en una sesión de Codex |

Por eso `aceptar_dialogos` lee la pantalla además del estado. Cada worktree nuevo es una carpeta nueva: los diálogos de
confianza aparecen en cada carril.

## Trampas conocidas
- **Codex y .git**: con `workspace-write`, Codex no puede crear `index.lock` (falla con «Operation not permitted»),
  incluso con `--add-dir` sobre el `.git` del repo. Por eso en `auto` el commit lo hace el coordinador.
- **Modelo de Codex**: con cuenta de ChatGPT, un modelo fuera de `~/.codex/models_cache.json` falla al primer
  prompt («model is not supported» o «doesn't include»), no al arrancar. Fija `FLOTA_MODELO_CODEX`.
- **Nombres**: `[a-z][a-z0-9_-]{0,31}`, únicos entre los agentes vivos de un servidor; `agent_name_taken` = reúsalo o
  usa otro nombre.
- **Sandbox de Claude Code**: el CLI de herdr habla por el socket `~/.config/herdr/sessions/<S>/herdr.sock`. Si tu sesión
  corre con sandbox, el repo necesita en `.claude/settings.local.json` el socket en
  `sandbox.network.allowUnixSockets` (o `herdr` en `sandbox.excludedCommands`).
- **Servidor**: nunca `herdr server stop` ni matar el proceso principal: detiene los panes de todas las corridas. Para
  experimentos, una sesión con nombre propio.
- **Reinicio del servidor**: los procesos no sobreviven; herdr restaura el diseño. Retoma un Claude con
  `--resume <sesion_agente>` (está en `carriles.json`) y vuelve a mandarle el brief y su posición en la cola.
