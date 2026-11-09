---
name: calidad-pruebas
description: Pruebas Python que de verdad prueban algo - evita los anti-patrones de pruebas generadas por IA (mocks excesivos, asserts triviales, pruebas que replican la implementación), usa Hypothesis, moto, testcontainers y schemathesis, y cierra con un gate de mutación con mutmut sobre el código cambiado. Úsala al escribir o revisar pruebas, cuando la cobertura sea alta pero haya bugs, o pidan "tests", "pytest", "mutation testing", "property-based", "mocks".
---

# Calidad de pruebas

Una prueba vale si **falla cuando el código está mal**. La evidencia de 2026 muestra que los agentes abusan de los mocks y que se puede llegar a 100 % de cobertura con solo 4 % de mutantes detectados. Cobertura no es calidad.

## Reglas para cada prueba nueva

1. **Verla fallar primero.** Escribe la prueba, córrela contra el código sin el cambio (o rompe el código a propósito) y confirma que falla por la razón correcta. Si no puedes hacerla fallar, no prueba nada.
2. **Asserts sobre comportamiento observable**: el valor devuelto, el estado guardado, el error lanzado, la respuesta HTTP. No sobre detalles internos ni sobre "se llamó a tal método".
3. **No mockees lo que estás probando** ni sus colaboradores de dominio. Mockea solo límites externos que no controlas, y prefiere fakes en memoria que cumplan el puerto (`Protocol`).
4. **Un comportamiento por prueba**, con nombre que lo describa: `test_cosecha_negativa_lanza_error`.
5. **Datos que importan**: casos borde (vacío, cero, negativo, máximo, unicode, zona horaria), no solo el caso feliz.

## Anti-patrones que debes rechazar (también en revisiones)

| Anti-patrón | Ejemplo | Corrección |
|---|---|---|
| Assert trivial | `assert resultado is not None`, `assert True` | comparar con el valor esperado exacto |
| Replicar la implementación | la prueba recalcula con la misma fórmula del código | valores esperados calculados a mano o propiedades |
| Mock del sistema bajo prueba | `patch("app.application.registrar.RegistrarCosecha.__call__")` | probar la clase real con fakes de sus puertos |
| Solo verificar llamadas | `mock.assert_called_once()` como único assert | verificar el efecto (estado, valor) |
| `boto3` mockeado a mano | `MagicMock()` para S3 | `moto` (`@mock_aws`): S3, SQS y DynamoDB en memoria, sin Docker ni cuenta |
| Capturar todo | `with pytest.raises(Exception)` | el error de dominio específico + `match=` |
| Borrar o saltar una prueba que falla | `@pytest.mark.skip` sin issue | arreglar el código; si de verdad hay que saltarla, explicar, enlazar el issue y que la persona agregue el `skip` (con `calidad-python`, un hook bloquea que Claude lo agregue) |
| Fijar una constante | `assert TARIFA == 0.02`: no falla aunque cambie el código que la usa | probar lo que hace el código con ella (`assert cobro(100) == 2`); fijar el valor solo vale si es un contrato público (una variable de entorno, la versión de un protocolo) |
| Snapshot de todo | comparar JSON gigante generado | asserts sobre los campos que importan |

## Herramientas según el tipo de prueba

- **Unitarias de dominio y casos de uso**: pytest + fakes en memoria. Sin red, sin Docker, rápidas.
- **Propiedades (Hypothesis)**: para funciones con muchas entradas posibles (parsers, cálculos, transformaciones de datos, optimización). Propiedades típicas: ida y vuelta (`decode(encode(x)) == x`), invariantes (el total no cambia al reordenar), comparación con una implementación simple de referencia, nunca lanza para entradas válidas. Fija la reproducibilidad en CI con `@settings(derandomize=True)` o un perfil de settings, y guarda los ejemplos que fallaron con `@example(...)`.
- **Integración de adaptadores**: `testcontainers` con Postgres real; para AWS, `moto` (`@mock_aws` en memoria, o `ThreadedMotoServer` si hace falta un endpoint HTTP). LocalStack exige cuenta y token desde marzo de 2026 y su plan gratis prohíbe el uso comercial: úsalo solo si la empresa paga la licencia. Marca las lentas con `@pytest.mark.integration` y córrelas aparte (`-m integration`); el marcador ya está registrado en el fragmento de `pyproject.toml`, porque con `--strict-markers` uno sin registrar rompe la colección.
- **API**: `TestClient` de FastAPI para flujos concretos; `schemathesis` contra el OpenAPI para encontrar entradas que rompen el servicio (`schemathesis run http://localhost:8000/openapi.json`, o su integración con pytest).

## Gate de mutación (mutmut 3) sobre lo que cambiaste

Mutmut cambia el código (un `+` por `-`, un `<` por `<=`...) y mira si alguna prueba falla. Un mutante que sobrevive es un comportamiento sin probar.

Configuración mínima en `pyproject.toml`:

```toml
[tool.mutmut]
source_paths = ["src/"]
pytest_add_cli_args_test_selection = ["tests/unit/"]   # solo pruebas rápidas
use_setproctitle = false                                # evita segfaults en macOS
```

Correrlo solo sobre los módulos cambiados:

```bash
uv add --dev mutmut
pats=$(python3 "${CLAUDE_PLUGIN_ROOT}/skills/calidad-pruebas/scripts/mutantes_del_diff.py" --base origin/main) || exit 1
uv run mutmut run $pats
uv run mutmut results          # lista sobrevivientes
uv run mutmut show <mutante>   # muestra el cambio
```

Por cada sobreviviente: escribe una prueba que lo mate, o justifica por escrito que es **equivalente** (el cambio no altera el comportamiento observable) y pide a la persona que marque esa línea con `# pragma: no mutate`. La excepción la pone ella: con `calidad-python`, un hook bloquea que Claude la agregue.

Umbral recomendado en código nuevo de `domain`/`application`: **≥ 80 % de mutantes muertos y cero sobrevivientes sin justificar**. En adaptadores y entrypoints, informativo. En CI completo, nocturno o semanal; en el PR, solo el diff.

Si el repo usa mypy o pyrefly, `type_check_command` en `[tool.mutmut]` descarta mutantes que el verificador de tipos ya atraparía.

## Verificación

1. Cada prueba nueva se vio fallar (dilo en el resumen: "falla sin el cambio: sí").
2. Ninguna fila de la tabla de anti-patrones aparece en el diff.
3. Gate de mutación sobre el diff con el umbral de arriba.
4. La skill `verify` pasa.
