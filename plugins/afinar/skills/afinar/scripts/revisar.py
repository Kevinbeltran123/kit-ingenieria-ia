"""Revisa un pedido para un agente y dice qué le falta: comprobación, límites, referencias, vaguedad y riesgos.

Uso: revisar.py [ARCHIVO]   (sin archivo lee stdin)   → JSON {"tarea", "palabras", "hallazgos", "completo"}
Reglas simples, sin llamar a ningún modelo: sirve para la skill afinar (antes y después de reescribir) y para el aviso
del hook. Un hallazgo es una pista, no un veredicto.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

VERBOS_TAREA = re.compile(
    r"\b(agrega|añade|crea|arregla|corrige|implementa|refactoriza|cambia|mueve|migra|construye|haz|hazme|escribe|"
    r"elimina|borra|quita|actualiza|reemplaza|configura|instala|integra|optimiza|mejora|limpia|genera|prueba|"
    r"despliega|sube|arma|monta|añadir|agregar|crear|arreglar|implementar|"
    r"add|fix|implement|create|refactor|build|update|remove|delete|migrate|write|make|deploy|optimize|improve)\b",
    re.IGNORECASE,
)
COMPROBACION = re.compile(
    r"(comprobaci[oó]n|comprueba|verifica|verificaci[oó]n|criterio|listo cuando|terminado cuando|debe (pasar|dar|"
    r"devolver|mostrar|quedar)|que pase|pasa[n]? (las )?pruebas|pytest|\btests?\b|\bjust \w|npm (run )?test|"
    r"vitest|assert|→|done when|acceptance|should (pass|return)|exit code)",
    re.IGNORECASE,
)
LIMITES = re.compile(
    r"(l[ií]mites?|no toques|no toque|no cambies|no modifiques|sin tocar|sin push|sin merge|solo (en|el|la|los|las)|"
    r"únicamente|fuera de alcance|no hagas|don't|do not|only)",
    re.IGNORECASE,
)
REFERENCIA = re.compile(r"(`[^`]+`|\b[\w./-]+\.(py|ts|tsx|js|md|json|toml|sql|ya?ml|css|html|sh)\b|\w+/\w+|#\d+)")
VAGAS = re.compile(
    r"\b(mejora|mejorar|optimiza|optimizar|limpia|limpiar|bonito|mejor|algo|cosas|etc|todo lo necesario|"
    r"lo que haga falta|como sea|r[aá]pido)\b",
    re.IGNORECASE,
)
RIESGOS = {
    "push o merge": re.compile(r"\b(push|merge|force)\b", re.IGNORECASE),
    "producción": re.compile(r"\b(producci[oó]n|prod|deploy|despliega|desplegar)\b", re.IGNORECASE),
    "borrado": re.compile(r"\b(borra|borrar|elimina|eliminar|delete|drop|truncate|rm -rf)\b", re.IGNORECASE),
    "migración o base de datos": re.compile(
        r"\b(migraci[oó]n|migra|base de datos|database|schema|esquema)\b", re.IGNORECASE
    ),
    "credenciales o dinero": re.compile(
        r"\b(credencial|token|secreto|password|contraseña|pago|cobro|factura)\w*", re.IGNORECASE
    ),
}


def es_tarea(texto: str) -> bool:
    """Un pedido de trabajo (no una pregunta ni una charla): tiene un verbo de tarea entre sus primeras palabras."""
    limpio = texto.strip()
    if not limpio or limpio.startswith("/"):
        return False
    if re.search(r"^\s*(meta|goal)\s*:", limpio, re.IGNORECASE | re.MULTILINE):
        return True
    primeras = " ".join(limpio.split()[:14])
    return bool(VERBOS_TAREA.search(primeras)) and not (limpio.endswith("?") and len(limpio.split()) < 25)


def revisar(texto: str) -> dict:
    palabras = len(texto.split())
    tarea = es_tarea(texto)
    hallazgos = []
    if tarea and not COMPROBACION.search(texto):
        hallazgos.append(
            {
                "clave": "comprobacion",
                "mensaje": "no dice cómo se comprueba que quedó bien (comando y resultado esperado)",
            }
        )
    if tarea and palabras >= 12 and not LIMITES.search(texto):
        hallazgos.append({"clave": "limites", "mensaje": "no dice qué no se toca ni hasta dónde llega"})
    if tarea and not REFERENCIA.search(texto):
        hallazgos.append(
            {
                "clave": "referencias",
                "mensaje": "no nombra archivos, módulos, comandos ni issues: el agente tendrá que adivinarlos",
            }
        )
    vagas = sorted({m.group(0).lower() for m in VAGAS.finditer(texto)})
    if tarea and vagas:
        hallazgos.append({"clave": "vago", "mensaje": f"palabras vagas sin criterio medible: {', '.join(vagas)}"})
    riesgos = [nombre for nombre, patron in RIESGOS.items() if patron.search(texto)]
    if riesgos:
        hallazgos.append(
            {"clave": "riesgo", "mensaje": f"toca algo delicado ({', '.join(riesgos)}): pedir confirmación antes"}
        )
    faltan = {h["clave"] for h in hallazgos} & {"comprobacion", "limites", "referencias"}
    return {"tarea": tarea, "palabras": palabras, "hallazgos": hallazgos, "completo": tarea and not faltan}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    texto = Path(args[0]).read_text(encoding="utf-8") if args else sys.stdin.read()
    print(json.dumps(revisar(texto), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
