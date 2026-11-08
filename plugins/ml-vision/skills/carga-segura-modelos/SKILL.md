---
name: carga-segura-modelos
description: Reglas para descargar, cargar y guardar pesos de modelos sin ejecutar código ajeno (pickle). Úsala al escribir código con torch.load, pickle, joblib, from_pretrained, hf_hub_download, timm, checkpoints, o al revisar dependencias de ML. Model security, safetensors, weights_only, trust_remote_code, fickling.
---

# Carga segura de modelos

Un archivo `.pt`, `.pth`, `.pkl`, `.bin` o `.ckpt` es pickle: **cargarlo puede ejecutar código arbitrario**. Los escáneres de pickle (picklescan, ModelScan, el del Hub) se evaden (USENIX Security '26). La defensa es no cargar pickle de fuentes no controladas.

## Reglas

1. **`torch>=2.6`** en `pyproject.toml`. Hasta 2.5.1, `weights_only=True` tenía un RCE (CVE-2025-32434).
2. **Guardar en safetensors** (`safetensors.torch.save_file`) u ONNX. Los checkpoints de entrenamiento (optimizador, estado) solo dentro del bucket propio.
3. **Cargar con `weights_only=True`** cuando no haya alternativa a `torch.load`:
   ```python
   state = torch.load(ruta, map_location="cpu", weights_only=True)
   ```
4. **Hugging Face / timm con revisión fija** (hash de commit, no `main`) y safetensors:
   ```python
   model = AutoModel.from_pretrained("facebook/dinov3-vitb16-pretrain-lvd1689m",
                                     revision="<sha del commit>", use_safetensors=True,
                                     trust_remote_code=False)
   ```
5. **Nunca `trust_remote_code=True`** con repos de terceros. Si un modelo lo exige, copia y revisa su código en el repo propio.
6. **`pickle.load` / `joblib.load`** solo sobre archivos generados por el propio pipeline y guardados en almacenamiento propio.
7. **Fuentes:** Hub de organizaciones conocidas (facebook, timm, roboflow), con la revisión anotada en el código o en un `models.lock`.

## Verificación

Busca patrones inseguros antes de dar el cambio por terminado:

```bash
grep -rnE "torch\.load\(|pickle\.loads?\(|joblib\.load\(|trust_remote_code[[:space:]]*=[[:space:]]*True|revision[[:space:]]*=[[:space:]]*['\"]main['\"]" --include='*.py' .
```
Cada `torch.load` que aparezca debe llevar `weights_only=True` o un comentario que justifique la excepción.

En CI, como segunda capa (no como garantía):

```bash
uvx fickling --check-safety modelos/*.pt
```

Revisa también que `torch` en `uv.lock` sea ≥ 2.6.

## Excepciones

Un checkpoint propio, recién generado en la misma máquina o en un bucket con acceso restringido, se puede cargar con `weights_only=False` si contiene objetos que lo exigen. Déjalo comentado en el código con el motivo.
