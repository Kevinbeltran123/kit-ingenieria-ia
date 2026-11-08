---
name: formular-modelo-optimizacion
description: Formula, implementa y verifica modelos de optimización (programación lineal, entera mixta, restricciones) con OR-Tools CP-SAT o HiGHS, con tabla de unidades, instancia mínima, verificador de factibilidad independiente y pruebas. Úsala cuando haya que asignar, planificar, programar, rutear o repartir recursos (cosecha, cuadrillas, rutas, turnos, inventario) o cuando alguien pida "optimizar", "un modelo de optimización", "MILP", "linear programming", "scheduling", "vehicle routing", "OR-Tools", "Pyomo", "HiGHS".
---

# Formular un modelo de optimización

Un modelo que el solver resuelve no es un modelo correcto. Los errores típicos al formular con IA son silenciosos: una unidad mezclada, una restricción con el signo al revés o un objetivo que premia lo contrario. Por eso este flujo separa **quién resuelve** (el solver) de **quién juzga** (un verificador escrito aparte, que no comparte código con el modelo).

Sigue los pasos en orden. No pases al siguiente sin que el anterior esté verificado.

## 1. Especificación en lenguaje natural

Escribe, antes de cualquier código, un bloque `ESPECIFICACION.md` (o docstring del módulo) con:

- **Decisión**: qué se decide (p. ej., "qué cuadrilla cosecha cada lote hoy").
- **Conjuntos**: índices (cuadrillas `C`, lotes `L`, días `D`).
- **Parámetros**: datos de entrada, cada uno con unidad y fuente.
- **Variables**: tipo (binaria, entera, continua) y cotas.
- **Restricciones**: una por regla de negocio, en palabras y en fórmula.
- **Objetivo**: qué se minimiza o maximiza y en qué unidad.
- **Supuestos y fuera de alcance**.

Si una regla de negocio no está clara, pregunta. No la inventes.

## 2. Tabla de unidades

| Parámetro | Símbolo | Unidad | Rango esperado | Fuente |
|---|---|---|---|---|
| Capacidad de la cuadrilla | `cap[c]` | kg RFF/día | 2.000–8.000 | Jefe de campo |
| Fruta lista en el lote | `dem[l]` | kg RFF | 0–20.000 | Censo de racimos |

Comprueba que **cada término de cada restricción** tenga la misma unidad en ambos lados y que el objetivo sume cosas comparables (no sumes km con horas sin un peso explícito y documentado). En CP-SAT todos los coeficientes son enteros: escala a la unidad entera más pequeña que tenga sentido (kg en vez de t, minutos en vez de horas) y anótalo en la tabla.

## 3. Elegir enfoque y solver

Ver `references/elegir-solver.md`. Resumen:

- **Asignación, turnos, secuencias, restricciones lógicas** (todos binarios/enteros): **OR-Tools CP-SAT**.
- **LP o MILP con muchas variables continuas** (mezclas, flujos, planificación con cantidades): **HiGHS** (vía `highspy`, Pyomo o PuLP).
- **Rutas de vehículos** con ventanas o capacidades: **OR-Tools routing**.
- **Heurística** solo si el exacto no escala en el tiempo disponible, y siempre comparada contra el exacto en instancias pequeñas.
- Gurobi solo si la empresa tiene licencia; su MCP envía el modelo a la nube de Gurobi, así que necesita aprobación antes de usarlo con datos reales.

Antes de escribir código con una API, consulta su documentación vigente (Context7), sobre todo OR-Tools, que cambia nombres entre versiones.

## 4. Instancia mínima resoluble a mano

Crea una instancia de 2 a 4 elementos por conjunto cuyo óptimo puedas calcular a mano o por fuerza bruta. Guarda el óptimo esperado en la prueba. Si el modelo no lo reproduce, el error está en la formulación, no en los datos.

## 5. Verificador de factibilidad independiente

Escribe `verificar(instancia, solucion) -> list[str]` en un módulo aparte:

- No importa nada del modelo ni del solver.
- Comprueba cada regla de negocio de la especificación, una por una, sobre la solución.
- Recalcula el objetivo desde cero y lo compara con el que reporta el solver.
- Devuelve la lista de violaciones legibles (vacía = factible).

Ejemplo completo: `scripts/verificar_cuadrillas.py` junto a `scripts/ejemplo_cuadrillas.py`.

## 6. Casos borde e infactibles a propósito

Como mínimo, pruebas para:

- Todo en cero (sin demanda): la solución debe ser trivial y factible.
- Cotas al máximo (capacidad exactamente igual a la demanda).
- **Una instancia infactible a propósito**: el código debe reportarla como infactible, no devolver una solución basura. En MILP, diagnostica con IIS (Gurobi) o relajando restricciones con variables de holgura penalizadas para encontrar cuál choca.
- Datos inválidos (negativos, unidades fuera de rango): fallan en la validación de entrada, antes del solver.

## 7. Pruebas con pytest

- Prueba de óptimo conocido en la instancia mínima (paso 4).
- Prueba de que **toda** solución que devuelve el modelo pasa el verificador.
- Prueba de fuerza bruta: en instancias pequeñas aleatorias (semilla fija), el objetivo del modelo es igual al mejor objetivo por enumeración.
- Pruebas de los casos borde (paso 6).

## 8. Escalado y tiempos

Aumenta el tamaño gradualmente (10, 100, 1.000 lotes) y registra en una tabla: tamaño, tiempo, estado (`OPTIMAL`/`FEASIBLE`), gap. Pon siempre un límite de tiempo (`max_time_in_seconds` en CP-SAT, `time_limit` en HiGHS) y trata `FEASIBLE` con gap como una respuesta válida pero no óptima, que hay que comunicar como tal. Si no escala: simetrías (rompe con orden), cotas más ajustadas, descomposición por zona o día, y solo después heurísticas.

## Plantillas para palma de aceite

`references/plantillas-agro.md` trae formulaciones de partida para planificación de rondas de cosecha por lote, asignación de cuadrillas y ruteo de recolección de fruto. Los parámetros agronómicos (frecuencia de ronda, rendimiento por jornal, tiempos de transporte, madurez) son ejemplos y **los debe validar la empresa** antes de usarlos.

## Cómo verificar que esta skill se cumplió

- Existe la especificación con tabla de unidades.
- Existe un verificador que no importa el modelo.
- `pytest` pasa e incluye: óptimo conocido, verificador sobre las soluciones, fuerza bruta, al menos un caso infactible.
- Hay límite de tiempo configurado y el estado del solver se maneja explícitamente (óptimo, factible, infactible, sin solución en el tiempo).
