---
name: explicar-cambios
description: Explica un cambio de código línea por línea en un HTML local que no usa internet (el código a un lado y una terminal que lo explica al otro), para que la persona entienda qué se hizo y por qué. Úsala antes de abrir un PR (el hook del plugin lo exige), al terminar una feature o un arreglo, o cuando pidan "explícame el cambio", "qué hiciste", "explain this diff", "walk me through the code".
---

# explicar-cambios

La persona revisa código que escribió la IA. Por cada cambio, esta skill le deja una página que se
recorre línea por línea: qué hace cada método, qué hace cada línea y por qué cambió. Al explicarlo
todo también salen a la luz errores antes del PR: márcalos.

## Pasos

1. Desde la raíz del repo, saca los datos de git:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/explicar-cambios/scripts/recolectar.py"
   ```
   - Compara la rama actual con la principal. Otra base: `--base <rama o commit>`. Para explicar
     algo que todavía no tiene commit: `--sin-commit` (para el PR sí hace falta el commit).
   - Para explicar un solo commit (uno viejo o de otra persona): `--commit <ref>`. Queda en
     `.explicaciones/commits/<commit>/` y en el paso 3 se pasa esa carpeta a `construir.py`.
   - Escribe `.explicaciones/<rama>/datos.json` (no se toca) y `textos.json` (lo completas tú).
     `.explicaciones/` queda fuera de git por `.git/info/exclude`.

2. Lee `textos.json` y completa todos los campos vacíos. Cada paso trae `codigo` (las líneas reales,
   solo para leer) y las listas `lineas_nuevas` y `lineas_borradas` con los números que necesitan nota.
   - `titulo`: qué hace el cambio, en una frase corta.
   - `resumen.problema`: qué pasaba antes o qué faltaba.
   - `resumen.solucion`: qué hace el código ahora, sin detalles de implementación.
   - `resumen.como_se_probo`: los comandos que corriste y su resultado real ("4 pruebas nuevas; pasan
     19 de 19"). Si algo no lo probaste, dilo.
   - `resumen.decisiones` y `resumen.pendiente` (opcionales): alternativas descartadas y por qué; lo
     que queda por hacer o vigilar.
   - En cada paso:
     - `titulo`: qué hace este bloque, en pocas palabras.
     - `explicacion`: qué hace el método o bloque completo y por qué cambió, en 2 a 5 frases. Si el
       método es nuevo, di qué recibe, qué devuelve y quién lo usa.
     - `notas`: una por cada número de `lineas_nuevas`. Di qué hace esa línea y para qué sirve, sin
       copiarla. Usa un rango (`"61-64"`) solo para líneas que hacen una sola cosa juntas, como un
       bloque de imports o un diccionario.
     - `notas_borradas`: por qué se quitó cada línea o bloque borrado (números de `lineas_borradas`).
     - `alerta`: `null`, o un objeto si al explicar ves algo que puede fallar (ver abajo).

3. Arma el HTML:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/explicar-cambios/scripts/construir.py"
   ```
   Si falta algo, lista qué (paso y líneas) y sale con 1: complétalo y vuelve a correrlo.
   Con `--abrir` además abre la página en el navegador.

4. Dale a la persona la ruta del HTML y resume en dos líneas qué cambió. Todas las explicaciones del
   repo quedan en `.explicaciones/index.html`.

## Cómo escribir las explicaciones
- Escribe para alguien que lee ese código por primera vez: español claro, frases cortas, voz activa.
- Explica el porqué además del qué: "guarda la cuenta antes de salir para que el siguiente intento
  la lea" dice más que "escribe el contador".
- Si usas un término técnico (idempotente, merge-base, código de salida 2), explícalo en pocas
  palabras la primera vez que aparece.
- Nombra las cosas como están en el código (funciones, variables, archivos) para que se puedan buscar.
- No inventes: si no sabes por qué algo es así, dilo en la nota o márcalo como `duda`.

## Alertas: errores que aparecen al explicar
Al recorrer el código línea por línea vas a notar cosas raras. No las escondas:
- `{"tipo": "bug", "estado": "abierta", "texto": "..."}`: algo que probablemente está mal. Corrígelo
  antes de abrir el PR y vuelve a generar la explicación, o pregúntale a la persona. El hook no deja
  abrir el PR con errores abiertos.
- `{"tipo": "riesgo", ...}`: funciona, pero puede dar problemas (rendimiento, casos borde, seguridad).
- `{"tipo": "duda", ...}`: algo que la persona debería confirmar.
- `estado`: `abierta`; `resuelta` si este mismo cambio lo corrige; `descartada` con `"motivo"`. Un
  error solo se descarta si la persona lo decidió: escribe en `motivo` quién y por qué.

## Verificación
- `construir.py` termina con `OK: .explicaciones/<rama>/<fecha>-<commit>.html` y no lista faltantes.
- Para el PR, la explicación debe ser del commit actual. Si haces otro commit, vuelve a correr los dos
  scripts; tus textos anteriores quedan en `textos.anterior.json` para reutilizar lo que no cambió.

## Cuándo no aplica
- Cambios solo en archivos generados (lockfiles, binarios): `recolectar.py` los omite y lo dice.
- Si la persona quiere saltarse la explicación de un PR, lo decide ella: `EXPLICADOR_DESACTIVAR=1` al
  lanzar Claude Code, o `{"desactivar": true}` en `.claude/explicador.json`. No lo desactives por tu cuenta.
