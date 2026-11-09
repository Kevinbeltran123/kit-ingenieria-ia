# python-ingenieria

Skills de ingeniería para repos Python (backend, datos, ML). Sin hooks: solo instrucciones y scripts que Claude carga cuando la tarea lo pide.

| Skill | Cuándo se usa | Script |
|---|---|---|
| `arquitectura-python` | Crear un servicio, ubicar código, refactorizar acoplamiento. Hexagonal pragmática con contratos de import-linter. Reemplaza a `software-architecture`. | — |
| `deuda-tecnica` | Limpiar código muerto, dependencias sin usar, complejidad y duplicados en PRs pequeños. | `deuda.py`: informe markdown |
| `documentacion-python` | Docstrings Google, ADR (MADR 4), README de servicio, Mermaid/C4, Zensical. Reemplaza a `write-concisely` para docs técnicas. | — |
| `rendimiento-python` | Algo está lento, o se va a reportar una mejora medida: py-spy/scalene, patrones N+1, async, Polars, y 7 preguntas antes de dar un número. | — |
| `calidad-pruebas` | Escribir o revisar pruebas; gate de mutación con mutmut sobre el diff. | `mutantes_del_diff.py` |
| `cadena-suministro-python` | Agregar dependencias, revisar CVE, secretos y workflows. | `suministro.py` |

Complementa a `calidad-python` (hooks + skill `verify`), que conviene tener activo en el mismo repo.

## Límites
- Los scripts corren las herramientas que encuentren (`.venv/bin` o PATH) y avisan de las que faltan; no instalan nada.
- `deuda.py` es un informe: vulture y jscpd dan falsos positivos, revísalos antes de borrar.
- Los umbrales (complejidad 15, mutación 80 %) son puntos de partida; ajústalos por repo.

## Origen
Las 7 preguntas de `rendimiento-python` están adaptadas de `benchmark-checklist` de pstack (cursor/plugins,
commit `6b0300214a09fd6029cfb7077043125758cd1fd2`, MIT, © 2026 Lauren Tan): ver `LICENSE-pstack`.

## Probar
    python3 -m pytest tests -q
