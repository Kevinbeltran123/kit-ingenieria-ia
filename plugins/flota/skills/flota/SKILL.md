---
name: flota
description: "Coordina una corrida de varios trabajadores (Claude y Codex) en carriles de herdr: reparte la meta en carriles con su brief, rama y worktree, vigila las entregas READY, prueba por tandas en la puerta y lleva la bitácora, con un tablero interactivo y avisos en cmux. Úsala cuando la persona te asigne el rol de coordinador, pida trabajadores en paralelo con herdr, o diga «coordina», «flota», «carriles», «lanes», «workers», «fleet», «coordinator». No la uses para una edición de una sola sesión, una pregunta, ni una segunda opinión rápida."
---

# Flota

Coordinas; los carriles construyen. Tu trabajo es partir la meta en carriles, elegir modelo y esfuerzo, escribir los
briefs, revisar lo que vuelve, probar por tandas, llevar la bitácora y traerle a la persona solo las decisiones que son
suyas. Lo pesado nunca va en tu propia sesión. Tus subagentes sirven para consultas rápidas dentro de tus propias
comprobaciones, nunca como carriles.

`S` = carpeta `scripts/` de esta skill (rutas absolutas en cada comando). Todos son de biblioteca estándar:
`python3 -I S/<script>.py`.

## Antes de empezar
1. Hay una sola sesión de herdr para todos los proyectos, `flota`: la abre la persona en cmux con el comando «Flota»,
   que deja el tablero a la vista; cada proyecto es un espacio en la barra de herdr y sus carriles van debajo. Tú eres
   `coord-<proyecto>` y solo tocas lo de tu proyecto. Si la sesión no existe, dile que abra «Flota».
2. Directorio de la corrida fuera del repo: `../<repo>-flota`. Si es nueva: `python3 -I S/carril.py preparar --repo
   <repo>`; crea `STATE.md`, `common.md`, `gate/queue.md`, `briefs/`, `wt/` y `carriles.json`, y registra el proyecto
   para el tablero. Los nombres de carril son únicos en toda la sesión: empiézalos con algo de tu proyecto.
3. Lee `STATE.md` y mira lo que ya corre antes de crear nada: `python3 -I S/carril.py lista --run <run> --sesion
   <sesión>`. Reúsa lo que sirva; nunca toques carriles, servidores ni paneles de otra corrida.
4. Escribe en `STATE.md` la meta (qué es terminar y la comprobación que lo demuestra) y los permisos que la persona
   dio, con sus palabras. Revisa `common.md` y ajústalo al proyecto (comandos de prueba, qué carril es dueño de qué).

## Modelos y esfuerzo
La elección explícita de la persona manda. Por defecto:

| Trabajo | Trabajador |
| --- | --- |
| Front end, diseño, refactor delicado | Claude `claude-opus-5-5`, high (xhigh para borradores de diseño) |
| Implementación acotada, pruebas, scripts | Claude `claude-sonnet-5-5`, medium |
| Back end, datos, revisión de riesgo | Codex con el modelo de la cuenta (`FLOTA_MODELO_CODEX`, p. ej. `gpt-6-luna`), high |
| Listas, extracción, formato | Claude `claude-haiku-5-5`, medium |
| Revisión antes de juntar cambios de riesgo | el otro proveedor del que escribió el carril, high |

Si un modelo falla (cuota, no disponible), dilo y usa el siguiente de la tabla; nunca lo cambies en silencio. Codex con
cuenta de ChatGPT solo acepta los modelos de `~/.codex/models_cache.json`; si el pane dice «model is not supported»,
cierra el carril y vuelve a iniciarlo con `--modelo`. `max` solo si la persona lo pide.

## Permisos de los carriles (`--permisos`)
- `auto` (por defecto): Claude en modo auto; Codex con sandbox `workspace-write` y sin preguntas. Codex no puede hacer
  commit (su sandbox deja `.git` en solo lectura): tú lo haces con `carril.py commit` después de revisar el diff.
- `preguntar`: cada acción sensible se detiene; lees el pane y respondes dentro del alcance del brief.
- `abierto`: sin sandbox ni preguntas. Solo si la persona lo pidió para esta corrida: ella exporta
  `FLOTA_PERMITIR_ABIERTO=1` y confirma en herdr el diálogo de Claude para ese modo (el script nunca lo acepta). Nunca
  lo exportes tú. Anótalo en `STATE.md`.
Los hooks del repo siguen corriendo en todos los niveles. Si tu propio clasificador de permisos rechaza lanzar un
carril, díselo a la persona en lugar de buscar otro camino.

## Un carril
1. **Brief** en `<run>/briefs/<nombre>.md` (plantilla en `references/plantillas.md`): meta, referencias que dio la
   persona, límites (qué archivos sí y no), base, comprobaciones que lo demuestran y la última línea esperada
   `<NOMBRE>-READY <rama> <head>`.
2. **Iniciar**:
   ```
   python3 -I S/carril.py iniciar --run <run> --sesion <sesión> --repo <repo> --nombre <nombre> \
     --tipo claude|codex [--modelo M] [--esfuerzo E] [--permisos auto] --brief <run>/briefs/<nombre>.md
   ```
   Crea el worktree desde `origin/HEAD` recién traído (o `--base`), arranca el agente en su espacio de herdr, responde
   los diálogos de confianza de la carpeta y le manda el brief. Sale con 3 si el agente quedó en un diálogo que no
   conoce (por ejemplo, hooks de Codex por revisar): eso lo decide la persona.
   Empieza con uno o dos carriles; lanzar todos a la vez agota la máquina y la cuota.
3. **Vigilar**: una instancia por corrida, en segundo plano, y vuelve a armarla cada vez que sale:
   `python3 -I S/vigilar.py --run <run> --sesion <sesión> --timeout 3600`. La primera vez solo imprime BASELINE.
   `CHANGED` trae las entregas nuevas; `STOPPED` es un carril que paró sin entregar: lee su pantalla
   (`herdr --session <sesión> agent read <nombre> --source recent-unwrapped --lines 80`).
4. **Hablarle**: `carril.py enviar --run <run> --sesion <sesión> --nombre <n> --texto "..."` (antepone «Coordinador:»).
   Para un diálogo: `carril.py teclas --sesion <sesión> --nombre <n> down enter`. Mensajes autocontenidos: archivo,
   rama, head y el cambio exacto; los carriles largos compactan su contexto.
5. **Recoger**: una entrega es una afirmación. Revisa el head, el diff contra los límites del brief y la evidencia
   antes de pasarla a la puerta. Codex en `auto`: revisa el diff y haz `carril.py commit --run <run> --nombre <n> -m
   "..."`.
6. **Cerrar** el espacio cuando su cambio ya se envió: `carril.py cerrar ...` (el worktree queda en disco).
   `carril.py marcar --estado gate|enviado` mueve la tarjeta en el tablero.

## Puerta y envío
Prueba la tanda, no cada carril: junta las ramas listas sobre la rama principal actual en un worktree de puerta, corre
lo que tocaron (y a quien llama cualquier función compartida que cambiaron) y da un veredicto por carril en
`gate/queue.md` (secciones `## En cola`, `## Probando`, `## Done`). Asegúrate de que las pruebas que nombras corrieron
de verdad. Un fallo es de la tanda, de la rama principal o de la máquina: averigua cuál antes de que alguien toque una
prueba. Detalle, envío y lecciones: `references/puerta.md`.

## Lo que se le pregunta a la persona
Siempre: push a la rama principal o de producción sin un permiso que lo cubra, cambios en la base de datos de
producción, borrar datos remotos, cualquier cosa con dinero, privacidad o credenciales, gasto por encima de lo
autorizado y todo lo que se publique a otras personas. Un PASS de la puerta es evidencia, no permiso. Un permiso vale
solo para lo que cubrió (misma meta, destino y efectos); el silencio no es un sí. Mientras una acción espera, sigue con
el resto. Nunca imprimas ni pidas un secreto en el chat.

## La interfaz
- **Tablero web**: ya está abierto en el espacio «Flota» de cmux (`python3 -I S/tablero.py --sesion flota --abrir`;
  la URL queda en `~/.local/state/flota/tablero-url`). Junta todos los proyectos registrados: columnas de flujo, línea
  de tiempo de estados, entregas, puerta, bitácora y un panel por carril con su pantalla en vivo, brief y entrega;
  desde ahí se le escribe, se responden diálogos, se enfoca en herdr y se arranca el coordinador de un proyecto.
  Atajos: Alt+F o Cmd+K busca, J/K cambia de carril, F enfoca, Esc cierra.
- **Vista de terminal**: el mismo script con `--terminal`.
- **cmux**: el plugin de herdr `kit.flota.puente` (carpeta `herdr/` del plugin) pone el estado de cada agente en la
  barra del espacio, una línea en su log y un aviso cuando alguien te espera o termina. Instálalo una vez con
  `herdr plugin link <plugin>/herdr`.
Dile a la persona dónde mirar cuando arranque el primer carril, y cuánto tardará cada espera larga.

## Informe
Una decisión por pregunta, con tu recomendación. Al volver la persona, primero lo que espera su sí. Termina bajo tres
títulos, sin los vacíos: Te espera, Qué cambió (resultado y verificación), Qué encontré. «Enviado» solo después de leer
de vuelta el remoto.

## Cómo verificar que se cumplió
- `carril.py lista` muestra cada carril con su estado y su línea READY.
- Cada entrega tiene su handover con los comandos de verificación y su salida; la puerta tiene su veredicto en `## Done`.
- `STATE.md` tiene la meta, los permisos con su origen y una bitácora que explica cada decisión.
- Comandos de herdr, diálogos y trampas conocidas: `references/herdr.md`.
