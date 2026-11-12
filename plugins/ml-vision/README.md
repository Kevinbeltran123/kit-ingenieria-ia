# ml-vision

Instalar en un repo: `/plugin install ml-vision --marketplace Kevinbeltran123/kit-ingenieria-ia` (registra el marketplace si hace falta; con `bin/adoptar.py` ya queda en `.claude/settings.json`).

Visión por computador y MLOps para el proyecto de enfermedades en palma (y similares), con foco en que las métricas sean creíbles.

## Skills
| Skill | Para qué |
|---|---|
| `division-sin-fuga` | Diseñar splits por palma/lote/finca/fecha y verificarlos con `scripts/verificar_division.py` (falla si hay fuga). |
| `receta-entrenamiento` | Fases de Karpathy adaptadas: datos → baselines tontos → DINOv3 congelado → regularizar → evaluar por finca → piloto en campo. |
| `carga-segura-modelos` | torch ≥ 2.10, `weights_only=True`, safetensors con revisión fija, sin `trust_remote_code`. |
| `licencias-vision` | AGPL de Ultralytics, RF-DETR sin `[plus]`, DINOv3/SAM 3; cómo registrar aprobaciones. |
| `ficha-modelo` | Plantillas de model card y dataset card con límites de validación en campo. |
| `explicar-resultado` | Explicar un resultado afirmación por afirmación con `scripts/resultado.py`: cada cifra sale de `resultado.json`, con referencia, alcance y lo no comprobado; no deja reportar con un error abierto. |
| `despliegue-vision-aws` | SageMaker spot, MLflow App, Batch Transform, Lambda + ONNX, paridad ONNX, drift de embeddings. |

## Hooks (PreToolUse)
| Hook | Bloquea |
|---|---|
| `evaluador_bloqueado.py` | Editar o escribir (también por Bash: `>`, `rm`, `mv`, `tee`, `sed -i`, `cp` hacia...) en `eval/`, `splits/`, `data/splits/` si existen, o en las rutas de `.claude/ml-vision.json` (`{"rutas_protegidas": [...]}`). Ese archivo también queda protegido: solo lo cambia la persona. Leer está permitido. |
| `licencias.py` | Agregar `ultralytics` o `rfdetr[plus]` a archivos de dependencias (también `requirements/` y el bloque PEP 723 de un script), a un Dockerfile o Containerfile (sus `RUN` y la imagen de `FROM`) o instalarlos o ejecutarlos (pip, uv, uvx, `uv run --with`, pipx, poetry, conda, pixi), salvo línea `APROBADO: <paquete> — ...` en `LICENSES.md`. |

## Límites
- El análisis de Bash es heurístico: cubre los comandos comunes, no un `python -c` que escriba en `eval/` ni un
  comando sobre la carpeta que contiene lo protegido (`mv .claude otra`, `rm -r data`). La métrica oficial la debe recalcular CI, y un cambio en `eval/` o `splits/` lo aprueba una persona: el perfil ml de `bin/adoptar.py` crea `.github/CODEOWNERS` para eso.
- Los hooks no reemplazan la revisión legal ni la de código.

## Probar
    python3 -m pytest tests -q
    claude --plugin-dir ./plugins/ml-vision
