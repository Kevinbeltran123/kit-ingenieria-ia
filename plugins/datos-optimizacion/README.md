# datos-optimizacion

Skills de ingeniería de datos y optimización. Se cargan solo cuando la tarea las necesita.

| Skill | Para qué |
|---|---|
| `formular-modelo-optimizacion` | Pasar de un problema de negocio a un modelo OR-Tools/HiGHS verificado: especificación, tabla de unidades, instancia mínima, verificador independiente, casos infactibles, pruebas y escalado. Trae plantillas para palma (cosecha, cuadrillas, rutas) y un ejemplo ejecutable. |
| `ingesta-idempotente` | Pipelines que se pueden re-ejecutar sin duplicar: merge por clave natural, watermarks con solape, cuarentena, linaje, pruebas de idempotencia. |
| `contratos-datos` | Pandera y Pydantic en los bordes, evolución de esquemas y pruebas de datos. |
| `migraciones-alembic` | SQLAlchemy 2 tipado y migraciones revisadas, reversibles y sin downtime en Postgres. |

## Ejemplo de optimización

    cd skills/formular-modelo-optimizacion/scripts
    uv run ejemplo_cuadrillas.py              # instancia mínima, óptimo 800 m
    python3 verificar_cuadrillas.py inst.json sol.json

## Límites

- Los parámetros agronómicos de las plantillas son ilustrativos: los debe validar la empresa.
- No incluye plugins de orquestadores (dbt, Dagster, Airflow): se agregan por repo según lo que use la empresa.
- El acceso seguro a bases de datos de producción (rol de solo lectura, bloqueo de DDL/DML) está en el plugin `barreras`.

## Pruebas

    python3 -m pytest tests -q                                   # verificador (el modelo se salta sin OR-Tools)
    uv run --with ortools --with pytest python -m pytest tests -q   # todo, incluido el modelo contra fuerza bruta
