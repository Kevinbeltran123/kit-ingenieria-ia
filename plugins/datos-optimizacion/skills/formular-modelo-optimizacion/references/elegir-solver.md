# Elegir enfoque y solver

| Problema | Enfoque | Herramienta por defecto | Notas |
|---|---|---|---|
| Asignación (tareas↔personas, lotes↔cuadrillas) | Programación con restricciones / entera | OR-Tools CP-SAT | Coeficientes enteros. Muy bueno con restricciones lógicas (`add_implication`, `only_enforce_if`) |
| Turnos y calendarios (shift scheduling) | CP | OR-Tools CP-SAT | Variables de intervalo, `add_no_overlap` |
| Secuenciación con tiempos (job shop) | CP | OR-Tools CP-SAT | Intervalos + precedencias |
| Mezclas, dietas, fertilización por dosis continuas | LP | HiGHS | Si todo es continuo, LP: rápido y con duales para sensibilidad |
| Planificación con cantidades + decisiones sí/no | MILP | HiGHS (Pyomo o highspy) | Si es grande y hay licencia, Gurobi |
| Flujo en red, transporte | LP / flujo de costo mínimo | OR-Tools `SimpleMinCostFlow` o HiGHS | Solución entera garantizada si los datos son enteros |
| Rutas con capacidad o ventanas (VRP, CVRP, VRPTW) | Metaheurística guiada | OR-Tools routing | No da prueba de optimalidad; fijar `time_limit` y comparar con cotas |
| Muy grande y con tiempo límite estricto | Heurística (greedy + búsqueda local) | Código propio | Comparar siempre contra el exacto en instancias chicas |
| Hiperparámetros de un modelo de ML | Optimización bayesiana | Optuna | No es investigación de operaciones; otra skill |

## Capa de modelado

- **Directo en la API** (`cp_model`, `highspy`): menos dependencias, más control. Bueno para un solo solver. En
  CP-SAT usa los nombres en snake_case (`new_bool_var`, `add`, `only_enforce_if`, `solver.value`), como el ejemplo
  del kit; los CamelCase viejos (`AddImplication`) siguen funcionando en OR-Tools 9.15, pero mezclarlos confunde.
- **Pyomo**: un mismo modelo para HiGHS, CBC, Gurobi. Útil si se espera cambiar de solver. Más lento al construir modelos enormes.
- **PuLP**: simple para MILP pequeños/medianos.
- **CVXPY**: problemas convexos (no MILP general).

## Estados que siempre hay que manejar

| Estado | CP-SAT | HiGHS | Qué hacer |
|---|---|---|---|
| Óptimo | `OPTIMAL` | `kOptimal` | Verificar y reportar |
| Factible, no probado óptimo | `FEASIBLE` | `kTimeLimit` con solución | Reportar gap |
| Infactible | `INFEASIBLE` | `kInfeasible` | Diagnosticar (holguras penalizadas, IIS) |
| Sin solución en el tiempo | `UNKNOWN` | `kTimeLimit` sin solución | Más tiempo, mejores cotas o descomposición |
| No acotado | no existe (los dominios son finitos) | `kUnbounded` o `kUnboundedOrInfeasible` | Falta una cota o una restricción; con `kUnboundedOrInfeasible` también puede ser infactible |
| Modelo mal construido | `MODEL_INVALID` | error | Bug de formulación |
