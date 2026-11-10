# Métodos de división (código de referencia)

Todos parten de un `DataFrame` con una fila por imagen y columnas `imagen, clase, palma_id, lote, finca, fecha`.
Después de dividir, escribe `splits/manifest.csv` y corre `verificar_division.py`.

## Nuevas palmas en fincas conocidas: StratifiedGroupKFold por lote

```python
from sklearn.model_selection import StratifiedGroupKFold

sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
df["fold"] = -1
for k, (_, idx) in enumerate(sgkf.split(df, y=df["clase"], groups=df["lote"])):
    df.loc[df.index[idx], "fold"] = k
# Ejemplo: fold 0 = test, fold 1 = val, resto = train.
df["split"] = df["fold"].map(lambda k: "test" if k == 0 else "val" if k == 1 else "train")
```
Agrupar por lote implica agrupar por palma (cada palma pertenece a un solo lote). Verifica que sea cierto en los datos.

## Fincas nuevas: holdout de finca

```python
fincas_test = ["F3"]  # elegir con negocio: representativa, no la "fácil"
test = df[df["finca"].isin(fincas_test)]
resto = df[~df["finca"].isin(fincas_test)]
# Dentro de resto, GroupKFold por finca (si hay ≥3) o StratifiedGroupKFold por lote.
```
Con pocas fincas, haz leave-one-farm-out y reporta cada finca por separado: la varianza entre fincas es el dato importante.

## Hacia adelante en el tiempo

```python
df["fecha"] = pd.to_datetime(df["fecha"])
corte_val, corte_test = pd.Timestamp("2026-06-01"), pd.Timestamp("2026-09-01")
df["split"] = np.select([df.fecha < corte_val, df.fecha < corte_test], ["train", "val"], "test")
# Una palma vista en train puede reaparecer en test en una fecha posterior SOLO si el uso real es
# "seguimiento de las mismas palmas". Si no, además excluye esas palmas del test.
```

## Bloques espaciales con buffer (ortomosaicos)

1. Divide el área en una cuadrícula de bloques más grandes que el rango de autocorrelación (como referencia, varios lotes; estímalo con un variograma de la variable objetivo o de los residuos).
2. Asigna bloques completos a folds.
3. Descarta las teselas a menos de `buffer` metros del borde de un bloque de otro fold.

Con `geopandas`: crea la cuadrícula, haz `sjoin` de los centroides de copa con los bloques y usa el ID de bloque como `groups` en `GroupKFold`.

## Deduplicación antes de dividir

- Exacta: SHA-256 del archivo (el verificador lo hace con `--imagenes`).
- Casi duplicados: embeddings (DINOv3) + similitud coseno > 0,95, o pHash con distancia de Hamming ≤ 4. FiftyOne (`compute_uniqueness`, `compute_near_duplicates`) sirve para revisarlos visualmente.
- Agrupa los casi duplicados en un mismo `grupo_dup` y úsalo también en `--grupos`.

## Desbalance sin fuga

- Pérdida ponderada o focal, o muestreo con reemplazo **solo dentro de train**.
- SMOTE u oversampling nunca antes del split ni sobre val/test.
- Mantén la prevalencia real en val y test: la métrica debe reflejar el campo.
