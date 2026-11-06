"""
Tool: genera la retroalimentación para el cadete, en español.

Se ejecuta después de que el profesor confirma, a partir de los puntajes finales.
Antes de devolverla, el código revisa que tenga 200 palabras o menos, que esté en
español y que no mencione puntajes. Si falla, se genera una vez más.
"""

import re

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool

from agent.rag.retrieval import load_task
from agent.rag.checks import count_words
from agent.llm import crear_llm, invocar_llm, nombre_modelo
from agent.observability import registrar_tool, registrar_evento
from agent.prompts import STUDENT_SYSTEM_PROMPT, build_student_prompt
from agent.tools.revisar_texto import buscar_palabras_espanol

MAX_PALABRAS = 200
MIN_PROPORCION_ESPANOL = 0.15   # baja, porque la retroalimentación incluye ejemplos en inglés

PATRONES_PUNTAJE = [
    r"\bbandas?\b", r"\bbands?\b", r"\bpuntajes?\b", r"\brúbrica\b",
    r"\b(content|organization|language)\s*:?\s*\d",
]


def calcular_progreso(historial_previo, debilidades_actuales):
    """
    Compara las debilidades actuales con las de la evaluación anterior más reciente.
    Se calcula con código, para que la retroalimentación solo afirme progreso real.
    """
    if not historial_previo:
        return {"tiene_historial": False, "debilidades_superadas": [], "debilidades_persistentes": []}
    anteriores = historial_previo[0]["debilidades"]
    return {
        "tiene_historial": True,
        "debilidades_superadas": [d for d in anteriores if d not in debilidades_actuales],
        "debilidades_persistentes": [d for d in anteriores if d in debilidades_actuales],
    }


def revisar_retroalimentacion(texto):
    """Devuelve la lista de problemas encontrados (vacía si está bien)."""
    problemas = []
    palabras = count_words(texto)
    if palabras > MAX_PALABRAS:
        problemas.append(f"too_long ({palabras} palabras)")
    if palabras and len(buscar_palabras_espanol(texto)) / palabras < MIN_PROPORCION_ESPANOL:
        problemas.append("not_spanish")
    if any(re.search(patron, texto.lower()) for patron in PATRONES_PUNTAJE):
        problemas.append("mentions_scores")
    return problemas


def generar(texto, task_id, puntajes_finales, justificacion, razones, progreso):
    llm = crear_llm(temperature=0.5)
    mensajes = [
        SystemMessage(content=STUDENT_SYSTEM_PROMPT),
        HumanMessage(content=build_student_prompt(texto, load_task(task_id), puntajes_finales,
                                                  justificacion, razones, progreso)),
    ]

    for intento in range(2):
        retroalimentacion = invocar_llm(llm, mensajes, nombre="generar_retroalimentacion")
        problemas = revisar_retroalimentacion(retroalimentacion)
        if not problemas:
            break
        registrar_evento("llm", "generar_retroalimentacion", "error", modelo=nombre_modelo(llm),
                         tipo_error="feedback_check_failed", detalle=", ".join(problemas))

    return {"retroalimentacion": retroalimentacion, "advertencias": problemas}


@tool
@registrar_tool
def generar_retroalimentacion(texto: str, task_id: str, puntajes_finales: dict,
                              justificacion: str, razones: dict, progreso: dict) -> dict:
    """Write feedback in Spanish for the cadet, based on the teacher's final scores,
    the assessment justification and the teacher's reasons for any adjustment. Mentions
    progress only if 'progreso' shows a previous assessment. Never mentions scores.
    Returns the feedback and a list of warnings if the automatic checks failed."""
    return generar(texto, task_id, puntajes_finales, justificacion, razones, progreso)