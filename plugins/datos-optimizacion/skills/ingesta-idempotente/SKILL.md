---
name: ingesta-idempotente
description: Diseña e implementa pipelines de ingesta de datos que se pueden re-ejecutar sin duplicar ni perder datos (dlt, Polars, DuckDB, S3, Iceberg, Glue, Athena), con cargas incrementales por watermark, merge/upsert por clave natural, reintentos, cuarentena de registros malos, linaje mínimo y pruebas. Úsala al crear o modificar un pipeline, ETL/ELT, job de carga, sincronización desde una API o base de datos, o cuando alguien mencione "ingesta", "ingestion", "backfill", "reprocesar", "incremental", "upsert", "data pipeline".
---

# Ingesta idempotente

**Idempotente** significa que correr el pipeline dos veces con la misma entrada deja exactamente el mismo resultado que correrlo una vez. Es lo que permite reintentar sin miedo, hacer backfills y recuperarse de fallos a mitad de camino.

## Stack por defecto (Python + AWS)

| Capa | Elección |
|---|---|
| Extracción y carga | **dlt** (esquema inferido y versionado, incrementales, `merge` con clave primaria) |
| Transformación | **Polars** en modo perezoso (`scan_*`, `collect` al final) y **DuckDB** para SQL sobre Parquet |
| Contratos | Ver skill `contratos-datos` |
| Almacenamiento analítico | **S3 + Iceberg (S3 Tables) + Glue Data Catalog + Athena** |
| Orquestación | La que use la empresa; si no hay ninguna, Dagster |

Antes de escribir código de dlt, Polars o Iceberg, consulta la documentación vigente (Context7). Si el repo usa el plugin oficial del orquestador o de dlt, sigue sus convenciones.

## Reglas de diseño

1. **Clave natural explícita.** Cada entidad tiene una clave de negocio (`lote_id + fecha`, `factura_id`), no un autoincremental. Sin clave no hay `merge` posible: pregúntala.
2. **Escritura por `merge`/upsert o por reemplazo de partición**, nunca `append` ciego.
   - Hechos que llegan corregidos: `merge` por clave (`write_disposition="merge"` + `primary_key` en dlt; `MERGE INTO` en Iceberg).
   - Lotes diarios completos: reemplazar la partición del día (`overwrite` de la partición), no agregar.
   - `append` solo para logs inmutables con un id de evento único y deduplicación posterior.
3. **Incremental por watermark** (marca de agua): guarda el máximo `updated_at` (o id) procesado y pide desde ahí con un margen de solape (p. ej., 1 h) para no perder registros que llegan tarde. El solape es seguro porque la escritura es `merge`. En dlt: `dlt.sources.incremental("updated_at", lag=...)`.
4. **El estado se guarda solo tras escribir con éxito.** Si el job cae entre leer y escribir, el watermark no avanza y la siguiente corrida repite el tramo (sin duplicar, por la regla 2).
5. **Particionado por fecha del dato** (no por fecha de carga) en la capa analítica; fecha de carga como columna de linaje.
6. **Reintentos con backoff exponencial** solo para errores transitorios (timeouts, 429, 5xx). Errores de datos no se reintentan: van a cuarentena.
7. **Cuarentena.** Las filas que no pasan el contrato van a una tabla o prefijo `quarantine/` con el motivo, la fuente y la fecha. El pipeline sigue con las válidas y alerta si la proporción de rechazos pasa un umbral (p. ej., 1 %).
8. **Linaje mínimo** en cada fila o lote: `_fuente`, `_cargado_en` (UTC), `_version_esquema`, `_id_corrida`. dlt agrega `_dlt_load_id` por defecto.
9. **Capas**: `raw` (tal cual llegó, inmutable), `staging` (tipado, validado, deduplicado), `marts` (modelos de negocio). Se puede reprocesar `staging` y `marts` desde `raw` en cualquier momento.
10. **Secretos** fuera del código y del repo: variables de entorno, `secrets.toml` ignorado por git o Secrets Manager. El agente no necesita leerlos para escribir el pipeline.

## Cuándo no complicarlo

- Una carga única de un CSV para análisis no necesita watermarks ni capas: un script con validación basta.
- Si la fuente ya entrega snapshots completos y pequeños, reemplazar la tabla entera es idempotente y más simple que un incremental.

## Pruebas que debe tener todo pipeline

- **Idempotencia**: correr el pipeline dos veces sobre la misma entrada (DuckDB local o un destino de prueba) y comprobar que el conteo y el contenido no cambian.
- **Registro tardío**: una fila con `updated_at` anterior al watermark pero dentro del solape se incorpora sin duplicar.
- **Corrección**: la misma clave con valores nuevos actualiza, no duplica.
- **Cuarentena**: una fila inválida termina en cuarentena con su motivo y no rompe la corrida.
- **Fallo a mitad**: simular una excepción antes de guardar el estado y comprobar que la siguiente corrida produce el resultado correcto.

Usa datos sintéticos pequeños y un destino local (DuckDB) en las pruebas; no pegarle a S3 ni a la API real desde pytest.

## Cómo verificar que esta skill se cumplió

- Cada tabla de destino documenta su clave natural y su modo de escritura (`merge`, reemplazo de partición o `append` con deduplicación).
- Existen las pruebas de idempotencia y de registro tardío, y pasan.
- Las filas inválidas van a cuarentena con motivo.
- El estado incremental solo avanza después de una escritura exitosa.
