# Contrato de «En vivo»

«En vivo» muestra lo que los agentes producen mientras lo producen: imágenes, curvas de entrenamiento, la página que
se modifica, el código que se edita y los documentos que se escriben. Sirve para cualquier proyecto registrado en la
flota (`~/.local/state/flota/corridas.json`).

## Piezas
| Archivo (en `scripts/`) | Dueño | Qué hace |
| --- | --- | --- |
| `vivo.py` | núcleo | Arma el contexto, llama a los detectores con caché, ordena y decide qué archivos se pueden servir |
| `vivo_registro.py` | detector | Lee los registros de sesión de Claude: archivos escritos/editados (`codigo`) y comandos (`comando`) |
| `vivo_imagenes.py` | detector | Imágenes nuevas agrupadas por carpeta (`imagenes`) |
| `vivo_metricas.py` | detector | CSV de métricas, su log y tareas de pueue (`metricas`) |
| `vivo_web.py` | detector | Servidores de desarrollo escuchando en localhost que pertenecen a un proyecto (`web`) |
| `vivo_documentos.py` | detector | Documentos .md y .html que cambian (`documento`) |
| `vivo-<tipo>.js` | vista | Cómo se dibuja cada tipo en la página (`vivo.html`) |

## Python (biblioteca estándar, compatible con 3.9)
- Cada detector expone `detectar(ctx: dict) -> list[dict]` y nada más es obligatorio. No lanza excepciones hacia
  afuera por un archivo raro: lo salta. Debe tardar menos de ~300 ms con raíces normales (no recorrer `.git`,
  `node_modules`, `.venv`, `__pycache__`, `.mypy_cache`, `.ruff_cache`; tope de entradas recorridas).
- `ctx` (lo arma `vivo.contexto()`):
  ```python
  {
      "ahora": 1794950000.0,  # epoch
      "desde": 1794946400.0,  # ventana: solo cosas que cambiaron después de esto (por defecto, la última hora)
      "proyectos": {"appalma-modelo": {"repo": "/abs/repo", "run": "/abs/repo-flota"}},
      "agentes": [  # carriles y coordinadores conocidos
          {
              "nombre": "palma-diseno",
              "proyecto": "appalma-modelo",
              "cwd": "/abs/worktree",
              "sesion_agente": "uuid-o-None",
              "tipo": "claude",
          },
      ],
      "raices": [  # carpetas a vigilar, ya resueltas y sin repetir
          {"ruta": "/abs/repo", "proyecto": "appalma-modelo", "agente": None},
          {"ruta": "/abs/repo-flota/wt/palma-diseno", "proyecto": "appalma-modelo", "agente": "palma-diseno"},
          {"ruta": "/abs/repo-flota", "proyecto": "appalma-modelo", "agente": None},
      ],
  }
  ```
  Una raíz de worktree está DENTRO de la carpeta de la corrida: al recorrer la corrida, salta `wt/` (cada worktree ya
  es su propia raíz con su agente).
- Un producto es un dict serializable a JSON:
  ```python
  {
      "id": "imagenes:/abs/runs/e004/recortes",  # estable entre consultas (tipo + algo único)
      "tipo": "imagenes",  # imagenes | metricas | web | codigo | comando | documento
      "proyecto": "appalma-modelo",
      "agente": "palma-diseno",  # o None si no se sabe
      "t": 1794949990.0,  # último cambio (epoch)
      "titulo": "312 recortes en runs/e004/recortes",  # una línea legible
      "datos": {...},  # según el tipo (abajo)
  }
  ```
- `datos` por tipo (rutas absolutas siempre):
  - `imagenes`: `{"carpeta", "total", "nuevas", "recientes": [rutas, hasta 12, la más nueva primero]}`
  - `metricas`: `{"archivo", "x": "epoch"|"step"|"fila", "series": {col: [números, hasta 500]}, "ultima": {col: n},
    "progreso": {"actual": n, "total": m} | None, "log": [últimas 15 líneas] | [], "errores": int}`
  - `web`: `{"url": "http://127.0.0.1:5173/", "puerto": 5173, "cwd", "ultimo_cambio": epoch | None,
    "archivos": [rutas cambiadas recientes, hasta 8]}`
  - `codigo`: `{"archivo", "mas": n, "menos": n, "fragmento": diff unificado recortado a 60 líneas, "herramienta": "Edit"|...}`
  - `comando`: `{"comando", "resultado": últimas 20 líneas, "ok": True|False|None, "duracion": s | None}`
  - `documento`: `{"archivo", "formato": "md"|"html", "tamano": bytes, "lineas": n}`
- Pruebas con pytest en `plugins/flota/tests/test_vivo_<tipo>.py`, con carpetas y archivos falsos en `tmp_path`.
  Nada de red ni de herdr real. Importa con `sys.path` apuntando a `scripts/` (como `ayudas_flota.py`).

## JavaScript (sin librerías, sin red)
Cada `vivo-<tipo>.js` se carga después de `vivo.html` y registra su vista:
```js
FlotaVivo.registrar("imagenes", {
  // Tarjeta compacta del feed (alto contenido). Devuelve un Node.
  resumen(producto, ctx) { ... },
  // Vista grande al hacer clic (panel derecho). Devuelve un Node. Opcional.
  detalle(producto, ctx) { ... },
});
```
`ctx` trae: `ctx.h(tag, attrs, ...hijos)` (crea elementos; nunca uses innerHTML con datos), `ctx.archivo(ruta)` (URL
para pedir un archivo al servidor, ya con token), `ctx.hace(t)` (texto «3m»), `ctx.api(ruta)` (fetch con token,
devuelve JSON). Usa las variables CSS del tablero (`--texto`, `--tenue`, `--suave`, `--borde`, `--panel`,
`--panel2`, `--trabajando`, `--espera`, `--listo`, `--puerta`) y la clase `.chip`. Sin colores fijos.

## Servir archivos
`GET /api/vivo/archivo?ruta=<abs>` solo entrega archivos bajo una raíz del contexto y con extensión permitida
(png, jpg, jpeg, webp, gif, md, txt, csv, json, log, html). El HTML va con `Content-Security-Policy: sandbox`.
