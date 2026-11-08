---
name: deuda-tecnica
description: Revisión periódica de deuda técnica en repos Python - código muerto (vulture), dependencias sin usar o faltantes (deptry), complejidad cognitiva (complexipy) y duplicados (jscpd) - con priorización y PRs pequeños de borrado. Úsala cuando pidan limpiar, reducir deuda técnica, quitar código innecesario, "dead code", "unused", "refactor", simplificar un módulo, o en la revisión mensual de un repo.
---

# Deuda técnica

La IA tiende a agregar: código 2,3× más verboso que el humano y que se degrada con cada iteración (SlopCodeBench, 2026). Esta skill hace lo contrario: medir, priorizar y borrar en pasos pequeños y verificables.

## 1. Medir

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/deuda-tecnica/scripts/deuda.py" . --salida informe-deuda.md
```

Corre lo que esté instalado (en `.venv/bin` o PATH) y lista lo que falta. Para instalar en el repo: `uv add --dev vulture deptry complexipy`. jscpd es de npm; úsalo solo si ya está en el sistema o en CI.

## 2. Priorizar

Ordena los hallazgos así y trabaja de arriba hacia abajo:

1. **Dependencias declaradas y no usadas** (deptry DEP002): borrarlas reduce superficie de ataque y tiempo de instalación. Riesgo casi nulo.
2. **Dependencias usadas y no declaradas** (DEP001/DEP003): son bugs latentes; decláralas.
3. **Código muerto** (vulture). Su confianza depende del tipo: 100 % argumentos sin usar y código inalcanzable,
   90 % imports, 60 % funciones, clases, métodos, variables y atributos. Lo de 90–100 % casi siempre se borra; lo de
   60 % pide revisar usos dinámicos (sección 3) antes de borrar.
4. **Funciones con complejidad > 15** que además cambian seguido (`git log --format= --name-only | sort | uniq -c | sort -rn | head`): ahí la deuda cuesta de verdad.
5. **Duplicados** de más de 8 líneas en código de producción.

Deja para después: complejidad en código que nadie toca y duplicados en pruebas.

## 3. Antes de borrar algo

- Busca usos dinámicos que vulture no ve: `getattr`, strings en configuración, entrypoints en `pyproject.toml`, rutas de FastAPI registradas por decorador, handlers de Lambda referenciados en IaC, fixtures de pytest, `__all__`.
- `git grep -n "<nombre>"` en todo el repo, incluidos YAML, Terraform/CDK y Dockerfiles.
- Si es API pública de una librería usada por otros repos, no lo borres: márcalo como deprecado.
- Falsos positivos confirmados van a `vulture_whitelist.py` con un comentario de por qué, y ese archivo se agrega a
  `paths` en `[tool.vulture]`; `deuda.py` corre vulture sin argumentos cuando esa sección existe, para respetarla.

## 4. Borrar en PRs pequeños

- Un tipo de cambio por PR: "quita dependencias sin uso", "borra código muerto de `app.adapters`", "simplifica `calcular_ruta`".
- Menos de ~300 líneas cambiadas por PR para que la revisión sea real.
- Refactor de complejidad: primero pruebas que fijen el comportamiento actual (ver `calidad-pruebas`), luego extraer funciones o aplanar condicionales; nada de cambios de comportamiento en el mismo PR.
- Mensaje del PR: qué se borró, cómo se comprobó que no se usaba, y la medición antes/después.

## 5. Verificar

1. La skill `verify` pasa.
2. Vuelve a correr `deuda.py`: el hallazgo atacado desapareció y no aparecieron nuevos.
3. Para dependencias: `uv sync` limpio y la app arranca.

## Prevención

- En revisiones de código pregunta "¿esto se puede borrar?" antes de "¿esto está bien?".
- ruff ya cubre parte en cada edición: `F401` (imports sin uso), `F841` (variables), `ERA` (código comentado), `ARG` (argumentos sin uso), `SIM`/`RET`/`PIE` (simplificaciones).
- Programa `deuda.py` en CI (semanal) como reporte, no como bloqueo: vulture y jscpd dan falsos positivos.
