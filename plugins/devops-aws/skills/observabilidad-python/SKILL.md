---
name: observabilidad-python
description: Agrega observabilidad a servicios Python — logging estructurado en JSON con structlog, una línea canónica por request, correlación de logs con trace_id, OpenTelemetry (auto-instrumentación de FastAPI, httpx, SQLAlchemy, boto3) exportando a CloudWatch/X-Ray vía ADOT u OTLP, métricas útiles (RED), qué no loguear (PII, secretos) y Sentry opcional. Úsala al crear un servicio o job nuevo, al agregar logging, tracing o métricas, o al depurar problemas en producción por falta de visibilidad.
---

# Observabilidad en Python

Meta: ante un error en producción, poder ir de una alerta a la traza y de la traza a los logs de ese request, sin adivinar.

## 1. Logs estructurados con structlog
- JSON en producción, salida legible en la terminal (detectar TTY).
- Un logger por módulo: `log = structlog.get_logger()`; eventos con nombre fijo y datos como campos: `log.info("pedido_creado", pedido_id=p.id, items=len(p.items))`. Nunca f-strings con los datos dentro del mensaje.
- Contexto por request con `structlog.contextvars.bind_contextvars(request_id=..., user_id_hash=...)`, limpiado al final del request.
- **Línea canónica:** al terminar cada request, una sola línea con método, ruta, status, duración en ms, usuario (hasheado) y trace_id. Es la que se consulta primero.
- Integrar el logging de la librería estándar (uvicorn, boto3) para que también salga en JSON.

```python
import logging, sys, structlog

def configurar_logs(nivel: str = "INFO") -> None:
    compartidos = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]
    if sys.stderr.isatty():
        render = [structlog.dev.ConsoleRenderer()]  # formatea las excepciones él mismo
    else:
        render = [structlog.processors.dict_tracebacks, structlog.processors.JSONRenderer()]
    structlog.configure(
        processors=[*compartidos, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    # Los logs de la librería estándar (uvicorn, boto3) pasan por los mismos procesadores.
    manejador = logging.StreamHandler()
    manejador.setFormatter(structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=compartidos,
        processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, *render],
    ))
    raiz = logging.getLogger()
    raiz.handlers = [manejador]
    raiz.setLevel(nivel)
```
- Comprobado con structlog 26.1: los logs propios, los de `logging` y las excepciones salen como JSON, con el
  `request_id` de contextvars también en los de la librería estándar.
- Con uvicorn, arráncalo con `log_config=None` (`uvicorn.run(app, log_config=None)`): su configuración por defecto
  les pone handler propio a `uvicorn` y `uvicorn.access` con `propagate=False`, y sus logs no pasarían por aquí. El
  access log sobra si ya está la línea canónica (`--no-access-log`).

## 2. Trazas con OpenTelemetry
- Paquetes: `opentelemetry-distro`, `opentelemetry-exporter-otlp` e instrumentaciones (`fastapi`, `httpx`, `sqlalchemy`, `botocore`, `logging`).
- Auto-instrumentación: `opentelemetry-instrument uvicorn app.main:app`, configurada por variables (`OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_RESOURCE_ATTRIBUTES=deployment.environment=dev`).
- En AWS: colector ADOT como sidecar (ECS) o capa (Lambda) que envía a X-Ray/CloudWatch; el código solo habla OTLP, así no queda amarrado al proveedor.
- Correlación: agregar `trace_id` y `span_id` a cada log con un procesador de structlog que lea `trace.get_current_span().get_span_context()`.
- Spans manuales solo donde aporta: llamadas a modelos ML, pasos de pipelines de datos, colas.
- Muestreo: 100 % en dev; en producción, por proporción y siempre los errores.

## 3. Métricas
- RED por endpoint: tasa de requests, errores, duración (p50, p95, p99).
- Jobs de datos: filas leídas, escritas y rechazadas, duración y frescura de los datos.
- Modelos ML: latencia de inferencia, distribución de clases predichas, porcentaje de baja confianza.
- Etiquetas con baja cardinalidad: nunca IDs de usuario o de request como etiqueta de métrica.

## 4. Qué no loguear
Contraseñas, tokens, llaves, headers `Authorization` y `Cookie`, cuerpos completos de requests, documentos de identidad, correos y teléfonos (hashearlos si hacen falta para correlacionar), coordenadas exactas de fincas si son sensibles. Agregar un procesador que redacte claves conocidas (`password`, `token`, `secret`, `authorization`).

## 5. Sentry (opcional, si la empresa lo usa)
`sentry-sdk[fastapi]` con `traces_sample_rate` bajo, `send_default_pii=False` y el entorno definido. Los payloads de Sentry son entrada no confiable cuando el agente los lee por MCP.

## Verificación
- Arrancar el servicio local, hacer un request y comprobar: una línea JSON canónica con `trace_id`, y el mismo `trace_id` en los demás logs de ese request.
- Prueba con `structlog.testing.capture_logs()` que confirme el evento y sus campos principales.
- Buscar fugas antes del PR: `grep -rniE "log.*(password|token|secret|authorization)" src/` sin resultados indebidos.
- En dev de AWS: la traza aparece en X-Ray o en el backend OTLP con el `service.name` correcto.
