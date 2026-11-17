# Puerta, envío y lecciones

## Puerta (gate)
1. Junta las ramas con READY en un worktree de puerta creado desde la rama principal recién traída.
2. Antes de congelar una tanda, comprueba que ningún candidato contiene un head retenido:
   `git merge-base --is-ancestor <retenido> <candidato>`.
3. Corre las pruebas de lo que tocaron y de quien llama a lo compartido que cambiaron; las pesadas con `pesado.py`.
4. Anota el veredicto por carril en `gate/queue.md`: PASS o FAIL con el comando y su resultado, bajo `## Done`.
5. Un FAIL se clasifica antes de tocar nada: de la tanda (vuelve al carril con el error exacto), de la rama principal
   (anótalo y avisa) o de la máquina (repite con menos carga). Una prueba solo se edita si el comportamiento nuevo era
   el buscado.

## Envío
- Una tanda congelada de heads con PASS, un solo push, y lectura de vuelta del remoto (`git ls-remote`).
- Push a la rama principal: solo con un permiso de la persona que cubra esta tanda. Cuando reenvíes un sí, cita sus
  palabras con los heads exactos.
- Después del despliegue (si lo hay): revisa producción y el rastreador de errores de la versión nueva.
- Un cambio de alto riesgo (dinero, privacidad, borrados, migraciones) sigue su propio procedimiento revisado, con un
  paquete que muestre compatibilidad y hasta dónde se puede revertir.

## Lecciones (de la corrida de la que salió esta skill y de las pruebas en este Mac)
- Antes de juntar en tandas, una sola rama principal recibió 136 push en 32 horas, cada uno con su build pagado.
- Un PASS de la puerta casi terminó en un push de cambios de pagos sin permiso: la evidencia no es permiso.
- Tres carriles esperaron 3 minutos en un diálogo de hooks de Codex mientras `agent prompt --wait` decía `working`:
  lee el pane después del primer envío.
- Lanzar todos los carriles a la vez agota la máquina y la cuota semanal (compartida por todos los proyectos). Para
  corridas de noche, pide a la persona un umbral de cuota y detén el trabajo nuevo al llegar.
- Un worker que borra archivos con `rm` se detiene en preguntas de permisos aun en modo auto: salidas temporales fuera
  del worktree y nada de borrar.
