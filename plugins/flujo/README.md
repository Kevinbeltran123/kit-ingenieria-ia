# flujo

Selección de 5 skills de [obra/superpowers](https://github.com/obra/superpowers) v7.0.2, sin hooks ni comandos (decisión: solo skills sueltas, por costo de contexto y control), y `correct` de [pstack](https://github.com/cursor/plugins/tree/6b0300214a09fd6029cfb7077043125758cd1fd2/harness/pstack/claude-code).

| Skill | Cuándo se activa |
|---|---|
| brainstorming | Algo nuevo y no trivial donde no está claro qué se quiere o por qué |
| writing-plans | Hay spec o requisitos de una tarea de varios pasos, antes de tocar código |
| test-driven-development | Implementar cualquier feature o bugfix |
| systematic-debugging | Cualquier bug, prueba fallida o comportamiento inesperado |
| verification-before-completion | Antes de decir que algo está terminado, arreglado o pasando |
| correct | Solo con `/correct`, cuando corregiste al agente por el mismo error: lo vuelve imposible con arquitectura, tipos, una regla de lint o una prueba (en ese orden) y lleva una tabla de reglas en el CLAUDE.md |

Se complementa con el hook de `calidad-python`: la skill pide verificar; el hook lo obliga.
Origen, cambios y cómo actualizar: `ORIGEN.md`.
