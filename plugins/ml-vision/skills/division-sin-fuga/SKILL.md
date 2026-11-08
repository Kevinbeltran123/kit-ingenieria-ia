---
name: division-sin-fuga
description: Diseña y verifica divisiones train/val/test sin fuga de datos para visión por computador y teledetección agrícola (palma de aceite, cultivos, imágenes de dron o satélite). Úsala al crear o cambiar splits, al armar validación cruzada, al ver métricas sospechosamente altas, o antes de reportar resultados. Cubre agrupación por planta/lote/finca, división espacial por bloques, división temporal y duplicados. Data leakage, GroupKFold, StratifiedGroupKFold, spatial cross-validation.
---

# División sin fuga

La métrica solo vale si el conjunto de prueba se parece a lo que el modelo verá en producción: **palmas, lotes, fincas y fechas que nunca vio**. Con división aleatoria de imágenes, el desempeño de CNN en teledetección se infló hasta 28 % (Kattenborn 2022).

## 1. Define la jerarquía antes de dividir

Pregunta (o busca en los metadatos) cuál es la unidad independiente y qué la correlaciona:

| Nivel | Por qué filtra información |
|---|---|
| Imagen / tesela | Teselas vecinas del mismo ortomosaico se solapan |
| Palma (`palma_id`) | Varias fotos o fechas de la misma palma |
| Lote / bloque | Suelo, manejo y edad compartidos; contagio espacial |
| Finca | Clima, sensor, operador y protocolo de vuelo |
| Fecha de vuelo | Iluminación, fenología, progresión de la enfermedad |

Regla mínima: **agrupar al menos por palma y por lote**. Si el modelo se usará en fincas nuevas, el test debe tener **al menos una finca entera** que no esté en train. Si se usará hacia adelante en el tiempo, el test debe ser **posterior** a train y val.

Si faltan `palma_id` o `lote` en los metadatos, detente y pídelos. Sin ellos no se puede garantizar una división válida.

## 2. Genera la división

Elige según el uso real del modelo (detalle y código en `references/metodos.md`):

- **Nuevas palmas en fincas conocidas:** `StratifiedGroupKFold(groups=lote)` estratificando por clase.
- **Fincas nuevas:** holdout de fincas completas + `GroupKFold(groups=finca)` en el resto.
- **Hacia adelante en el tiempo:** corte por fecha (train < val < test), sin mezclar vuelos.
- **Mapas continuos (ortomosaicos):** bloques espaciales con buffer entre folds (Roberts 2017).

Reglas que siempre aplican:
1. Deduplicar **antes** de dividir (hash exacto; casi duplicados con embeddings o pHash si hay vuelos solapados).
2. Normalización, oversampling (SMOTE), selección de features y aumento de datos se ajustan **solo con train**.
3. No usar como feature el ID de lote, finca o fecha.
4. Guardar el split como archivo versionado (`splits/manifest.csv` con DVC o en git) y no recalcularlo en cada corrida. Fija la semilla.
   `splits/` está protegido por el hook del plugin: escribe la propuesta en `splits_propuesta/manifest.csv`,
   verifícala (paso 3) y pídele a la persona que la mueva a `splits/`. Así nadie cambia la división sin que la persona la vea.

## 3. Verifica (obligatorio)

Corre el verificador sobre el manifiesto (una fila por imagen). Si es una propuesta, pásale
`splits_propuesta/manifest.csv`:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/division-sin-fuga/scripts/verificar_division.py" splits/manifest.csv \
    --grupos palma_id,lote,finca --col-fecha fecha --temporal --imagenes data/raw
```

- Sale con **1** si una imagen, palma, lote o finca aparece en más de un split, si hay archivos idénticos en splits distintos, o (con `--temporal`) si el test no es posterior.
- Sale con **2** si falta una columna, una fecha es ilegible o `--imagenes` no encuentra ninguna imagen.
- Guarda en el manifiesto una columna `sha256` (el hash de cada imagen, calculado al crearlo) e inclúyela en
  `--grupos`: así los duplicados se detectan aunque las imágenes no estén, como en CI.
- Columnas con otros nombres: `--col-imagen`, `--col-split`, `--grupos`, `--split-prueba`.
- Quita `finca` de `--grupos` solo si el uso previsto es dentro de las mismas fincas, y dilo en el reporte.

Para que ningún cambio rompa la división, llévalo a la CI del repo: copia el script al repo (por ejemplo
`tools/verificar_division.py`), porque `${CLAUDE_PLUGIN_ROOT}` solo existe en tu máquina, y en CI usa la columna
`sha256` en `--grupos` en vez de `--imagenes`.

## 4. Checklist de fuga (Kapoor & Narayanan 2023)

- [ ] ¿Algún preprocesamiento usó estadísticas de val/test?
- [ ] ¿Hay casi duplicados entre splits (vuelos solapados, fotos en ráfaga)?
- [ ] ¿Alguna feature codifica lote, finca, fecha o sensor?
- [ ] ¿El test es "del pasado" respecto a train?
- [ ] ¿La etiqueta viene del censo de campo o de mirar la misma imagen?
- [ ] ¿Se reportan métricas por finca y el peor caso, no solo el promedio?

## Cuándo no hace falta tanto

En un prototipo de una tarde para ver si la señal existe, basta con agrupar por palma. Antes de comparar modelos, publicar números o decidir algo de negocio, aplica todo lo anterior.

## Referencias
- Kattenborn et al. 2022, *ISPRS Open J.*: CV aleatoria infla CNN en teledetección hasta 28 %.
- Roberts et al. 2017, *Ecography*: validación cruzada en bloques para datos con dependencia.
- Ploton et al. 2020, *Nat. Commun.*: con validación espacial, mapas "buenos" no predecían.
- Kapoor & Narayanan 2023, *Patterns*: taxonomía de fuga, 294+ papers afectados.
- Dataset UAV Ganoderma v2 (BINUS, 2026, CC BY 4.0): ejemplo de split sin solapamiento de bloque ni palma.
