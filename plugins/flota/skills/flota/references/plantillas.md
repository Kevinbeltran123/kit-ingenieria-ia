# Plantillas

## Brief de un carril (`<run>/briefs/<nombre>.md`)
```markdown
# <nombre>: <meta en una línea>

## Meta
<qué debe quedar hecho, visto por quien lo usa>

## Referencias
<lo que dio la persona para esta parte: capturas, issues, archivos, decisiones>

## Límites
- Sí: <rutas o módulos de este carril>
- No: <lo que es de otro carril o no se toca>

## Base
<rama y SHA de la base; carril.py lo deja en carriles.json>

## Cómo se comprueba
- <comando> → <resultado esperado>

## Entrega
Escribe <run>/handover-<nombre>.md con qué hiciste, cómo lo verificaste (comando y salida) y lo pendiente.
Última línea, sola: <NOMBRE>-READY <rama> <head>
```

## Revisión (`<run>/review-<carril>.md`)
Hallazgos que cambian el resultado, lo que debe quedarse y el arreglo más pequeño útil. Última línea:
`REVIEW-READY <carril> <PASS|CAMBIOS>`.

## Entrega de una pregunta
Si el carril necesita una decisión: la pregunta en su handover y la línea `<NOMBRE>-PREGUNTA`. El coordinador la
responde o se la trae a la persona.
