---
name: explicar-resultado
description: Explica un resultado de modelo o de datos (un experimento, una evaluación, el cierre de una tarea) afirmación por afirmación, con cada cifra tomada del archivo de salida y no escrita a mano, contra qué se midió, en cuántos lotes y qué no se comprobó. Al redactarla salen errores que pasaron desapercibidos (fuga, etiquetas mal unidas, cifras contra una referencia débil). Úsala al terminar un experimento o una tarea grande que no es solo código, antes de reportar una métrica o de dar una tarea por entregada, o cuando pidan "explícame el resultado", "qué significa este número", "explain this result", "experiment report".
---

# explicar-resultado

`explicar-cambios` (plugin explicador) explica el código línea por línea. Esta skill hace lo mismo con un
resultado: obliga a decir qué se afirma, con qué cifra, medida contra qué y con qué alcance. Las cifras salen
del archivo que escribió el experimento, así la explicación no puede mostrar un número inventado.

## Pasos

1. El experimento deja sus métricas en `runs/<id>/resultado.json`: un objeto JSON, anidado si hace falta, con
   números en las hojas (`{"auc": {"media": 0.87, "por_lote": {"3-2008": 0.83}}, "n_lotes": 11}`). Lo escribe
   el código, no tú. Si el experimento no lo deja, arréglalo en el código y vuelve a correrlo.

2. Crea la plantilla:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/explicar-resultado/scripts/resultado.py" plantilla runs/<id>
   ```
   Escribe `runs/<id>/explicacion.json` con los campos vacíos y la lista de claves disponibles.

3. Completa `explicacion.json`:
   - `titulo` y `pregunta`: qué se quería saber, en una frase cada uno.
   - `como_se_hizo`: datos usados (qué vuelos, qué fechas), método y el comando que lo reproduce.
   - `afirmaciones`: una por cada cosa que el resultado permite decir. En cada una:
     - `texto`: la afirmación, con `{valor}` donde va la cifra. No escribas el número.
     - `clave`: la ruta de la cifra en `resultado.json`, con puntos (`auc.media`).
     - `referencia`: contra qué se midió: `campo`, `experto`, `etiqueta_historica` o `ninguna`.
     - `alcance`: `{"unidades": <n>, "grupos": <n>, "descripcion": "8.980 palmas de 11 lotes, un vuelo por lote"}`.
     - `no_comprobado`: lista de lo que esta afirmación no cubre (lotes, fechas, sensores, clases). No puede
       quedar vacía: siempre hay algo fuera.
   - `alertas`: lo raro que veas al explicar, con el mismo esquema de `explicar-cambios`:
     `{"tipo": "bug" | "riesgo" | "duda", "estado": "abierta" | "resuelta" | "descartada", "texto": "...", "motivo": "..."}`.
     Un error solo se descarta si lo decidió la persona: `motivo` dice quién y por qué.
   - `siguiente`: qué habría que hacer para cerrar lo no comprobado.

4. Valida y arma la explicación:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/explicar-resultado/scripts/resultado.py" construir runs/<id>
   ```
   Si falta algo lo lista y sale con 1. Si todo está, escribe `runs/<id>/explicacion.md` con las cifras ya
   puestas y sale con 0. Sale con 2 si queda un `bug` abierto: corrígelo y vuelve a correr el experimento, o
   pregúntale a la persona.

5. Dale a la persona la ruta de `explicacion.md` y resume en dos líneas qué se puede afirmar y qué no.

## Preguntas que debes hacerte al escribir cada afirmación

Son las que destapan errores. Si alguna respuesta es "no sé", es una alerta de tipo `duda`.

- ¿La cifra se calculó sobre datos que el modelo no vio? ¿Lo verificó `verificar_division.py` (skill
  `division-sin-fuga`) o solo lo supongo?
- ¿La etiqueta corresponde a la misma unidad y a la misma fecha que la imagen? ¿Lo comprobé a la vista en
  algunos casos?
- ¿La referencia es fiable? Una cifra contra `etiqueta_historica` mide coincidencia con un registro, no
  acierto: el script lo marca y no deja llamarla desempeño.
- ¿Cuál es el peor grupo, y cuánto se aleja de la media?
- ¿Un método tonto (la media, una sola variable) da casi lo mismo?
- ¿Elegí el umbral, el modelo o las variables mirando estos mismos datos?
- ¿Cuántas unidades positivas hay de verdad en la muestra? Con pocas, el intervalo es ancho.

## Cuándo no aplica
- Cambios solo de código: usa `explicar-cambios`.
- Exploraciones rápidas que no se van a reportar ni a usar para decidir.

## Verificación
- `resultado.py construir` termina con `OK: runs/<id>/explicacion.md`.
- En `explicacion.md` no hay ninguna cifra que no esté en `resultado.json`.
- La sección "Lo que no se comprobó" tiene al menos una línea por afirmación.
