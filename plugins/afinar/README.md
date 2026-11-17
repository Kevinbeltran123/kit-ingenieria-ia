# afinar

Ayuda a escribir mejores pedidos para los agentes en cualquier repo del kit.

## Qué trae
| Pieza | Qué hace |
| --- | --- |
| Skill `afinar` (`/afinar <pedido>`) | Reescribe el pedido con meta, comprobación ejecutable, límites, contexto del repo, entrega, tamaño (una sesión o carriles de la flota), riesgos y supuestos; pregunta como mucho dos cosas. También revisa un pedido ya escrito y, después de un fallo, propone el pedido corregido y la causa |
| `scripts/revisar.py` | Reglas simples, sin modelo: dice si a un pedido le falta comprobación, límites o referencias, si tiene palabras vagas y si toca algo delicado |
| Hook `UserPromptSubmit` | En pedidos de trabajo sin comprobación o con riesgos, agrega una nota para que el agente proponga la comprobación (o pregunte una vez) y confirme lo irreversible. No bloquea; `AFINAR_AVISO=0` lo apaga |

## Cuándo usarlo
- Antes de una tarea de más de unos minutos, o antes de mandarla a la flota (el resultado sirve como brief).
- Cuando un agente entregó otra cosa: `/afinar ¿por qué falló esto? <pedido y lo que pasó>`.

## Límites
- `revisar.py` es heurístico: busca señales (comandos, «no toques», nombres de archivo). Un hallazgo es una pista.
- No ejecuta la tarea ni escribe reglas en `CLAUDE.md` sin el sí de la persona.

/plugin install afinar --marketplace Kevinbeltran123/kit-ingenieria-ia
