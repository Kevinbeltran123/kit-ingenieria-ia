---
name: licencias-vision
description: Licencias de modelos, librerías y datasets de visión por computador y qué implican para un producto comercial o cerrado. Úsala al elegir un detector o backbone (YOLO/Ultralytics, RF-DETR, SAM, DINOv3), al agregar dependencias de visión, al usar datasets públicos o cuando el hook de licencias bloquee una instalación. AGPL, Apache-2.0, model license, commercial use.
---

# Licencias en visión por computador

Esto no es asesoría legal: la decisión final es del área legal de la empresa. La skill sirve para detectar el riesgo a tiempo y dejarlo documentado.

## Tabla de referencia (verificada 2026-11)

| Componente | Licencia | Producto cerrado | Nota |
|---|---|---|---|
| Ultralytics (YOLOv8/11/26) | AGPL-3.0 | Requiere licencia Enterprise | Según su FAQ, los **pesos entrenados** también quedan bajo AGPL. Servirlo por red obliga a publicar el código. |
| RF-DETR Nano–Large (detección) y RF-DETR-Seg (todos los tamaños) | Apache-2.0 | Sí | Instalar `rfdetr` **sin** el extra `[plus]` |
| RF-DETR Atto, Femto, Pico, XL y 2XL de detección (`rfdetr[plus]`) | Roboflow PML 1.0 | Solo con plan de Roboflow; autoalojado comercial exige el add-on Enterprise | El hook de este plugin lo bloquea sin aprobación |
| supervision | MIT | Sí | |
| timm | Código Apache-2.0; los pesos, según el modelo | Revisar los pesos | Su README advierte que los pesos entrenados en ImageNet heredan su uso solo para investigación, y algunos de Facebook son CC-BY-NC 4.0: mira la licencia en la ficha de cada modelo |
| DINOv3 | DINOv3 License (Meta) | Sí, con usos prohibidos | Permite uso comercial; prohíbe usos bajo ITAR y fines militares, nucleares, de espionaje o de armas. Incluir el texto de la licencia al redistribuir |
| SAM 2 | Apache-2.0 | Sí | |
| SAM 3 | Licencia propia de Meta (SAM License) | Con restricciones | Útil para pre-anotación; revisar antes de desplegar |
| FiftyOne, Label Studio, CVAT | Apache-2.0 / MIT | Sí (autoalojados) | Versiones empresariales aparte |
| Datasets Mendeley CC BY 4.0 | CC BY 4.0 | Sí, con atribución | Citar en la ficha del dataset |
| PlantVillage, PlantDoc | Varias | Revisar | Además, no transfieren bien a campo |

## Procedimiento

1. Antes de agregar un modelo o librería de visión, ubícalo en la tabla o busca su `LICENSE` en el repo oficial (`gh api repos/<owner>/<repo>/license`).
2. Si es AGPL, licencia propia o desconocida y el producto es cerrado o se sirve como servicio: propone la alternativa Apache/MIT y escala la decisión a la persona.
3. Si legal aprueba, registra la aprobación en `LICENSES.md` en la raíz del repo:
   ```markdown
   - APROBADO: ultralytics — licencia Enterprise n.º 123, aprobado por <persona/área> (2026-11-07)
   ```
   El hook `licencias` de este plugin solo deja agregar `ultralytics` o `rfdetr[plus]` si existe esa línea.
4. Lista en la ficha del modelo (`ficha-modelo`) la licencia del backbone, de los pesos base y de cada dataset usado.

## Verificación

```bash
uv tree | grep -iE "ultralytics|rfdetr"           # dependencias directas y transitivas
grep -iE "APROBADO:" LICENSES.md                  # aprobaciones registradas
```
Si aparece un paquete restringido sin aprobación, el cambio no está terminado.
