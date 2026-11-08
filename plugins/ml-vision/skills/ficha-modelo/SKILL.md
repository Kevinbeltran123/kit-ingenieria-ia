---
name: ficha-modelo
description: Crea o actualiza la ficha del modelo (model card) y la ficha del dataset (dataset card) para modelos de visión y agro, incluyendo cómo se dividieron los datos, métricas por finca, calibración, licencias y límites de validación en campo. Úsala antes de registrar un modelo en MLflow/SageMaker Model Registry, al publicar resultados o al entregar un modelo a otro equipo. Model card, dataset card, datasheet.
---

# Ficha del modelo y del dataset

Un modelo sin ficha no se registra. La ficha dice para qué sirve, con qué datos se probó y **dónde no se ha probado**.

## Pasos

1. Copia las plantillas al repo si no existen:
   - `references/plantilla-dataset-card.md` → `docs/dataset-card.md`
   - `references/plantilla-model-card.md` → `docs/model-card.md`
2. Llena cada campo con datos verificables: hash del dataset (DVC), ID del run de MLflow, commit de git, archivo de split.
3. Copia las métricas del reporte de evaluación (fase 5 de `receta-entrenamiento`) tal cual; no las redondees a favor.
4. Escribe los límites con la misma claridad que los resultados: fincas, fechas, sensores, cultivares y grados de severidad que **no** están en el test.
5. Adjunta las fichas como artefactos del run de MLflow (`mlflow.log_artifact`) antes de registrar el modelo.

## Verificación

- No quedan campos `<...>` sin llenar: `grep -n "<" docs/model-card.md docs/dataset-card.md`.
- El hash del dataset y el ID del run coinciden con los del registro.
- La sección "Límites" no está vacía.
- Las métricas incluyen al menos una por finca y el peor caso.
