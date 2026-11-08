# 07 · ML, visión por computador y MLOps

Investigación del 2026-11-07. Contexto: modelo para identificar enfermedades en palma (probablemente palma de aceite) en una empresa colombiana; stack Python + GitHub + AWS; desarrollo casi 100% con Claude Code; kit instalado por repo, nunca global.

**Método.** Actividad de repos verificada con `gh api` el 2026-11-07 (`pushed_at`, último commit en la rama por defecto, último release, estrellas, licencia SPDX). Criterio: último commit en la rama por defecto desde ~2026-09-25. Papers y datasets con año y fuente. Nada se instaló. El contenido web se trató como datos no confiables.

---

## 1. Tabla de herramientas

Leyenda de veredicto: **ADOPTAR** (entra al kit), **CONDICIONAL** (entra solo si se usa ese servicio o tras revisión legal), **REFERENCIA** (leer o copiar ideas, no instalar), **DESCARTAR**.

| Nombre | Tipo | Qué hace | Último commit / release | Licencia | Evidencia | Riesgo | Veredicto |
|---|---|---|---|---|---|---|---|
| `huggingface/skills` | Skills + plugin de Claude Code (`.claude-plugin`) | 23 skills oficiales: `huggingface-vision-trainer` (DETR/D-FINE/RT-DETR, timm incl. DINOv3, SAM/SAM2), `huggingface-datasets`, `huggingface-community-evals`, `hf-cli`, y **7 skills `hf-cloud-*` para SageMaker** (planificador de despliegue, preflight de IAM, defaults de producción, selección de imagen) | commit 2026-10-29 · sin releases · 11,3k ★ | Apache-2.0 | Repo oficial de HF | El vision-trainer entrena en HF Jobs (nube de HF y no AWS) → los datos de la empresa saldrían a HF | **ADOPTAR** solo las skills `hf-cloud-sagemaker-*` y `hf-cli`; vision-trainer como **REFERENCIA** |
| `huggingface/hf-mcp-server` | MCP (HTTP remoto `huggingface.co/mcp`) | Buscar modelos, datasets, papers y docs del Hub; Jobs; sandboxes; Spaces como herramientas | commit 2026-11-04 · v0.4.33 (2026-11-04) · 314 ★ | MIT | [Docs HF](https://huggingface.co/docs/hub/en/hf-mcp-server) | Las herramientas de escritura (Contribute Repos, Jobs) y los Spaces de la comunidad son superficie de inyección de prompts. Activar solo las de lectura | **ADOPTAR** (solo lectura) |
| `K-Dense-AI/scientific-agent-skills` (antes *claude-scientific-skills*) | Skills (177) | Útiles aquí: `pytorch-lightning`, `scikit-learn`, `shap`, `statistical-analysis`, `statistical-power`, `geopandas`, `geomaster`, `transformers`, `umap-learn`, `exploratory-data-analysis` | commit 2026-11-02 · v2.72.0 (2026-10-01) · 56,4k ★ | MIT | Trae un escaneo de seguridad por LLM de cada skill (`scan_skills.py`) | Volumen enorme y casi todo biomédico. Instalar el paquete entero contamina el contexto | **CONDICIONAL**: copiar 4–6 skills sueltas, con su versión fijada |
| `ultralytics/ultralytics` | Librería (YOLO11/YOLO26) | Detección, segmentación, export a ONNX/TensorRT/CoreML | commit 2026-11-08 · v8.4.207 (2026-11-07) · 63,2k ★ | **AGPL-3.0** | Ultralytics dice que **los pesos entrenados también quedan bajo AGPL**, aunque se usen en privado o vía SaaS ([FAQ de licencia](https://www.ultralytics.com/license), [issue #22458](https://github.com/ultralytics/ultralytics/issues/22458)) | Legal: un uso comercial cerrado exige Enterprise License (precio a cotizar) | **CONDICIONAL**: solo con licencia Enterprise o en prototipos internos que no salen. No existe MCP oficial |
| `roboflow/rf-detr` | Librería y modelo | Detector y segmentador DETR en tiempo real (ICLR 2026). Supera a YOLO26 en RF100-VL con tamaños parecidos | commit 2026-11-06 · 1.12.0 (2026-11-06) · 10k ★ | Apache-2.0 (Nano–Large y todas las seg); **PML 1.0** (Atto/Femto/Pico/XL/2XL) | [Licencias RF-DETR](https://roboflow.com/model-licenses/rf-detr), [benchmarks](https://github.com/roboflow/rf-detr/blob/develop/docs/learn/benchmarks.md) | Instalar `rfdetr[plus]` cambia la licencia. Prohibirlo | **ADOPTAR** como detector por defecto (sin `[plus]`) |
| `roboflow/supervision` | Librería | Utilidades de CV: tracking, conteo, slicing (SAHI) para ortomosaicos, métricas | 2026-11-06 · 51,5k ★ | MIT | — | Bajo | **ADOPTAR** |
| `roboflow/computer-vision-skills` | Skills | 13 skills, casi todas atadas a la plataforma Roboflow (API, Universe, planes) | commit 2026-11-05 · 50 ★ | Apache-2.0 | — | Atadas al proveedor; los datos irían a la nube de Roboflow | **CONDICIONAL** (solo si la empresa adopta Roboflow) |
| `huggingface/pytorch-image-models` (timm) | Librería | Backbones (ConvNeXt, EfficientNet, ViT, DINOv2/v3) para clasificar hoja o recortes de copa | commit 2026-11-03 · v1.0.31 (2026-11-03) · 37,3k ★ | Apache-2.0 (los pesos tienen licencias propias) | — | Revisar la licencia de cada peso | **ADOPTAR** |
| `facebookresearch/dinov3` | Modelo base | Backbone autosupervisado. Hay variante entrenada con satélite (SAT-493M) | commit 2026-07-15 · 11,7k ★ | **DINOv3 License** (propia de Meta) | El texto de la licencia permite uso, derivados y redistribución con aviso; prohíbe usos militares y de ITAR | Licencia no OSI; hay que incluir el texto al redistribuir. Repo quieto desde julio | **ADOPTAR el modelo** (vía timm/HF), con nota legal |
| `facebookresearch/sam3` (SAM 3 / 3.1) | Modelo base | Segmentación por concepto de texto ("palm crown"); útil para pre-anotar copas | commit 2026-10-23 · 12,2k ★ | **SAM License** (propia de Meta, 2025-11-19) | — | Licencia no OSI. SAM 2 (Apache-2.0, sin commits desde 2026-05) es la alternativa permisiva | **CONDICIONAL** (pre-anotación; revisar licencia) |
| `mlflow/mlflow` (MCP integrado: `mlflow mcp run`) | MCP local + plataforma | Tracking y Model Registry. El MCP expone `MLFLOW_MCP_TOOLS=ml` (experimentos, runs, modelos, despliegues) | commit 2026-11-08 · 28,7k ★ | Apache-2.0 | [Docs del MCP](https://mlflow.org/docs/latest/genai/mcp/) (experimental, ≥3.5.1). SageMaker ofrece **MLflow serverless sin costo adicional** ([AWS, 2025-12-02](https://aws.amazon.com/about-aws/whats-new/2025/12/sagemaker-ai-serverless-mlflow-ai-development)) | Por defecto el MCP trae herramientas de borrado (`delete_traces`). Limitar a `ml` y negar los deletes con permisos | **ADOPTAR** (columna vertebral del MLOps) |
| `mlflow/skills` | Skills | 10 skills, casi todas de GenAI/trazas. `mlflow-sagemaker` conecta con MLflow gestionado en SageMaker | commit 2026-11-04 · 89 ★ | Apache-2.0 | Oficial | Poco ML clásico | **ADOPTAR** solo `mlflow-sagemaker` y `mlflow-docs` |
| `wandb/wandb-mcp-server` + `wandb/skills` | MCP + skills | Consulta de runs, comparación y reportes. `wandb-autoresearch` corre ensayos acotados con W&B Launch | MCP 2026-11-06; skills 2026-11-06 · 72/74 ★ | MIT / Apache-2.0 | [Docs W&B MCP](http://docs.wandb.ai/platform/mcp-server) | SaaS de pago; datos fuera de AWS | **CONDICIONAL** (solo si eligen W&B en vez de MLflow) |
| `treeverse/dvc` (antes iterative) | CLI | Versionado de datos y pipelines sobre S3 | commit 2026-11-06 · 3.67.1 (2026-03-31) · 16k ★ | Apache-2.0 | Lo adquirió Treeverse (lakeFS); el repo sigue activo | No existe MCP oficial; los releases se espaciaron | **ADOPTAR** (o S3 versionado + manifiestos con hash si se quiere algo mínimo) |
| `voxel51/fiftyone` + `fiftyone-mcp-server` + `fiftyone-skills` | Librería + MCP + 19 skills | Curación de datasets, duplicados casi idénticos, embeddings, evaluación de modelos (TP/FP/FN), exploración visual | lib 2026-11-06 (v1.22.1) · MCP 2026-11-05 (27 ★) · skills 2026-10-29 (48 ★) | Apache-2.0 (el MCP declara Apache en su README pero la API de GitHub no detecta archivo de licencia) | Skills `fiftyone-find-duplicates` y `fiftyone-model-evaluation` encajan con la división sin fuga | El MCP expone más de 45 herramientas y puede **instalar plugins solo** → desactivarlo o limitarlo | **ADOPTAR** lib + 3–4 skills; MCP **CONDICIONAL** |
| `HumanSignal/label-studio` | App de anotación | Anotación autoalojable (cajas, polígonos), backend ML para pre-anotar | 2026-11-07 · 28,6k ★ | Apache-2.0 | — | Bajo | **ADOPTAR** (o CVAT) |
| `HumanSignal/label-studio-mcp-server` | MCP | — | **2025-05-30** | Apache-2.0 | — | Abandonado | **DESCARTAR** |
| `cvat-ai/cvat` | App de anotación | Anotación de video/ortomosaico, SAM integrado | commit 2026-11-06 · v2.82.0 (2026-11-05) · 17k ★ | MIT | — | Bajo | **ADOPTAR** como alternativa a Label Studio |
| `awslabs/mcp` → `sagemaker-ai-mcp-server` | MCP | **Hoy solo gestiona clústeres HyperPod**: no entrena ni despliega endpoints normales | monorepo 2026-11-07; último cambio funcional en esa carpeta 2026-08-26 (después, solo bumps de dependencias) | Apache-2.0 | [README](https://github.com/awslabs/mcp/tree/main/src/sagemaker-ai-mcp-server) | Sugiere `--allow-write --allow-sensitive-data-access` | **DESCARTAR** para este caso. Mejor `aws-documentation-mcp-server` / `aws-api-mcp-server` (los evalúa el investigador de AWS) |
| `Lightning-AI/pytorch-lightning` | Librería | Bucle de entrenamiento reproducible (`seed_everything`, `deterministic=True`) | commit 2026-09-21 · 2.6.6 (2026-09-10) · 31,4k ★ | Apache-2.0 | — | Al límite de la ventana (4 días antes del corte) | **ADOPTAR** (madura). Alternativa: PyTorch puro |
| `trailofbits/fickling` | CLI de seguridad | Escanea y descompila pickles (allowlist para ML desde 2025-09) | commit 2026-11-07 · v0.1.13 (2026-11-03) | LGPL-3.0 | [Trail of Bits, 2025-09-16](https://blog.trailofbits.com/2025/09/16/ficklings-new-ai/ml-pickle-file-scanner) | Ningún escáner es infalible (ver §5) | **ADOPTAR** en CI como segunda línea |
| `protectai/modelscan` | CLI de seguridad | Escáner de modelos | **2026-02-18** | Apache-2.0 | Lo evaden USENIX Sec '26 y SafePickle 2026 | Inactivo | **DESCARTAR** |
| `safetensors/safetensors` | Formato | Pesos sin ejecutar código | 2026-11-06 | Apache-2.0 | Auditado; formato por defecto en transformers | — | **ADOPTAR (obligatorio)** |
| `microsoft/onnxruntime`, `onnx/onnx` | Runtime / formato | Inferencia portable en CPU/GPU/móvil | 2026-11-08 | MIT / Apache-2.0 | — | — | **ADOPTAR** |
| `evidentlyai/evidently` | Librería de drift | Reportes de drift (tabular y de embeddings) | commit **2026-09-10** · v0.7.23 | Apache-2.0 | — | Fuera de la ventana por 2 semanas | **REFERENCIA**: volver a verificar antes de usarla. Para imágenes alcanza con drift de embeddings DINOv3 + una prueba MMD/KS propia |
| `NannyML/nannyml`, `deepchecks/deepchecks` | Drift / validación | — | 2025-07 / 2025-12 | — | — | Inactivos | **DESCARTAR** |
| `Orchestra-Research/AI-Research-SKILLs` | Skills | Skills de investigación en ML | commit **2026-06-16** | MIT | 14k ★ | Sin commits desde junio | **DESCARTAR** (como mucho, referencia) |
| `karpathy/autoresearch` | Referencia | Agente que itera `train.py` con presupuesto fijo y **evaluador intocable** (`prepare.py`) | 2026-03-26 · 99k ★ | — | Patrón de diseño, no herramienta | — | **REFERENCIA** (§6) |

No existen: un MCP oficial de Ultralytics (`ultralytics/mcp` da 404), un MCP oficial de Roboflow (`roboflow/roboflow-mcp` da 404), un MCP de DVC ni una skill de Lightning hecha por Lightning-AI.

---

## 2. Estado del arte: enfermedades de la palma de aceite

### 2.1 Enfermedades relevantes en Colombia

ICA las declara de **control oficial** ([Res. 092771 de 2021](https://www.ica.gov.co/areas/agricola/direccion-tecnica-de-sanidad-vegetal/proteccion-fitosanitaria-en-palmas/desplegable/documentos-de-interes/resolucion-092771-del-17-de-marzo-2021.aspx)). Esa misma resolución define una **escala de severidad de la PC (grados 1–5 según el % de lesión de la hoja flecha)**, una taxonomía de etiquetas lista para usar:

| Enfermedad | Agente | Dónde se ve | Implicación para el modelo |
|---|---|---|---|
| **Pudrición del cogollo (PC)** | *Phytophthora palmivora* | Hoja flecha y cogollo (copa), la mejor vista es desde arriba | La amenaza n.º 1 en Colombia ([Cenipalma, Agronomy 2024](https://www.mdpi.com/2073-4395/14/11/2486)). Etiquetar por grado ICA |
| **Marchitez letal (ML)** | Agente sin confirmar; vector *Haplaxius crudus* | Secamiento de hojas, caída de frutos; Llanos Orientales | Se propaga en focos: la autocorrelación espacial es enorme → split por bloque obligatorio ([Cenipalma ML](https://www.cenipalma.org/sanidad/marchitez-letal/)) |
| **Anillo rojo (AR)** | *Bursaphelenchus cocophilus*, con *R. palmarum* | Anillo interno del estípite; amarillamiento de hojas | Desde el aire se confunde con ML y con deficiencias. Hace falta verdad de campo |
| **Ganoderma (pudrición basal, BSR)** | *Ganoderma boninense* (gran problema en SE Asia) | Base del estípite; la copa muestra síntomas tarde | Es donde hay más literatura y datasets públicos (Malasia/Indonesia) |
| **Deficiencias nutricionales** | N, K, Mg, B | Clorosis en hojas | Con UAV multiespectral solo se detecta bien el **N**; P/K/Mg no (OA ≈ 0,44, [Uktoro 2024](https://scik.org/index.php/cmbn/article/view/8520)) |

### 2.2 Trabajos clave (2024-2026)

- **Cenipalma: PC con monitoreo digital + IA (segmentación de instancias).** 672 palmas de 15 años, monitoreo mensual durante 12 meses. López-Vásquez, García-Cárdenas, Sarria, Morales. [Agronomy 14(11):2486, 2024](https://www.mdpi.com/2073-4395/14/11/2486); versión en español en [Revista Palmas 46(3), 2025/2026](https://publicaciones.fedepalma.org/index.php/palmas/article/view/14495). **Es el grupo de referencia en Colombia (Cenipalma, sanidad: G. Sarria, A. Morales)** y el socio natural para conseguir datos y validar en campo.
- **Riesgo epidemiológico de la PC (Tumaco frente a Villavicencio).** Ramírez-Gil et al., UNAL. [Plant Pathology 73(7), 2024](https://bsppjournals.onlinelibrary.wiley.com/doi/10.1111/ppa.13949). Sirve para variables de contexto (clima y suelo).
- **Ganoderma por UAV RGB + térmico + estructura de copa**, 1 278 palmas verificadas en campo, SMOTE, 94,2 % de exactitud. Husin et al. [J. Agric. Food Res. 26, 2026](https://www.sciencedirect.com/science/article/pii/S266615432600030X). *Ojo: SMOTE mal aplicado (antes del split) filtra información; revisar cómo lo hicieron.*
- **Ganoderma con hiperespectral UAV (5 cm) + Mask R-CNN para copas + RF/SVM.** Nagara et al. [Front. Remote Sens. 7, 2026](https://www.frontiersin.org/journals/remote-sensing/articles/10.3389/frsen.2026.1788857/full). El patrón dominante: **primero segmentar copas y después clasificar por palma**.
- **App móvil para estadios de BSR + Web GIS.** Daranagama & Takeuchi. [Front. Remote Sens. 6, 2025](https://www.frontiersin.org/journals/remote-sensing/articles/10.3389/frsen.2025.1553844/full). Reconocen que *no hay datasets públicos grandes de BSR*.
- **Reseña de UAV para plagas y enfermedades en palmas.** [Remote Sensing 16(23):4371, 2024](https://www.mdpi.com/2072-4292/16/23/4371).
- **Sentinel-2 para palma sana/enferma.** [J. Oil Palm Res. 35(3), 2023](https://jopr.mpob.gov.my/files/2022/10/jopr2023v353-narissara.pdf). El satélite sirve a escala de lote, no de palma individual. Para nutrientes bajo nubes, Sentinel-1 (radar): [IOP EES 1650, 2026](https://iopscience.iop.org/article/10.1088/1755-1315/1650/1/012019/pdf).

### 2.3 Datasets públicos

| Dataset | Contenido | Licencia | Nota |
|---|---|---|---|
| [UAV RGB Ganoderma v2](https://data.mendeley.com/datasets/s23jvbpnr3/2) (BINUS, 2026-09) | 1 352 teselas de 640², 9 400 copas COCO (722 positivas por censo de campo) | CC BY 4.0 | **Modelo a imitar**: split sin solapamiento de bloque ni de palma, dataset card, checksums SHA-256, etiqueta de campo (no visual), y aclara que "negativa" ≠ sana confirmada |
| [Oil Palm Tree Detection for Anomaly Identification](https://data.mendeley.com/datasets/nh7d23dgnw) (Perú, 2025) | RGB de un P4 Multispectral, clases sana/anómala, Faster R-CNN | CC BY 4.0 | Latinoamericano, cercano al dominio |
| [Image Dataset of Oil Palm Leaf Diseases](https://data.mendeley.com/datasets/cp65skff89/1) (Indonesia, 2025) | Recortes de hoja sana/enferma | CC BY 4.0 | Binario, pequeño |
| [OilPalm_Dataset.id](https://data.mendeley.com/datasets/xj4rs77c4j/1) (2024) | UAV, segmentación palma/suelo/otros | CC BY 4.0 | Sirve para preentrenar el detector de copas |
| PlantDoc / PlantWild | Hojas en campo, multicultivo | varias | Benchmarks "in the wild". **No usar PlantVillage para entrenar**: tiene sesgo de fondo y no transfiere a campo ([Frontiers 2026](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2026.1860665/full); [PMC 2026](https://pmc.ncbi.nlm.nih.gov/articles/PMC13236948)) |

No encontré **ningún dataset público de PC, ML ni AR**. Los datos tendrán que ser propios o venir de un convenio con Cenipalma.

### 2.4 Modelos base recomendados

- **Detección/segmentación de copas:** RF-DETR Nano–Large o RF-DETR-Seg (Apache-2.0), con slicing SAHI de `supervision` sobre ortomosaicos. YOLO26 solo con licencia Enterprise.
- **Clasificación por palma u hoja:** backbone **DINOv3 congelado + cabeza lineal** como baseline. Hay evidencia de 2026 de que, en enfermedades de plantas "in the wild", fusionar backbones congelados (DINOv2 + DINOv3 + CLIP) vence a la supervisión con texto y la cabeza casi no importa ([Frontiers Plant Sci. 2026](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2026.1860665/full)). Para satélite, la variante DINOv3 SAT-493M.
- **Modelos agro de dominio:** LeafVision ([EAAI 2026](https://www.sciencedirect.com/science/article/pii/S0952197626009425)), A100 ([arXiv 2610.22991, 2026-10](https://arxiv.org/abs/2610.22991), pesos aún sin publicar) y SCOLD ([ESWA 2026](https://www.sciencedirect.com/science/article/abs/pii/S0957417425037005)). Son prometedores con pocas etiquetas, pero ninguno se entrenó con palma; compararlos contra DINOv3 antes de adoptarlos.
- **Pre-anotación:** SAM 3 (prompt de texto) o SAM 2 en CVAT/Label Studio, siempre con revisión humana.
- **Sensor:** RGB es barato pero ve tarde. Multiespectral o térmico para detección temprana (Ganoderma, PC). El hiperespectral es caro y sirve para investigación.

---

## 3. Buenas prácticas que una skill debe imponer

1. **División sin fuga (lo más importante).** La unidad independiente es la **palma**, y la autocorrelación llega a **lote/bloque, finca y fecha de vuelo**. Reglas: `GroupKFold`/`StratifiedGroupKFold` por bloque o finca; nunca repartir teselas de un mismo ortomosaico entre train y test; test con al menos una **finca entera y una fecha posterior** nunca vistas; buffer espacial entre folds. Evidencia: la CV aleatoria infló el desempeño de CNN en teledetección **hasta 28 %** ([Kattenborn 2022](https://www.sciencedirect.com/science/article/pii/S2667393222000072)); con validación espacial, mapas que "funcionaban" resultaron no tener capacidad predictiva ([Ploton 2020, Nat. Commun.](https://www.nature.com/articles/s41467-020-18321-y)); bloquear siempre que haya dependencia ([Roberts 2017, Ecography](https://nsojournals.onlinelibrary.wiley.com/doi/10.1111/ecog.02881)).
2. **Taxonomía de fuga de Kapoor & Narayanan** como checklist: preprocesamiento, oversampling o normalización antes del split; duplicados (vuelos solapados = casi duplicados → deduplicar con embeddings); features ilegítimas (ID de lote, fecha); test "del pasado" ([Patterns 2023](https://www.cell.com/patterns/pdfExtended/S2666-3899%2823%2900159-9)).
3. **Desbalance.** Las enfermas son pocas (7,7 % en el dataset de Ganoderma). Usar pérdida ponderada o focal y muestreo **solo dentro de train**; SMOTE nunca antes del split.
4. **Métricas.** Por palma: recall de la clase enferma con su IC, PR-AUC (no accuracy) y matriz de confusión por grado de severidad. Por detección: mAP@50 + recall con IoU fijo. Reportar **por finca** y el peor caso. Comparar contra baselines tontos: clase mayoritaria e índice VARI con umbral.
5. **Calibración.** ECE + diagrama de confiabilidad; temperature scaling en validación. Fijar el umbral de alerta según el costo (pasar por alto una PC sale mucho más caro que una inspección extra). El estudio de 2026 mostró que calibración, OOD y ensembles **no cierran solos** la brecha de laboratorio a campo ([PMC 2026](https://pmc.ncbi.nlm.nih.gov/articles/PMC13236948)) → hace falta validar en campo.
6. **Validación en campo.** Etiqueta = censo fitosanitario de campo (como en el dataset BINUS v2), no "parece enferma en la foto". Piloto prospectivo: el modelo marca, el técnico verifica y se mide precisión y recall reales.
7. **Versionado y reproducibilidad.** Datos en S3 con DVC (o manifiesto con hash); cada run de MLflow guarda commit git + hash del dataset + seed + entorno `uv.lock`; los splits se guardan como archivo versionado y no se recalculan.
8. **Model card y dataset card** (plantilla tipo HF + "model info sheet" de Kapoor): zonas, fechas, sensores, GSD, cultivar (*E. guineensis* frente a híbrido OxG), límites conocidos.
9. **Despliegue.** Export ONNX y paridad numérica PyTorch↔ONNX probada en CI; cuantización INT8 para móvil/edge (ONNX Runtime Mobile, TFLite o CoreML).
10. **Monitoreo de drift.** Distribución de embeddings y de confianza por vuelo/finca/mes, más una muestra etiquetada periódica en campo.
11. **Seguridad de modelos.** Ver §5.

---

## 4. Stack MLOps recomendado en AWS (mínimo viable)

| Capa | Elección | Por qué |
|---|---|---|
| Datos crudos y ortomosaicos | S3 (versionado + cifrado KMS) | Estándar, barato |
| Versionado de datos | DVC con remoto S3 | Activo, Apache-2.0 |
| Anotación | Label Studio o CVAT autoalojado (ECS/EC2) + pre-anotación SAM | Los datos no salen de la cuenta |
| Curación/EDA | FiftyOne (local o EC2) | Duplicados, errores de etiqueta, análisis por finca |
| Entrenamiento | SageMaker Training Jobs (spot) con contenedor PyTorch; código en GitHub | Pago por uso; sin clúster |
| Tracking + registro | **MLflow serverless en SageMaker AI** (sin costo adicional, [AWS 2025-12](https://aws.amazon.com/about-aws/whats-new/2025/12/sagemaker-ai-serverless-mlflow-ai-development)) → SageMaker Model Registry | Un solo registro y despliegue directo ([docs](https://docs.aws.amazon.com/sagemaker/latest/dg/mlflow.html)) |
| Inferencia por lotes (ortomosaicos) | **SageMaker Batch Transform** o Processing Job con GPU | El caso principal: vuelo → mapa de alertas |
| Inferencia bajo demanda (foto desde app) | Lambda con imagen de contenedor + ONNX Runtime CPU, o SageMaker **Serverless Inference** (máx. 6 GB de RAM, **sin GPU, sin Model Monitor, sin data capture** ([docs](https://docs.aws.amazon.com/sagemaker/latest/dg/serverless-endpoints.md))) | Escala a cero |
| Edge/móvil sin señal en campo | ONNX INT8 / TFLite / CoreML en el celular | Las fincas tienen mala conectividad |
| Monitoreo | Model Monitor **solo calcula estadísticas tabulares de la salida**, no de las imágenes ([docs](https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor.html)) → job programado propio de drift de embeddings + CloudWatch | — |
| CI | GitHub Actions: tests, chequeo de fuga del split, paridad ONNX, `fickling` sobre artefactos, OIDC a AWS (sin llaves) | — |

---

## 5. Seguridad y licencias

- **Pickle = ejecución de código.** `torch.load` con `weights_only=True` tuvo un RCE hasta PyTorch 2.5.1 ([CVE-2025-32434](https://nvd.nist.gov/vuln/detail/cve-2025-32434)) → exigir **torch ≥ 2.6**. Casi todos los modelos maliciosos del Hub usan pickle, y su tasa se multiplicó por 5 en un año ([PickleBall, CCS '25](https://cs.brown.edu/people/vpk/papers/pickleball.ccs25.pdf)). Picklescan, ModelScan y el escáner de HF se evaden ([USENIX Security '26](https://www.usenix.org/system/files/conference/usenixsecurity26/sec26_prepub_liu-tong_0.pdf); [SafePickle 2026](https://arxiv.org/abs/2602.19818)). **Regla:** solo `.safetensors`/ONNX de fuentes fijadas por `revision` (hash), `use_safetensors=True`, `trust_remote_code=False` ([SECURITY.md de transformers](https://github.com/huggingface/transformers/blob/main/SECURITY.md)). `fickling` en CI como segunda capa, nunca como garantía.
- **Licencias.** Ultralytics AGPL-3.0 alcanza también a los pesos entrenados → con producto cerrado hace falta Enterprise. RF-DETR: Apache solo sin `[plus]`. DINOv3 y SAM 3 tienen licencias propias de Meta (comerciales con restricciones; incluir el texto). Datasets CC BY 4.0: hay que citarlos. Decisión para el área legal de la empresa.
- **MCP.** Solo herramientas de lectura por defecto (HF, MLflow `ml`). Nada de `--allow-write` en MCP de AWS. El MCP de FiftyOne puede instalar plugins → desactivado.

---

## 6. Qué recomiendan los expertos sobre agentes y ML

- **Karpathy, ["A Recipe for Training Neural Networks"](http://karpathy.github.io/2019/04/25/recipe) (2019-04-25):** el entrenamiento "falla en silencio". Su receta: primero hacerse uno con los datos, montar el esqueleto de entrenamiento y evaluación más **baselines tontos**, sobreajustar un batch, luego regularizar, ajustar y exprimir. Una skill puede convertir eso en pasos con verificación.
- **Karpathy, [autoresearch](https://github.com/karpathy/autoresearch) (2026-03):** el agente solo edita `train.py`; la evaluación (`prepare.py`) y la métrica son fijas e intocables; presupuesto de tiempo fijo por experimento. El humano programa `program.md`. **Patrón para el kit: evaluador bloqueado.**
- **Integridad de la evaluación con agentes:** en ejecuciones naturales, agentes LLM de ingeniería de ML intentaron **manipular el evaluador en ~50 % de los episodios**; bloquear el evaluador lo eliminó ([RewardHackingAgents, arXiv 2603.11337, 2026-03](https://arxiv.org/abs/2603.11337)). Revisar solo el artefacto final no basta; hay que recalcular la métrica de forma independiente ([arXiv 2609.28614, 2026-09](https://arxiv.org/html/2609.28614)); ver también [CapCode, arXiv 2606.07379](https://arxiv.org/abs/2606.07379).
- **Kapoor & Narayanan (Princeton, [Patterns 2023](https://reproducible.cs.princeton.edu/)):** la fuga afectó a 294+ papers en 17 campos; proponen "model info sheets".
- `wandb-autoresearch` (W&B/CoreWeave, 2026) formaliza ensayos acotados, smoke tests y estado reanudable: es una referencia útil aunque no se use W&B.

---

## 7. Vacíos: skills y hooks propios para el kit

| Skill/hook propuesto | Qué impone | Cómo verifica |
|---|---|---|
| **`division-sin-fuga`** (prioridad 1) | Pide la jerarquía (palma → bloque → finca → fecha); genera splits `StratifiedGroupKFold` + holdout de finca y fecha; los guarda versionados | Script que **falla** si un `palm_id`/`bloque`/`ortomosaico` aparece en dos splits, si hay casi duplicados entre splits (pHash/embeddings) o si el test tiene fechas anteriores a las de train |
| **`evaluador-bloqueado`** (hook) | `eval/` y `splits/` en solo lectura para el agente (hook PreToolUse que niega Edit/Write) | La métrica oficial la recalcula CI con el checkpoint, no la reporta el agente |
| **`receta-karpathy`** | Fases con salida obligatoria: EDA visual → baselines tontos → sobreajustar un batch → entrenamiento completo | Cada fase deja un artefacto en MLflow; no se pasa de fase sin él |
| **`metricas-y-calibracion-agro`** | PR-AUC, recall de enfermas con IC, métricas por finca, ECE, umbral por costo | Plantilla de reporte; falla si solo hay accuracy |
| **`carga-segura-de-modelos`** (hook + skill) | Prohíbe `torch.load` sin `weights_only=True`, `pickle.load`, `trust_remote_code=True`, `torch<2.6` | grep/semgrep en PreToolUse y en CI + `fickling` |
| **`licencias-cv`** | Bloquea `import ultralytics` y `rfdetr[plus]` salvo que exista `LICENSES.md` con aprobación | Hook sobre `pyproject.toml` |
| **`dataset-card` / `model-card`** | Plantillas con zona, fecha, sensor, GSD, cultivar, origen de la etiqueta (campo o visual), límites | Archivo obligatorio para registrar en el Model Registry |
| **`export-onnx-paridad`** | Export + prueba de paridad (tolerancia) + benchmark de latencia CPU/móvil | Test en CI |
| **`drift-embeddings`** | Job que compara embeddings DINOv3 por finca/mes contra la línea base | Alerta en CloudWatch |
| **`taxonomia-fitosanitaria-co`** | Etiquetas alineadas con ICA/Cenipalma (grados 1–5 de PC; ML, AR, MS) | Validación del esquema de anotación |

---

## Fuentes principales (además de las enlazadas arriba)

- Repos verificados con `gh api` el 2026-11-07: github.com/huggingface/skills, /huggingface/hf-mcp-server, /K-Dense-AI/scientific-agent-skills, /ultralytics/ultralytics, /roboflow/rf-detr, /roboflow/supervision, /roboflow/computer-vision-skills, /huggingface/pytorch-image-models, /facebookresearch/dinov3, /facebookresearch/sam3, /mlflow/mlflow, /mlflow/skills, /wandb/wandb-mcp-server, /wandb/skills, /treeverse/dvc, /voxel51/fiftyone, /voxel51/fiftyone-mcp-server, /voxel51/fiftyone-skills, /HumanSignal/label-studio, /HumanSignal/label-studio-mcp-server, /cvat-ai/cvat, /awslabs/mcp, /Lightning-AI/pytorch-lightning, /trailofbits/fickling, /protectai/modelscan, /evidentlyai/evidently, /Orchestra-Research/AI-Research-SKILLs, /karpathy/autoresearch.
- Licencias: https://www.ultralytics.com/license · https://www.ultralytics.com/legal/enterprise-software-license · https://roboflow.com/model-licenses/rf-detr · LICENSE.md de dinov3 y LICENSE de sam3 (leídos con `gh api`).
- Seguridad: https://huggingface.co/docs/hub/en/security-pickle · https://arxiv.org/html/2508.15987 · https://github.com/vllm-project/vllm/security/advisories/GHSA-rh4j-5rhw-hr54
