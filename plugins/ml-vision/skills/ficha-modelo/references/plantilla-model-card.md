# Ficha del modelo: <nombre>

## Resumen
- **Qué hace:** <p. ej., clasifica cada copa de palma según la escala ICA de PC: grado 0 (sana), 1–5, cráter, hoja clorótica>
- **Decisión que apoya:** <p. ej., priorizar inspección de técnicos>
- **No usar para:** <p. ej., diagnóstico definitivo, otras especies, imágenes de celular>
- **Versión / registro:** <nombre en Model Registry, versión>
- **Run de MLflow:** <run_id> · **Commit:** <sha> · **Dataset:** <hash DVC> · **Split:** <ruta y hash>

## Arquitectura y entrenamiento
- **Detector de copas:** <modelo, pesos base y revisión>
- **Clasificador:** <backbone, congelado o no, cabeza>
- **Pesos base y licencias:** <p. ej., DINOv3 ViT-B/16, DINOv3 License; RF-DETR-Seg Medium, Apache-2.0>
- **Hiperparámetros clave:** <lr, épocas, aumentos, pérdida>
- **Entorno:** <imagen de contenedor, torch, `uv.lock` hash>

## Datos de evaluación
- **Cómo se dividió:** <por lote/finca/fecha; resultado de verificar_division.py>
- **Fincas y fechas en test:** <...>
- **Prevalencia en test:** <% por clase>

## Métricas (test, una sola evaluación)
| Métrica | Global | Peor finca | Por finca |
|---|---|---|---|
| Recall clase enferma (IC 95 %) | <...> | <...> | <...> |
| PR-AUC | <...> | <...> | <...> |
| mAP@50 (detección) | <...> | <...> | <...> |
| ECE (tras temperature scaling) | <...> | | |

- **Umbral de alerta:** <valor> · **Por qué:** <costo de falso negativo vs. falso positivo>
- **Baselines:** clase mayoritaria <...>, regla VARI <...>
- **Matriz de confusión por grado:** <enlace al artefacto>

## Validación en campo
- **Piloto:** <fecha, finca, n palmas, protocolo ciego>
- **Resultado:** <precisión y recall reales> o "pendiente"

## Límites conocidos
- <Fincas, regiones, cultivares (E. guineensis vs. híbrido OxG), sensores, GSD, horas del día no cubiertos>
- <Grados de severidad con pocos ejemplos>
- <Condiciones donde falla (nubes, sombra, palmas jóvenes)>

## Seguridad y mantenimiento
- **Formato de pesos:** safetensors / ONNX · **Paridad ONNX:** <tolerancia verificada>
- **Monitoreo de drift:** <job, umbral, frecuencia>
- **Responsable:** <persona o equipo> · **Revisión siguiente:** <fecha>
