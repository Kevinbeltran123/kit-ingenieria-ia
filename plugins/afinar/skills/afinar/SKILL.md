---
name: afinar
description: "Convierte un pedido suelto en un prompt claro para un agente (meta, comprobación, límites, contexto del repo, entrega, tamaño y riesgos), señala lo que falta o es ambiguo y, después de un intento fallido, propone el pedido corregido. Úsala cuando la persona diga «afina», «mejora este prompt», «revisa este pedido», «arma el brief», «por qué falló esto», «improve prompt», «refine», «brief», o antes de mandar trabajo grande a la flota. No la uses para preguntas simples ni para ejecutar la tarea: afinar no hace el trabajo."
---

# Afinar

Un buen pedido le dice al agente qué es terminar, cómo se demuestra y qué no tocar. Esta skill lo arma a partir de lo
que escribió la persona y de lo que ya dice el repo, sin inventar requisitos. No ejecuta la tarea.

`S` = carpeta `scripts/` de esta skill. `python3 -I S/revisar.py` lee un pedido por stdin y devuelve en JSON lo que le
falta (comprobación, límites, referencias, palabras vagas, riesgos).

## Pasos
1. **Revisa el pedido tal cual**: `printf '%s' "<pedido>" | python3 -I S/revisar.py`. Anota los hallazgos.
2. **Lee el contexto mínimo del repo** (no más de unos minutos):
   - `CLAUDE.md` o `AGENTS.md`: comandos de prueba, tipos y lint, lo que «No hacer», convenciones.
   - Recetas disponibles: `justfile`, `package.json` (scripts), `Makefile`, `pyproject.toml`.
   - Dónde vive lo que se pide: busca los nombres del pedido en el código (CodeGraph si el repo tiene `.codegraph/`,
     si no grep) y quédate con 1 a 5 archivos o símbolos.
   - Estado del trabajo: `ESTADO.md`, la rama actual y si hay cambios sin commit.
   - Política de modelos del proyecto: una sección `## Modelos` en `CLAUDE.md` o en `<repo>-flota/STATE.md`. Manda
     sobre los valores por defecto: si el proyecto pide razonamiento profundo (por ejemplo Fable para planear, diseñar
     experimentos o revisar), recomiéndalo así y nunca bajes de modelo o esfuerzo para ahorrar cuota.
3. **Escribe el pedido afinado** con esta forma, en el idioma de la persona:
   ```
   Meta: <qué queda hecho, visto por quien lo usa; una o dos frases>
   Comprobación: <comando> → <resultado esperado>   (una o más; ejecutables, no «que funcione»)
   Límites: Sí: <archivos o módulos>. No: <lo que no se toca; lo de «No hacer» que aplique>
   Contexto: <archivos y símbolos relevantes, decisiones previas, enlaces que dio la persona>
   Entrega: <qué devolver: diff y explicación, PR, informe, resultado.json...>
   Tamaño: <una sesión> o <flota con N carriles: uno por archivo o módulo>, con modelo y esfuerzo por parte
   Riesgos: <lo que puede salir mal y cómo se notaría; acciones que requieren confirmación>
   Supuestos: <lo que decidiste sin preguntar, para que la persona lo corrija si no es así>
   ```
4. **Pregunta solo lo que cambia el resultado y no se puede deducir**: como mucho dos preguntas, cada una con tu
   recomendación. Todo lo demás va en «Supuestos».
5. **Vuelve a revisar** el pedido afinado con `revisar.py`: debe salir `"completo": true`. Si un hallazgo sigue, corrígelo
   o explica en «Supuestos» por qué no aplica.
6. **Ofrece el siguiente paso**: ejecutarlo ya en esta sesión, guardarlo como brief de la flota
   (`<repo>-flota/briefs/<nombre>.md`, con la última línea `<NOMBRE>-READY <rama> <head>` que pide la skill `flota`), o
   dejarlo para copiar. No ejecutes nada sin que la persona lo elija.

## Revisar un pedido ya escrito
Si la persona solo pide revisión («¿está bien este prompt?»), no lo reescribas entero: corre `revisar.py`, di los dos o
tres problemas que más cambian el resultado y el arreglo más pequeño para cada uno. Permite «está bien así».

## Después de un fallo
Cuando un agente hizo otra cosa, se atascó o entregó algo que no servía:
1. Junta el pedido original y lo que pasó (la entrega, el error, el diff o lo que dijo la persona).
2. Clasifica la causa: faltaba la comprobación, faltaban límites, el contexto apuntaba a otro sitio, la meta era
   ambigua, la tarea era demasiado grande para una sesión, o el fallo fue de la herramienta y no del pedido.
3. Devuelve el pedido corregido (con la forma del paso 3) y una línea con la causa.
4. Si el mismo tropiezo ya pasó antes, propón convertirlo en regla con `/correct` (plugin `flujo`) o una línea en
   `CLAUDE.md`; no lo escribas sin el sí de la persona.

## Aviso automático
El hook del plugin revisa cada pedido de trabajo de ocho palabras o más. Si no dice cómo se comprueba, o menciona push,
producción, borrados, migraciones o credenciales, agrega una nota para que el agente proponga la comprobación (o haga
una sola pregunta) y confirme antes de lo irreversible. No bloquea nada; se apaga con `AFINAR_AVISO=0`.

## Cómo verificar que se cumplió
- El pedido afinado tiene las ocho secciones y `revisar.py` lo da por `"completo": true`.
- Cada comprobación es un comando que existe en el repo (receta, script o prueba), no una intención.
- Las preguntas son dos o menos y cada una trae recomendación; lo demás está en «Supuestos».
- El modelo y el esfuerzo sugeridos respetan la sección `## Modelos` del proyecto, si existe.
