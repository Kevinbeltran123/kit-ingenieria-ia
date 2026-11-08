---
name: receta-entrenamiento
description: Receta por fases para entrenar modelos de visión por computador (clasificación, detección o segmentación de plantas, palmas, enfermedades) sin fallas silenciosas, adaptada de la "Recipe for Training Neural Networks" de Karpathy. Úsala al empezar un modelo, al elegir baseline, al depurar un entrenamiento que no mejora o antes de afirmar que un modelo funciona. Incluye métricas por clase y por finca, calibración, desbalance, MLflow y DVC. Training recipe, baseline, overfit one batch, DINOv3 linear probe.
---

# Receta de entrenamiento

El entrenamiento "falla en silencio": un bug no lanza error, solo da un modelo un poco peor. Por eso se avanza por fases y **cada fase deja un artefacto** (gráfica, tabla o run de MLflow). No pases de fase sin él.

Antes de empezar: la división debe estar hecha y verificada con la skill `division-sin-fuga`. El código de evaluación vive en `eval/` y no lo modifica el agente (hook `evaluador-bloqueado` de este plugin).

## Fase 0: el problema y la taxonomía

- Escribe qué decisión toma alguien con la salida del modelo (p. ej., "enviar técnico a inspeccionar esta palma") y qué cuesta cada error. Pasar por alto una pudrición del cogollo (PC) cuesta mucho más que una inspección extra.
- Fija las etiquetas con la autoridad del dominio. Ejemplo para PC, la escala de la resolución ICA 092771 de 2021 (numeral 2.4.3): grado 0 (sana); leve, grados 1–2 (lesiones hasta el 40 % de la hoja flecha); intermedio, grados 3–4 (hasta el 80 %); avanzado, grado 5, cráter (sin flechas ni hojas jóvenes) y hoja clorótica. La misma resolución define palma recuperada (flechas sanas y al menos 8 hojas nuevas bien desarrolladas): etiquétala aparte de sana. Valida el esquema con Cenipalma o el agrónomo de la empresa.
- La etiqueta sale del **censo de campo**, no de mirar la foto. "Sin etiqueta positiva" ≠ "sana".

Artefacto: `docs/problema.md` con decisión, costos y taxonomía.

## Fase 1: conocer los datos

- Abre los datos en FiftyOne (`fiftyone app`): mira cientos de ejemplos por clase y por finca.
- Busca duplicados, etiquetas erróneas, clases confundibles, sesgos de fondo, sensor o fecha.
- Cuenta ejemplos por clase × finca × fecha. Las enfermas suelen ser < 10 %.
- No entrenes con PlantVillage: fotos de laboratorio con sesgo de fondo que no transfieren a campo.

Artefacto: notebook o reporte con conteos y una galería de casos difíciles.

## Fase 2: esqueleto + baselines tontos

1. Pipeline completo de punta a punta (datos → modelo → métricas → MLflow) con un modelo trivial.
2. Baselines obligatorios: clase mayoritaria y una regla simple (p. ej., índice VARI con umbral sobre la copa).
3. Fija semillas; verifica que dos corridas iguales den lo mismo.
4. Revisa la pérdida inicial: con C clases balanceadas debería rondar `ln(C)`.
5. Visualiza **exactamente** lo que entra a la red, después de aumentos y normalización.

Artefacto: run de MLflow con los baselines.

## Fase 3: baseline fuerte y sobreajustar un batch

- Patrón dominante para palma: **segmentar copas primero** (RF-DETR-Seg Nano–Large, Apache-2.0, con slicing SAHI de `supervision` para ortomosaicos) y **clasificar por palma** después.
- Clasificador base: **DINOv3 congelado + cabeza lineal** (linear probe). Barato y difícil de superar con pocas etiquetas.
- Sobreajusta un batch pequeño hasta pérdida ≈ 0. Si no puede, hay un bug: no sigas.

Artefacto: run con el linear probe y la curva del batch sobreajustado.

## Fase 4: regularizar y mejorar

En este orden, midiendo cada cambio contra el anterior:
1. Más datos o mejores etiquetas (casi siempre gana).
2. Aumentos coherentes con el campo: iluminación, escala, rotación, desenfoque de movimiento.
3. Fine-tuning parcial del backbone con learning rate bajo.
4. Pérdida ponderada o focal para el desbalance (muestreo solo en train).
5. Early stopping con la métrica de validación que importa, no con la pérdida.

Un cambio a la vez. Registra cada experimento en MLflow con: commit de git, hash del dataset (DVC), semilla y `uv.lock`.

## Fase 5: evaluar como en campo

Elige el modelo final, su umbral y su calibración **en validación** (o con validación cruzada agrupada, ver `division-sin-fuga`). Después evalúa **ese único modelo** sobre el test que nunca se tocó, una sola vez. Si comparas candidatos en test y te quedas con el mejor, el número de test ya es parte de la selección y sale optimista.

- **Por palma:** recall de la clase enferma con intervalo de confianza, PR-AUC (no accuracy), matriz de confusión por grado de severidad. El intervalo sale de un bootstrap por **lote** (se remuestrean lotes enteros con reemplazo), nunca por imagen: las fotos de una palma y las palmas de un lote no son independientes, y remuestrear imágenes da un intervalo falsamente angosto. Con pocos lotes en test el intervalo sale ancho, y así se reporta.
- **Detección:** mAP@50 y recall a IoU fijo.
- **Por finca y por fecha**, con el peor caso explícito.
- **Calibración:** ECE y diagrama de confiabilidad; temperature scaling ajustado en validación.
- **Umbral** elegido en validación por costo de errores y documentado; en test solo se aplica.
- Comparación contra los baselines tontos de la fase 2.

Un reporte que solo trae accuracy no pasa esta fase.

Artefacto: reporte de evaluación + `ficha-modelo` (skill de este plugin).

## Fase 6: validación en campo

Piloto prospectivo: el modelo marca palmas, un técnico verifica sin conocer la predicción, y se miden precisión y recall reales. Calibración, OOD y ensembles no cierran solos la brecha laboratorio→campo (estudio de 2026), así que este paso no se salta antes de producción.

## Señales de alarma

- Métrica de test muy superior a lo publicado → revisa fuga (`division-sin-fuga`).
- Gran diferencia entre fincas → el modelo aprendió la finca, no la enfermedad.
- Mejora que desaparece al cambiar la semilla → ruido, no mejora.
- Se compararon varios modelos en test → ese test ya sirvió para elegir; la estimación honesta necesita datos nuevos (otra finca o fechas posteriores).
- El agente propone cambiar la métrica o el evaluador → no; la métrica es fija.

## Referencias
- Karpathy, "A Recipe for Training Neural Networks" (2019).
- Karpathy, autoresearch (2026): evaluación fija, el agente solo edita el entrenamiento.
- RewardHackingAgents (arXiv 2603.11337, 2026): ~50 % de episodios con manipulación del evaluador si no se bloquea.
- Cenipalma: López-Vásquez et al., *Agronomy* 14(11):2486 (2024), PC con segmentación de instancias.
