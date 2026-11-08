# Ficha del dataset: <nombre>

## Origen
- **Fincas / regiones:** <lista, con coordenadas aproximadas si se pueden compartir>
- **Fechas de captura:** <rango y número de vuelos o jornadas>
- **Sensor y plataforma:** <dron, cámara, RGB/multiespectral/térmico, altura de vuelo, GSD en cm/px>
- **Cultivar:** <E. guineensis, híbrido OxG, edad de las palmas>
- **Quién capturó y con qué protocolo:** <...>

## Etiquetas
- **Taxonomía:** <p. ej., escala ICA de PC (Res. 092771 de 2021): grado 0 sana, grados 1–5, cráter y hoja clorótica; recuperada aparte>
- **Origen de la etiqueta:** censo de campo / inspección visual de la imagen / mixto
- **Quién etiquetó y cómo se revisó:** <agrónomo, técnico, doble anotación, acuerdo inter-anotador>
- **Qué significa "negativo":** <sana confirmada en campo vs. sin hallazgo>

## Composición
| Clase | Imágenes | Palmas | Lotes | Fincas |
|---|---|---|---|---|
| <...> | <...> | <...> | <...> | <...> |

## Versionado
- **Ubicación:** <s3://..., remoto DVC>
- **Hash DVC / checksums SHA-256:** <...>
- **Manifiesto y split:** <splits/manifest.csv, hash>
- **Duplicados:** <método de deduplicación y cuántos se quitaron>

## Licencia y permisos
- **Licencia:** <interna / CC BY 4.0 / convenio con ...>
- **Datasets externos incluidos y su cita:** <...>
- **Restricciones:** <datos de fincas de terceros, ubicación sensible>

## Límites y sesgos conocidos
- <Estaciones, horarios, condiciones climáticas no cubiertas>
- <Clases con pocos ejemplos>
- <Diferencias de sensor entre fincas>
