"""Tool: consulta el historial de evaluaciones confirmadas de un cadete."""

from langchain_core.tools import tool

from agent.memory.long_term import obtener_historial


@tool
def consultar_historial(cadete_id: str, limite: int = 10) -> list:
    """Return a cadet's previous confirmed assessments, most recent first.
    Each item has the date, task, final scores, weaknesses detected, the
    planner's action and whether the teacher adjusted any score. Use it to
    answer questions about a cadet's progress or recurring weaknesses.
    cadete_id has the form 'CDT-004'. Returns an empty list if the cadet has
    no previous assessments."""
    return obtener_historial(cadete_id, limite)


# Prueba manual: python -m agent.tools.consultar_historial
if __name__ == "__main__":
    from pprint import pprint
    pprint(consultar_historial.invoke({"cadete_id": "CDT-004"}))

    