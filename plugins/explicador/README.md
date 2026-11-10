# explicador

Instalar en un repo: `/plugin install explicador --marketplace Kevinbeltran123/kit-ingenieria-ia` (registra el marketplace si hace falta; con `bin/adoptar.py` ya queda en `.claude/settings.json`).

Cada cambio queda explicado línea por línea en una página local: el código a la izquierda y una
terminal que lo explica a la derecha. Sirve para entender lo que escribió la IA y para encontrar
errores antes del PR.

| Pieza | Qué hace |
|---|---|
| Skill `explicar-cambios` | `recolectar.py` saca de git las líneas reales y las agrupa en pasos (uno por bloque o método). Claude escribe la explicación de cada paso y una nota por cada línea cambiada. `construir.py` valida que no falte ninguna y arma el HTML. |
| Hook `PreToolUse` | Antes de `gh pr create`, exige una explicación del commit actual y sin errores abiertos. |

Los números de línea y el código salen de git, nunca de lo que escribe Claude: así la página no puede
mostrar código inventado.

## Dónde quedan
`.explicaciones/<rama>/<fecha>-<commit>.html` y un índice en `.explicaciones/index.html`. La carpeta
queda fuera de git con `.git/info/exclude`, sin tocar el `.gitignore` del equipo. El HTML no carga
nada de internet: la fuente IBM Plex Mono va incrustada (licencia OFL en `skills/explicar-cambios/scripts/fuentes/OFL.txt`).

## Recorrer una explicación
`↑` `↓` línea por línea · `←` `→` paso por paso · `r` resumen · clic en una línea o en una nota para
ir a ella. Al abrir se ve el resumen: problema, solución, cómo se probó, decisiones y alertas.

## Desactivar
Solo la persona: `EXPLICADOR_DESACTIVAR=1` al lanzar Claude Code, o `{"desactivar": true}` en
`.claude/explicador.json`.

## Límites
- El hook ve `gh pr create` lanzado por Claude. Un PR abierto desde la web de GitHub no pasa por él;
  para esos casos se pide la skill a mano.
- Explicar cada línea cuesta tokens: un cambio de 300 líneas puede llevar varios miles. Es el precio
  de entender el código en detalle.
- Si construyes imágenes de Docker en local, agrega `.explicaciones/` al `.dockerignore` (la
  plantilla del kit ya lo trae).

## Probar
    python3 -m pytest tests -q
