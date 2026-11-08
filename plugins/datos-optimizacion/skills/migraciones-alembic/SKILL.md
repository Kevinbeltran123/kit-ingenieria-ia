---
name: migraciones-alembic
description: Escribe modelos con SQLAlchemy 2 (estilo tipado con Mapped) y migraciones de base de datos con Alembic que sean revisadas, reversibles y sin downtime en Postgres (expand/contract, índices concurrentes, migraciones de datos separadas). Úsala al crear o cambiar tablas, columnas, índices o restricciones, al generar una migración, o cuando alguien mencione "migración", "migration", "Alembic", "autogenerate", "SQLAlchemy", "cambio de esquema", "ALTER TABLE".
---

# Migraciones con Alembic y SQLAlchemy 2

Si el repo tiene la skill `supabase-postgres-best-practices`, úsala para decidir tipos de columna, índices y bloqueos en Postgres. Esta skill cubre el flujo de migraciones.

## Modelos (SQLAlchemy 2)

- Estilo tipado: `class Lote(Base)` con `id: Mapped[int] = mapped_column(primary_key=True)` y `Mapped[str | None]` para nulos. Nada de `Column()` suelto del estilo 1.x.
- Restricciones en el modelo, con **nombres explícitos** mediante `MetaData(naming_convention=...)`. Sin nombres, Alembic no puede borrarlas de forma fiable después.
- Sesiones con `with Session(engine) as s, s.begin():` y consultas con `select()`; nada de `session.query()` en código nuevo.

## Flujo de una migración

1. Cambia el modelo.
2. `alembic revision --autogenerate -m "descripcion corta"`.
3. **Revisa el archivo generado línea por línea, antes del commit.** Una migración recién generada y sin commit se
   puede corregir; cuando ya está en git, el plugin `barreras` bloquea editarla y hay que crear otra.
   Autogenerate no detecta todo y a veces propone cosas peligrosas:
   - No detecta cambios en valores de un `Enum`, renombres (los ve como borrar + crear, perdiendo datos), cambios de `server_default` (solo los compara con `compare_server_default=True` en `env.py`; viene apagado), ni ciertos índices funcionales o parciales.
   - Si ves un `drop_column` + `add_column` que en realidad es un renombre, reemplázalo por `alter_column(..., new_column_name=...)`.
4. Escribe `downgrade()` real. Si no es reversible (borrar datos), dilo explícitamente con un comentario y lanza una excepción en `downgrade()`.
5. Prueba `upgrade` → `downgrade` → `upgrade` contra una base local (Postgres en Docker o testcontainers), no SQLite: el comportamiento difiere.
6. Revisa el SQL que se va a ejecutar en producción con `alembic upgrade --sql <rev_anterior>:<rev_nueva>`.

## Reglas

- **Nunca edites una migración ya aplicada** en algún entorno compartido. Crea una nueva que corrija.
- **Esquema y datos van en migraciones separadas.** Las migraciones de datos grandes van en lotes (`UPDATE ... WHERE id BETWEEN ...`) o como un job aparte, no en una transacción gigante.
- **No importes los modelos de la aplicación dentro de una migración**: el modelo cambiará y romperá migraciones viejas. Usa `sa.table()`/`sa.column()` locales o SQL.
- Un `head` por rama; resuelve divergencias con `alembic merge`.

## Cambios sin downtime en Postgres (expand/contract)

Para cualquier cambio que rompa el código que está corriendo:

1. **Expand**: agrega lo nuevo de forma compatible (columna nueva nullable, tabla nueva). Despliega.
2. El código escribe en ambos lados y lee del nuevo. Rellena históricos con una migración de datos en lotes.
3. **Contract**: cuando nadie usa lo viejo, en otra migración y otro despliegue, quita lo viejo y agrega `NOT NULL` si aplica, sin bloquear la tabla (fila `SET NOT NULL` de abajo).

Operaciones que bloquean y cómo evitarlo:

| Operación | Riesgo | Alternativa |
|---|---|---|
| `CREATE INDEX` | Bloquea escrituras | `op.create_index(..., postgresql_concurrently=True)` dentro de `with op.get_context().autocommit_block():` |
| `ADD COLUMN ... NOT NULL DEFAULT` volátil | Reescribe la tabla | Columna nullable, rellenar en lotes, luego `NOT NULL` como en la fila siguiente |
| `ALTER COLUMN ... SET NOT NULL` | Recorre toda la tabla con bloqueo exclusivo | Postgres 18: `ADD CONSTRAINT c NOT NULL col NOT VALID` y después `VALIDATE CONSTRAINT c`. Postgres 12–17: `CHECK (col IS NOT NULL) NOT VALID`, `VALIDATE CONSTRAINT`, `SET NOT NULL` (con un CHECK válido no recorre la tabla) y borrar el CHECK |
| `ALTER COLUMN TYPE` | Reescribe y bloquea | Columna nueva + copia + cambio de lectura (expand/contract) |
| `ADD CONSTRAINT FOREIGN KEY / CHECK` | Valida toda la tabla con bloqueo | `NOT VALID` primero, `VALIDATE CONSTRAINT` después |

Pon `lock_timeout` (p. ej., `SET lock_timeout = '5s'`) al inicio de migraciones en tablas grandes para que fallen rápido en vez de encolar todo el tráfico detrás.

## Pruebas en CI

- Un job que levanta Postgres, corre `alembic upgrade head`, luego `alembic downgrade base` (o hasta la migración anterior) y otra vez `upgrade head`.
- Una prueba que compara el esquema resultante con los modelos (`alembic check` falla si hay diferencias pendientes de migrar).

## Cómo verificar que esta skill se cumplió

- La migración fue revisada (sin renombres convertidos en borrado, enums cubiertos a mano).
- `downgrade()` existe y funciona, o es explícitamente irreversible.
- `upgrade → downgrade → upgrade` pasa contra Postgres real.
- `alembic check` no reporta diferencias.
- Los índices en tablas grandes se crean de forma concurrente.
