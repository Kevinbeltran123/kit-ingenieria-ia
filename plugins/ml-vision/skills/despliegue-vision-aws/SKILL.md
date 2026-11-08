---
name: despliegue-vision-aws
description: Cómo entrenar, registrar, desplegar y monitorear modelos de visión en AWS con costo bajo: SageMaker Training con spot, MLflow serverless y Model Registry, Batch Transform para ortomosaicos de dron, Lambda con ONNX en CPU para fotos sueltas, modelos INT8 sin conexión en campo, paridad ONNX y drift de embeddings. Úsala al diseñar el despliegue, exportar a ONNX o configurar monitoreo de un modelo de visión. SageMaker, MLOps, ONNX Runtime, model drift.
---

# Despliegue de visión en AWS

Elige la arquitectura por el patrón de uso, no por la herramienta. Detalle de cada paso en `references/pasos.md`.

## Arquitectura mínima viable

| Capa | Elección |
|---|---|
| Datos y ortomosaicos | S3 con versionado y cifrado KMS; DVC con remoto S3 |
| Anotación | Label Studio o CVAT autoalojado + pre-anotación SAM con revisión humana |
| Entrenamiento | SageMaker Training Jobs con instancias spot y checkpoints en S3 |
| Tracking y registro | MLflow serverless de SageMaker AI → SageMaker Model Registry |
| Vuelo completo → mapa de alertas | SageMaker Batch Transform o Processing Job con GPU |
| Foto suelta desde app | Lambda (imagen de contenedor) + ONNX Runtime CPU, o Serverless Inference |
| Campo sin señal | ONNX INT8 / TFLite / CoreML en el celular |
| Drift | Job programado propio sobre embeddings + CloudWatch |
| CI | GitHub Actions con OIDC a AWS (sin llaves) |

Límites a recordar: Serverless Inference no tiene GPU, Model Monitor ni data capture (máx. 6 GB de RAM). Model Monitor solo calcula estadísticas tabulares de la salida, no de las imágenes; por eso el drift va en un job propio.

## Reglas

1. El entrenamiento se lanza desde código versionado en git; el job registra commit, hash del dataset y semilla en MLflow.
2. Solo se despliega un modelo registrado con ficha (`ficha-modelo`) y evaluado con el test intacto.
3. Exporta a ONNX y prueba **paridad numérica** PyTorch vs. ONNX en CI antes de desplegar.
4. Pesos en safetensors u ONNX (`carga-segura-modelos`).
5. El agente no despliega: los cambios de infraestructura van por PR y se aplican desde CI.

## Verificación

- Prueba de paridad ONNX pasa en CI (`references/pasos.md`, sección 3).
- Latencia medida en el destino real (Lambda, celular) con imágenes del tamaño de producción.
- El job de drift tiene una línea base guardada y una alarma en CloudWatch.
- El run de MLflow del modelo desplegado tiene ficha, métricas por finca y reporte de paridad.
