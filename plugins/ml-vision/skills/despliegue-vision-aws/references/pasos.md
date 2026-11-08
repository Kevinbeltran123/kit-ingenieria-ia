# Pasos de despliegue (referencia)

Ajusta nombres de buckets, roles y versiones. Fija versiones exactas de contenedores y librerías.

## 1. Entrenamiento en SageMaker con spot

```python
# SageMaker Python SDK v3 (sagemaker>=3): `sagemaker.pytorch.PyTorch` ya no existe.
from sagemaker.core import image_uris
from sagemaker.train import ModelTrainer
from sagemaker.train.configs import CheckpointConfig, Compute, InputData, SourceCode, StoppingCondition

imagen = image_uris.retrieve(framework="pytorch", region=REGION, version="2.10.0", py_version="py313",
                             instance_type="ml.g5.xlarge", image_scope="training")
entrenador = ModelTrainer(
    training_image=imagen, role=ROL_SAGEMAKER,
    source_code=SourceCode(source_dir="src", entry_script="train.py"),
    compute=Compute(instance_type="ml.g5.xlarge", instance_count=1, enable_managed_spot_training=True),
    stopping_condition=StoppingCondition(max_runtime_in_seconds=4 * 3600, max_wait_time_in_seconds=8 * 3600),
    checkpoint_config=CheckpointConfig(s3_uri=f"s3://{BUCKET}/checkpoints/{EXPERIMENTO}/"),
    environment={"MLFLOW_TRACKING_URI": MLFLOW_ARN, "GIT_SHA": GIT_SHA},
)
entrenador.train(input_data_config=[
    InputData(channel_name="train", data_source=f"s3://{BUCKET}/datasets/{HASH_DVC}/"),
])
```
- La imagen de PyTorch 2.10.0 solo viene con Python 3.13 (`py313`; SDK 3.28.0). Para otra versión, mira las que
  trae `image_uris` en el SDK instalado.
- `train.py` debe reanudar desde `/opt/ml/checkpoints` (spot puede interrumpir).
- El contenedor necesita el plugin `sagemaker-mlflow` (por ejemplo en `SourceCode(requirements=...)`): sin él, la ARN
  de la MLflow App en `MLFLOW_TRACKING_URI` falla con `UnsupportedModelRegistryStoreURIException`.
- Registra en MLflow: `GIT_SHA`, `HASH_DVC`, semilla, `uv.lock` como artefacto.

## 2. Registro

```python
import onnx

# Se registra el ONNX del paso 3 y los pesos en safetensors. No uses mlflow.pytorch.log_model: cargar ese
# formato (pickle o pt2) ejecuta código, lo que contradice la skill carga-segura-modelos.
mlflow.onnx.log_model(onnx.load("modelos/palma.onnx"), name="model", input_example=ejemplo,
                      registered_model_name="palma-pc-clasificador")
mlflow.log_artifact("modelos/pesos.safetensors")
mlflow.log_artifact("docs/model-card.md")
mlflow.log_artifact("reportes/evaluacion.html")
```
Exporta a ONNX (paso 3) antes de registrar. Promueve a "aprobado" en Model Registry solo tras revisión humana.
En el servicio, carga el ONNX con onnxruntime; no uses `mlflow.pytorch.load_model`.

## 3. Export ONNX y paridad

```python
# tests/test_paridad_onnx.py
from pathlib import Path

import numpy as np, onnxruntime as ort, torch
from PIL import Image

from entrenamiento.transformaciones import transformacion_eval  # la de validación y test
from servicio.preprocesar import preprocesar                     # la misma función que llama la Lambda


def test_paridad_onnx(modelo_pytorch, rutas_test, tmp_path):  # rutas_test: JPEG reales del test, no ruido
    modelo_pytorch.eval()
    lote = torch.stack([transformacion_eval(Image.open(r).convert("RGB")) for r in rutas_test])
    # dynamic_shapes por posición: en un dict, las claves son los argumentos de forward
    # (pixel_values en transformers), no los input_names del ONNX.
    torch.onnx.export(modelo_pytorch, (lote,), tmp_path / "model.onnx", dynamo=True,
                      input_names=["x"], output_names=["y"], dynamic_shapes=({0: "batch"},))
    sesion = ort.InferenceSession(str(tmp_path / "model.onnx"), providers=["CPUExecutionProvider"])
    with torch.no_grad():
        esperado = modelo_pytorch(lote).numpy()
    obtenido = sesion.run(None, {"x": lote.numpy()})[0]
    np.testing.assert_allclose(obtenido, esperado, rtol=1e-3, atol=1e-4)
    assert (obtenido.argmax(1) == esperado.argmax(1)).all()


def test_preprocesamiento_del_servicio_igual_al_de_entrenamiento(rutas_test):
    # La Lambda decodifica, redimensiona y normaliza con su propio código: si difiere del de
    # entrenamiento (interpolación, RGB/BGR, media y desviación), en producción el modelo ve otra cosa.
    for r in rutas_test:
        servicio = preprocesar(Path(r).read_bytes())  # bytes → array, como en la Lambda
        entrenamiento = transformacion_eval(Image.open(r).convert("RGB")).numpy()
        assert servicio.shape == entrenamiento.shape and servicio.dtype == np.float32
        np.testing.assert_allclose(servicio, entrenamiento, atol=2e-2)  # ≈ 1 nivel de gris normalizado
```
- La primera prueba solo compara la exportación: si la Lambda entrega BGR, pasa igual. Por eso la segunda
  compara el preprocesamiento desde el JPEG crudo (comprobado con torch 2.15: el error de BGR solo lo atrapa ella).
- Si `preprocesar` no se puede importar en las pruebas, el preprocesamiento está duplicado: muévelo a un módulo
  que usen la Lambda y estas pruebas.
- Para INT8, compara también métricas (recall de enfermas) entre FP32 e INT8 sobre el test: la tolerancia numérica no basta.

## 4. Inferencia por lotes (ortomosaicos)

1. El vuelo llega a `s3://.../vuelos/<finca>/<fecha>/`.
2. Un Processing Job: corta el ortomosaico en teselas con solapamiento (SAHI/`supervision`), detecta copas, clasifica por palma, une resultados por coordenada.
3. Salida: GeoJSON/GeoPackage con una alerta por palma + confianza calibrada.
4. Dispara el job con EventBridge al crearse el objeto.

## 5. Inferencia bajo demanda

- Lambda con imagen de contenedor: `onnxruntime` + modelo ONNX dentro de la imagen (no descargar en cada invocación).
- Mide arranque en frío y latencia con imágenes del tamaño real.
- Valida tamaño y tipo de imagen de entrada; rechaza lo demás.

## 6. Drift de embeddings

1. Línea base: embeddings DINOv3 del set de validación, guardados con su hash.
2. Job semanal (EventBridge + Processing Job o Lambda): embeddings de las imágenes nuevas por finca/mes.
3. Métrica: distancia entre distribuciones (p. ej., MMD o distancia coseno entre centroides) y distribución de confianza.
4. Publica la métrica en CloudWatch con alarma; ante alerta, muestrea imágenes para etiquetado en campo.

## 7. Permisos

- Rol de SageMaker con acceso solo a los prefijos S3 del proyecto.
- CI con OIDC (`aws-actions/configure-aws-credentials` fijado por SHA), sin llaves de larga duración.
- El agente usa un perfil de solo lectura; no lanza jobs ni despliega.
