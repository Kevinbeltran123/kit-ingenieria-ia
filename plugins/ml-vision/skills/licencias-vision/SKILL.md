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
| RF-DETR Nano–Large, RF-DETR-Seg | Apache-2.0 | Sí | Instalar `rfdetr` **sin** el extra `[plus]` |
| RF-DETR `[plus]` (XL/2XL) | Licencia propia de Roboflow | Revisar | El hook de este plugin lo bloquea sin aprobación |
| supervision, timm | MIT / Apache-2.0 | Sí | |
| DINOv3 | Licencia propia de Meta (DINOv3 License) | Con restricciones | Incluir el texto de la licencia; revisar usos prohibidos |
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
