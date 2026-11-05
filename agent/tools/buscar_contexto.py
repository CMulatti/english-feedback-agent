"""Tool: busca por significado en los criterios y en los casos previos (memoria semántica)."""

from langchain_core.tools import tool

from agent.observability import registrar_tool
from agent.memory.semantic import buscar_criterios, buscar_casos


@tool
@registrar_tool
def buscar_contexto(consulta: str, task_id: str = None) -> list:
    """Search by meaning in the assessment criteria (Cambridge rubric and the
    academy's institutional criteria) and in previous confirmed cases, including
    teacher corrections. Use it to explain a rule or to find how teachers resolved
    similar situations. If task_id is given, cases are limited to that task.
    Each result has its content, its source and a reference to cite."""
    return buscar_criterios(consulta) + buscar_casos(consulta, task_id=task_id)


# Prueba manual: python -m agent.tools.buscar_contexto
if __name__ == "__main__":
    for pregunta in ["Why is half a band deducted when there is no greeting?",
                     "Has a teacher corrected a text with repetitive structures?"]:
        print(f"\n=== {pregunta}")
        for resultado in buscar_contexto.invoke({"consulta": pregunta}):
            print(f"- [{resultado['fuente']} · {resultado['referencia']}] {resultado['contenido'][:120]}")