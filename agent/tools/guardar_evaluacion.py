"""
Tool: guarda una evaluación confirmada por el profesor.

Escribe en las dos memorias a la vez:
- SQLite (largo plazo): el registro completo, para el historial del cadete y la Etapa 3.
- Chroma (semántica): el resumen del caso y el texto, para encontrar casos parecidos.

Solo se ejecuta cuando el profesor presiona Confirmar.
"""

from datetime import date

from langchain_core.tools import tool

from agent.observability import registrar_tool
from agent.memory.long_term import guardar_evaluacion as guardar_en_sqlite
from agent.memory.semantic import agregar_caso

CRITERIOS = ["Content", "Organization", "Language"]


def validar(puntajes_propuestos, puntajes_finales, razones):
    """Revisa los puntajes finales y que cada ajuste tenga su razón. Devuelve una lista de problemas."""
    problemas = []
    for criterio in CRITERIOS:
        valor = puntajes_finales.get(criterio)
        if valor is None or not 0 <= valor <= 5 or (valor * 2) != int(valor * 2):
            problemas.append(f"{criterio}: el puntaje debe estar entre 0 y 5, en pasos de 0,5.")
        elif valor != puntajes_propuestos.get(criterio) and not (razones.get(criterio) or "").strip():
            problemas.append(f"{criterio}: el puntaje fue ajustado y falta la razón.")
    return problemas


def guardar(cadete_id, task_id, texto, corridas, puntajes_propuestos, puntajes_finales,
            razones, accion, debilidades, modelo, version_prompt):
    razones = {c: r for c, r in (razones or {}).items() if (r or "").strip()}
    problemas = validar(puntajes_propuestos, puntajes_finales, razones)
    if problemas:
        return {"error": "No se guardó la evaluación.", "problemas": problemas}

    evaluacion = {
        "fecha": date.today().isoformat(),
        "cadete_id": cadete_id,
        "task_id": task_id,
        "corridas": corridas,
        "propuesto": puntajes_propuestos,
        "final": puntajes_finales,
        "razones": razones,
        "debilidades": debilidades,
        "accion": accion,
        "modelo": modelo,
        "version_prompt": version_prompt,
    }
    evaluacion_id = guardar_en_sqlite(evaluacion)

    agregar_caso({"task_id": task_id, "texto": texto, "propuesto": puntajes_propuestos,
                  "final": puntajes_finales, "razones": razones, "debilidades": debilidades},
                 referencia=evaluacion_id)

    return {"ok": True, "evaluacion_id": evaluacion_id}


@tool
@registrar_tool
def guardar_evaluacion(cadete_id: str, task_id: str, texto: str, corridas: list,
                       puntajes_propuestos: dict, puntajes_finales: dict, razones: dict,
                       accion: str, debilidades: list, modelo: str, version_prompt: str) -> dict:
    """Save an assessment confirmed by the teacher in the cadet's history (SQLite)
    and in the semantic memory of cases (Chroma). Every score that differs from the
    proposed one must have a reason. Only to be used after the teacher confirms."""
    return guardar(cadete_id, task_id, texto, corridas, puntajes_propuestos, puntajes_finales,
                   razones, accion, debilidades, modelo, version_prompt)