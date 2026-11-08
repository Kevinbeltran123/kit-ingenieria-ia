---
name: carga-segura-modelos
description: Reglas para descargar, cargar y guardar pesos de modelos sin ejecutar código ajeno (pickle). Úsala al escribir código con torch.load, torch.hub.load, pickle, joblib, from_pretrained, hf_hub_download, timm, checkpoints, o al revisar dependencias de ML. Model security, safetensors, weights_only, trust_remote_code.
---

# Carga segura de modelos

Un archivo `.pt`, `.pth`, `.pkl`, `.bin` o `.ckpt` es pickle: **cargarlo puede ejecutar código arbitrario**. Los escáneres de pickle (picklescan, ModelScan, el del Hub) se evaden (USENIX Security '26). La defensa es no cargar pickle de fuentes no controladas.

## Reglas

1. **`torch>=2.10`** en `pyproject.toml`. `weights_only=True` tuvo dos fallas que permiten ejecutar código al cargar
   un checkpoint: CVE-2025-32434 (hasta 2.5.1) y CVE-2026-24747 (hasta 2.9.1). PyTorch no publica parches para
   versiones viejas.
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
   **Tampoco `torch.hub.load` desde GitHub:** ejecuta el `hubconf.py` del repo, que es lo mismo con otro nombre, y
   PyTorch confía por defecto en algunos dueños (como `facebookresearch`), así que ni pregunta. Para DINOv3 usa
   transformers o timm con revisión fija (en timm, `hf-hub:<org>/<repo>@<sha>`).
6. **`pickle.load` / `joblib.load`** solo sobre archivos generados por el propio pipeline y guardados en almacenamiento propio.
7. **Fuentes:** Hub de organizaciones conocidas (facebook, timm, roboflow), con la revisión anotada en el código o en un `models.lock`.

## Verificación

Busca patrones inseguros antes de dar el cambio por terminado:

```bash
grep -rnE "torch\.load\(|torch\.hub\.load\(|load_state_dict_from_url\(|pickle\.loads?\(|joblib\.load\(|trust_remote_code[[:space:]]*=[[:space:]]*True|revision[[:space:]]*=[[:space:]]*['\"]main['\"]" \
    --include='*.py' --include='*.ipynb' .
grep -rnE "from_pretrained\(|hf_hub_download\(" --include='*.py' --include='*.ipynb' . | grep -v "revision="
```
- Cada `torch.load` debe llevar `weights_only=True` o un comentario que justifique la excepción.
- No debe quedar ningún `torch.hub.load` ni `load_state_dict_from_url` con fuentes de terceros.
- La segunda búsqueda lista descargas sin `revision=`; sin revisión equivale a `main`. Las llamadas que ocupan
  varias líneas pueden salir aquí aunque tengan revisión: revísalas a mano.

En CI, para lo que se despliega: entre los artefactos no debe haber archivos pickle.

```bash
find <carpeta-de-artefactos> -type f \( -name '*.pt' -o -name '*.pth' -o -name '*.pkl' -o -name '*.bin' -o -name '*.ckpt' \)
```
Debe salir vacío: lo que se despliega va en safetensors u ONNX.

Revisa también que `torch` en `uv.lock` sea ≥ 2.10.

## Excepciones

Un checkpoint propio, recién generado en la misma máquina o en un bucket con acceso restringido, se puede cargar con `weights_only=False` si contiene objetos que lo exigen. Déjalo comentado en el código con el motivo.
