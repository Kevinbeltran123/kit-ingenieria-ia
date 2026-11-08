---
name: contratos-datos
description: Define y hace cumplir contratos de datos en los bordes del sistema con Pandera (DataFrames de Polars o pandas) y Pydantic v2 (registros, APIs, mensajes), incluyendo validación en la ingesta, evolución de esquemas compatible y pruebas de datos con hypothesis. Úsala al recibir datos de una fuente externa, al definir el esquema de una tabla o DataFrame, al cambiar columnas, o cuando alguien mencione "esquema", "schema", "validación de datos", "data contract", "data quality", "Pandera", "Pydantic".
---

# Contratos de datos

Un contrato es la descripción ejecutable de qué forma tienen los datos: columnas, tipos, nulos, rangos, unicidad y reglas entre columnas. Se valida **en los bordes**, donde los datos entran al sistema o pasan de un equipo a otro. Adentro se confía en que ya cumplen.

## Qué herramienta en cada borde

| Borde | Herramienta | Por qué |
|---|---|---|
| API (entrada/salida de FastAPI), mensajes, archivos de configuración, filas sueltas | **Pydantic v2** (`BaseModel`) | Valida y convierte objetos; integración nativa con FastAPI |
| Lotes tabulares (DataFrames de Polars o pandas) en ingesta y transformaciones | **Pandera** (`DataFrameModel`) | Valida columnas completas, rápido, reglas entre filas y columnas |
| Esquema de la tabla en la base de datos | SQLAlchemy 2 + Alembic (ver skill `migraciones-alembic`) | La base es la última barrera: `NOT NULL`, `CHECK`, `UNIQUE`, claves foráneas |

No valides lo mismo tres veces con tres herramientas. Elige el borde y deja la base de datos como respaldo con restricciones simples.

## Cómo escribir un contrato

1. **Un módulo por dominio** (`contratos/cosecha.py`) versionado junto al código que lo usa.
2. Cada columna con: tipo, si admite nulos, rango o valores permitidos, y unidad en el nombre o en la descripción (`peso_kg`, `area_ha`).
3. **Unicidad de la clave natural** como regla explícita (`unique=["lote_id", "fecha"]`).
4. Reglas entre columnas como `@dataframe_check` (p. ej., `fecha_cosecha >= fecha_siembra`).
5. Modo estricto (`strict=True`) en la entrada de fuentes externas: una columna nueva inesperada debe avisar, no pasar en silencio.
6. `coerce=True` solo donde la fuente manda texto que debe ser número o fecha, y documentado.
7. Validación perezosa (`lazy=True`) para obtener **todos** los errores de un lote de una vez, no solo el primero, y mandar las filas malas a cuarentena (ver skill `ingesta-idempotente`).

Consulta la documentación vigente de Pandera (Context7) para la sintaxis exacta con Polars: la API de backends cambia entre versiones.

## Evolución del esquema

| Cambio | ¿Compatible? | Cómo hacerlo |
|---|---|---|
| Agregar columna opcional | Sí | Agregar con nulo permitido o valor por defecto |
| Agregar columna obligatoria | No | Primero opcional, rellenar históricos, después obligatoria |
| Renombrar columna | No | Agregar la nueva, escribir ambas, migrar consumidores, quitar la vieja (expand/contract) |
| Cambiar tipo | No | Columna nueva con el tipo nuevo y migración |
| Hacer más estricto un rango | Depende | Medir primero cuántas filas históricas lo violan |

Sube la versión del contrato (`_version_esquema`) en cada cambio incompatible y anótala en el linaje.

## Pruebas de datos

- **Casos válidos e inválidos fijos**: un DataFrame pequeño que pasa y uno por cada regla que debe fallar, comprobando el mensaje.
- **Property-based con hypothesis**: Pandera puede generar datos que cumplen el esquema (`Schema.strategy()`); úsalos para probar que las transformaciones conservan el contrato de salida.
- **Contrato de salida**: cada transformación valida su resultado contra el contrato de la capa siguiente en las pruebas.
- En CI, una muestra de datos reales anonimizados contra el contrato detecta derivas de la fuente antes de producción.

## Cuándo no hace falta

- Un notebook exploratorio no necesita contratos; el pipeline que nace de él, sí.
- Datos internos que ya pasaron un contrato en el borde no se revalidan en cada función.

## Cómo verificar que esta skill se cumplió

- Cada fuente externa tiene un contrato estricto validado al entrar.
- La clave natural tiene regla de unicidad.
- Hay pruebas con un caso inválido por regla y pasan.
- Los cambios incompatibles suben la versión del esquema.
