# Origen

- Repo: https://github.com/obra/superpowers (licencia MIT, ver `LICENSE`, autor Jesse Vincent)
- Tag: v7.0.2 (objeto de tag `c62ffea8267a70de07583e153544d355b6748a56`)
- Commit: `22f0b463e7a5e579904dd6211a520321035526f7`
- Copiado: 2026-11-07

## Copiado
| Skill | Archivos |
|---|---|
| test-driven-development | SKILL.md, writing-good-tests.md |
| systematic-debugging | SKILL.md, root-cause-tracing.md, defense-in-depth.md, condition-based-waiting.md, condition-based-waiting-example.ts, find-polluter.sh |
| writing-plans | SKILL.md |
| verification-before-completion | SKILL.md |
| brainstorming | SKILL.md, builder-check-prompt.md |

## No copiado
- **executing-plans**: depende de los scripts de `subagent-driven-development` (sdd-workspace, task-brief, review-package) y de las skills using-git-worktrees, requesting-code-review y finishing-a-development-branch. Su lugar lo cubre la sección "Execution Handoff" reescrita en writing-plans.
- brainstorming/visual-companion.md y brainstorming/scripts/ (servidor Node local para mockups).
- Hooks, comandos, `using-superpowers` (inyección de contexto en SessionStart) y el resto de skills.

## Modificado (marcado con `<!-- kit: ... -->` donde es un bloque)
- systematic-debugging/SKILL.md: `superpowers:` → `flujo:` en 2 referencias.
- test-driven-development/writing-good-tests.md: la referencia a writing-skills apunta a skill-creator / `claude plugin eval`.
- writing-plans/SKILL.md: sin la línea de worktrees; planes en `docs/planes/`; cabecera del plan y "Execution Handoff" reescritos para ejecutar en la misma sesión con TDD + verificación.
- brainstorming/SKILL.md: `description` sin "You MUST… any creative work" (se activaba en casi cualquier pedido); `superpowers:writing-plans` → `flujo:writing-plans`; specs en `docs/specs/`; quitado el companion visual (se dibuja en texto o Mermaid).

## Segunda fuente: pstack
- Repo: https://github.com/cursor/plugins, carpeta `harness/pstack/claude-code` (licencia MIT, ver `LICENSE-pstack`,
  autora Lauren Tan)
- Commit: `6b0300214a09fd6029cfb7077043125758cd1fd2` (pstack 0.15.36)
- Copiado: 2026-11-08
- Copiado: `correct/SKILL.md`, sin cambios salvo una nota `<!-- kit: -->` (la excepción la escribe la persona).
- Tomado: en systematic-debugging/SKILL.md, el punto del estado legítimo de `principle-fix-root-causes`, marcado
  con `<!-- kit: -->`.
- No copiado, con el motivo:
  - `create-verification-skill` y `maintain-verification-skill`: Claude Code ya trae `/run-skill-generator`, que
    escribe la skill del proyecto para levantar y manejar la app, y `/run`, que la usa (comprobado en 2.1.319).
  - `blast-radius`: `differential-review` (Trail of Bits, ya en el marketplace) cubre el mismo pedido ("qué más
    rompe este cambio"), y la de pstack depende de 4 skills suyas no copiadas (`how`, `why`, `arena`, `unslop`).
  - `benchmark-checklist`: sus 7 preguntas están adaptadas en `python-ingenieria/rendimiento-python`.
  - `poteto-mode` y el resto: otro flujo de trabajo, con acciones externas sin preguntar.

## Revisión de seguridad
Solo Markdown, un `.ts` de ejemplo (no se ejecuta) y `find-polluter.sh` (bisección local que corre `npm test` por archivo; sin red ni lecturas fuera del repo). Sin hooks, MCP ni binarios.

## Actualizar
Ver `terceros/README.md`: comparar `git diff <SHA viejo> <SHA nuevo> -- skills/<skill>` de las 5 skills, reaplicar los cambios de arriba.
Para pstack, lo mismo con `harness/pstack/claude-code/skills/correct` y `principle-fix-root-causes` en cursor/plugins. El plugin no lleva `version`: el commit nuevo ya es la versión nueva.
