---
name: rendimiento-python
description: Optimización de rendimiento en Python con medición primero - perfilado con py-spy y scalene, benchmarks con pytest-benchmark, y patrones comunes (consultas N+1, I/O async, Polars vs pandas, vectorización). Úsala cuando algo esté lento, haya timeouts, alto uso de CPU o memoria, costos altos de cómputo, o pidan "optimizar", "performance", "profiling", "es lento", "acelerar".
---

# Rendimiento Python

Regla: **no optimices sin una medición antes y otra después**. La intuición sobre dónde se va el tiempo suele fallar, y una "optimización" sin medir es solo código más complicado.

## 1. Definir la meta

Antes de tocar código, escribe: qué operación, cuánto tarda hoy, cuánto debería tardar y con qué datos (tamaño realista, no 10 filas). Ejemplo: "procesar un ortomosaico de 2 GB: hoy 14 min, meta < 5 min, en `ml.g5.xlarge`".

## 2. Medir dónde se va el tiempo

| Situación | Herramienta | Comando |
|---|---|---|
| Proceso corriendo (API, worker) sin reiniciar | py-spy | `py-spy top --pid <PID>` o `py-spy record -o perfil.svg --pid <PID>` |
| Script o prueba de principio a fin | py-spy | `py-spy record -o perfil.svg -- python script.py` |
| CPU vs memoria vs Python vs código nativo, línea por línea | scalene 2.x | `scalene run script.py` y después `scalene view --cli -r` (solo las líneas con actividad) |
| Comparar dos implementaciones de una función | pytest-benchmark | `uv run pytest tests/bench --benchmark-only` |
| Consultas a base de datos | logs de SQLAlchemy | `create_engine(..., echo=True)` o `EXPLAIN ANALYZE` |

- No uses la función de sugerencias con IA de scalene: envía el código a un servicio externo.
- py-spy en macOS necesita `sudo` para adjuntarse a un PID; en contenedores, `--cap-add SYS_PTRACE`.
- Mide con datos y hardware parecidos a producción.

## 3. Patrones comunes (de más a menos frecuente)

1. **Consultas N+1**: un `SELECT` por cada elemento de una lista. Solución: `selectinload`/`joinedload` en SQLAlchemy 2, o una consulta con `IN`. Se detecta contando sentencias en el log.
2. **I/O secuencial**: llamadas HTTP, S3 o base de datos una tras otra. Solución: `asyncio.gather` con un límite (`asyncio.Semaphore`), o `ThreadPoolExecutor` si la librería es síncrona (boto3).
3. **Bloquear el event loop**: código síncrono pesado dentro de un endpoint `async def` de FastAPI. Solución: `def` normal (FastAPI lo corre en un threadpool) o `await asyncio.to_thread(...)`.
4. **Bucles de Python sobre datos tabulares**: `for fila in df.iterrows()`. Solución: operaciones vectorizadas; para datos medianos/grandes, Polars (lazy, multihilo) o DuckDB en lugar de pandas.
5. **Cargar todo en memoria**: leer un CSV o Parquet entero para filtrar 1 %. Solución: `pl.scan_parquet(...).filter(...).collect()` o leer por bloques.
6. **Recalcular lo mismo**: `functools.cache` para funciones puras; caché con TTL para llamadas externas.
7. **Serialización**: Pydantic v2 ya es rápido; evita convertir modelos a dict y de vuelta varias veces.
8. **Imágenes y ML**: decodificar fuera del bucle de GPU (DataLoader con `num_workers`), batch en inferencia, ONNX Runtime para CPU.

Optimizaciones de micro-nivel (cambiar `+` por `join`, etc.) casi nunca son el cuello de botella: confírmalo en el perfil antes.

## 4. Cambiar y volver a medir

- Un cambio a la vez; repite la misma medición del paso 2.
- Si la mejora es < 10 % y el código queda más complejo, revierte.
- Las pruebas existentes deben seguir pasando (skill `verify`); si no había, escribe una que fije el resultado antes de optimizar.

## 5. Reportar

En el PR:

```
Operación: procesar ortomosaico 2 GB (ml.g5.xlarge)
Antes: 14 min 10 s (mediana de 3 corridas)
Después: 4 min 35 s
Causa: decodificación JPEG en el hilo principal; ahora en DataLoader con 8 workers
Perfil: perfil-antes.svg / perfil-despues.svg
```

## Verificación

- Hay una medición antes y otra después, con los mismos datos y hardware.
- La mejora se explica por una causa vista en el perfil.
- `verify` pasa.
