# Plantillas de modelos para palma de aceite

Formulaciones de partida. **Los parámetros agronómicos son ilustrativos y los debe validar la empresa** (agronomía, jefes de campo, Cenipalma). No están verificados.

## 1. Planificación de rondas de cosecha por lote

**Decisión:** qué lotes se cosechan cada día del horizonte.

- Conjuntos: lotes `L`, días `D` (p. ej., 14 días).
- Parámetros:
  - `ronda_max[l]` (días): máximo de días entre cosechas del lote para no perder fruta sobremadura. *Ejemplo: 10–15 días; validar.*
  - `ultima[l]` (día): última cosecha antes del horizonte.
  - `kg[l]` (kg RFF por ronda): estimado por censo de racimos.
  - `cap_dia[d]` (kg RFF/día): capacidad total de cosecha (cuadrillas disponibles) y de recepción en planta extractora.
- Variables: `x[l,d] ∈ {0,1}` = se cosecha el lote `l` el día `d`.
- Restricciones:
  - Ventana de ronda: en toda ventana de `ronda_max[l]` días consecutivos hay al menos una cosecha del lote (empezando a contar desde `ultima[l]`).
  - Capacidad: `Σ_l kg[l]·x[l,d] ≤ cap_dia[d]` para cada día.
  - Opcional, espaciamiento mínimo: no cosechar el mismo lote dos veces en menos de `ronda_min[l]` días.
- Objetivo: minimizar la desviación de la carga diaria respecto al promedio (cosecha pareja para la planta), o minimizar la fruta en riesgo (días por encima de un umbral).
- Solver: CP-SAT (todo binario, ventanas = restricciones de suma sobre ventanas deslizantes).

## 2. Asignación de cuadrillas a lotes

**Decisión:** qué cuadrilla cosecha cada lote hoy. Ejemplo ejecutable: `scripts/ejemplo_cuadrillas.py`.

- Conjuntos: cuadrillas `C`, lotes del día `L`.
- Parámetros:
  - `cap[c]` (kg RFF/día): rendimiento de la cuadrilla. *Ejemplo: depende de cosecheros, altura de la palma y topografía; validar.*
  - `kg[l]` (kg RFF): fruta lista en el lote.
  - `dist[c,l]` (m): distancia del campamento de la cuadrilla al lote.
- Variables: `x[c,l] ∈ {0,1}`.
- Restricciones:
  - Cada lote lo cosecha exactamente una cuadrilla: `Σ_c x[c,l] = 1`.
  - Capacidad: `Σ_l kg[l]·x[c,l] ≤ cap[c]`.
  - Opcional: habilidades (lotes de palma alta solo con cuadrillas con malayo/cuchillo largo).
- Objetivo: minimizar `Σ dist[c,l]·x[c,l]` (m recorridos).
- Variante con lotes divisibles (varias cuadrillas por lote): variables continuas de kg asignados → MILP con HiGHS.

## 3. Ruteo de recolección de fruto (RFF)

**Decisión:** ruta de cada vehículo (tractor con vagón, camión) para recoger la fruta de los centros de acopio y llevarla a la planta.

- Nodos: planta extractora (depósito) y centros de acopio con fruta del día.
- Parámetros:
  - `kg[i]` (kg RFF) en cada centro.
  - `cap_veh[v]` (kg).
  - `t[i,j]` (min) tiempo de viaje por la red de vías internas.
  - Ventanas de tiempo opcionales: la fruta debe llegar a la planta antes de X horas desde el corte (la calidad del aceite cae con la demora). *Validar el límite con la empresa.*
- Modelo: CVRP o VRPTW con OR-Tools routing (`RoutingModel`, dimensión de capacidad, dimensión de tiempo).
- Objetivo: minimizar tiempo total o número de vehículos y luego tiempo.
- Verificador: cada centro visitado una vez, capacidad por ruta, ventanas cumplidas, tiempo recalculado desde la matriz.

## Datos que hay que pedir a la empresa

- Censo de racimos o estimación de kg por lote y frecuencia de actualización.
- Rendimiento real de cuadrillas (histórico de kg/jornal por tipo de lote).
- Matriz de tiempos o red de vías (GIS) y estado de vías en invierno.
- Reglas de la planta extractora: horario de recepción, capacidad diaria, límite de horas desde el corte.
