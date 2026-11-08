# Estado

## Dónde quedamos (2026-11-07)
Kit completo y verificado en local: 7 plugins propios + 15 de terceros fijados por SHA + plantillas + `bin/adoptar.py`.

Verificación:
- `claude plugin validate .` pasa (22 plugins).
- 270 pruebas pasan (14 más se saltan sin OR-Tools; con él pasan las 19 de datos-optimizacion).
- Sesiones reales de Claude Code:
  - calidad-python: ruff quitó un import, Stop bloqueó por pytest y Claude corrigió el bug.
  - barreras: bloqueó `terraform apply` y la edición a mano de `uv.lock`; dejó pasar `terraform plan`.
- `adoptar.py` aplicado a un repo nuevo sin errores.
- Costo fijo en contexto (descripciones de skills): ~1.000 tokens perfil base, ~2.800 con todo.

## Pendiente
1. Subir el kit a un repo privado de GitHub y apuntar `plantillas/claude/settings.json` a él (`--marketplace-github OWNER/REPO`).
2. Limpieza de lo instalado en global (`~/.claude`), a decidir con Kevin:
   - quitar/reemplazar: software-architecture, write-concisely, code-simplifier, review-local-changes, commit, create-pr, playwright-skill, ui-ux-pro-max, antislop.
   - security-guidance: pasar de global a proyecto.
   - context7: modo CLI y versión parcheada (CVE-2026-75130).
3. Actualizar uv local (0.10.7 → ≥0.13) para `exclude-newer = "7 days"`.
4. Datos de la empresa: orquestador de datos, Terraform vs CDK, monitoreo, gestor de tareas → activar plugins condicionales.
5. Mejoras conocidas: pytest del hook Stop corre la suite completa; barreras no ve `echo >> uv.lock` por Bash ni `python -c` (CI es la red final); validar políticas IAM con Access Analyzer.
6. Skills no construidas aún: `geo-raster-agro`, CLAUDE.md del equipo de datos, `observabilidad` de ML (drift) más allá de la referencia.

## Decisiones
- Stack empresa: casi todo Python, GitHub, AWS. Sin política de IA.
- Alcance: marketplace propio, instalar por repo, nada global.
- Superpowers: opción B (5 skills copiadas, fijadas por SHA; executing-plans fuera porque depende de partes no copiadas).
- Excluido de terceros: web-design-guidelines de Vercel (descarga instrucciones sin fijar en cada uso).
- Sin atribución a Claude en commits/PR (plantilla settings.json).
