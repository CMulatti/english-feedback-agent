"""
Tool: evalúa un texto con el LLM, varias veces, y compara los resultados.

1. Recupera el contexto de la tarea (RAG por tarea, Etapa 1).
2. Ejecuta N_EVALUACIONES corridas con el mismo prompt.
3. Calcula la mediana de cada criterio (puntaje propuesto) y detecta los criterios
   en que las corridas difieren más de UMBRAL_DESACUERDO (regla 3: caso dudoso).

Si una corrida falla (por ejemplo, el modelo está saturado), se continúa con las demás.
Se usa median_low: con un número par de corridas, elige el menor de los dos valores
centrales en vez de promediarlos, así el puntaje propuesto siempre es uno que alguna
corrida realmente asignó.
"""

import re
import statistics

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool

from config import settings
from agent.rag.retrieval import retrieve_context
from agent.llm import crear_llm, invocar_llm, nombre_modelo
from agent.observability import registrar_tool, registrar_evento
from agent.prompts import TEACHER_SYSTEM_PROMPT, build_teacher_prompt

CRITERIOS = ["Content", "Organization", "Language"]


# ---------- Funciones auxiliares ----------

def leer_puntajes(respuesta):
    """
    Busca 'Scores: Content 3 | Organization 2.5 | Language 3' y devuelve
    {'Content': 3.0, 'Organization': 2.5, 'Language': 3.0}.
    Devuelve None si falta la línea o algún puntaje no es válido (0 a 5, en pasos de 0,5).
    """
    for linea in respuesta.splitlines():
        limpia = linea.replace("*", "").strip()
        if not limpia.startswith("Scores:"):
            continue
        puntajes = {}
        for criterio in CRITERIOS:
            encontrado = re.search(rf"{criterio}\s*:?\s*(\d+(?:[.,]\d+)?)", limpia)
            if not encontrado:
                return None
            valor = float(encontrado.group(1).replace(",", "."))
            if not 0 <= valor <= 5 or (valor * 2) != int(valor * 2):
                return None
            puntajes[criterio] = valor
        return puntajes
    return None


def resumir_corridas(corridas):
    """Calcula la mediana, el rango y los criterios en desacuerdo."""
    mediana, rango, desacuerdo = {}, {}, []
    for criterio in CRITERIOS:
        valores = [corrida[criterio] for corrida in corridas]
        mediana[criterio] = statistics.median_low(valores)
        rango[criterio] = max(valores) - min(valores)
        if rango[criterio] > settings.UMBRAL_DESACUERDO:
            desacuerdo.append(criterio)
    return mediana, rango, desacuerdo


def indice_mas_cercano(corridas, mediana):
    """Devuelve el índice de la corrida más cercana a la mediana (su justificación es la que se muestra)."""
    distancias = [sum(abs(c[k] - mediana[k]) for k in CRITERIOS) for c in corridas]
    return distancias.index(min(distancias))


# ---------- Evaluación ----------

def evaluar(texto, task_id, revision, casos_similares=None):
    contexto = retrieve_context(task_id)
    mensajes = [
        SystemMessage(content=TEACHER_SYSTEM_PROMPT),
        HumanMessage(content=build_teacher_prompt(texto, contexto, revision, casos_similares or [])),
    ]
    llm = crear_llm()

    corridas, respuestas, errores = [], [], []
    for numero in range(1, settings.N_EVALUACIONES + 1):
        # Cada corrida tiene 2 oportunidades: si falta la línea Scores, se pide de nuevo
        for _ in range(2):
            try:
                respuesta = invocar_llm(llm, mensajes, nombre="evaluar_texto")
            except Exception as error:
                errores.append("llm_failed")
                print(f"   Corrida {numero}: el modelo no respondió ({error})")
                break
            puntajes = leer_puntajes(respuesta)
            if puntajes:
                corridas.append(puntajes)
                respuestas.append(respuesta)
                break
            errores.append("missing_scores")
            registrar_evento("llm", "evaluar_texto", "error", modelo=nombre_modelo(llm),
                             tipo_error="missing_scores", detalle=respuesta[-200:])

    if not corridas:
        return {"error": "No se obtuvo ninguna evaluación válida.", "errores": errores}

    mediana, rango, desacuerdo = resumir_corridas(corridas)
    elegida = indice_mas_cercano(corridas, mediana)

    return {
        "corridas": corridas,
        "mediana": mediana,
        "rango": rango,
        "criterios_en_desacuerdo": desacuerdo,
        "corridas_validas": len(corridas),
        "justificacion": respuestas[elegida],
        "modelo": nombre_modelo(llm),
        "version_prompt": settings.VERSION_PROMPT,
        "errores": errores,
    }


# ---------- La tool ----------

@tool
@registrar_tool
def evaluar_texto(texto: str, task_id: str, revision: dict, casos_similares: list = None) -> dict:
    """Assess a student's text against the Cambridge A2 rubric and the academy's
    criteria, using the task's knowledge base. Runs the assessment several times
    and returns the scores of each run, the median score per criterion (the
    proposed score), the criteria where runs disagree, and the justification.
    Requires the output of revisar_texto as 'revision'."""
    return evaluar(texto, task_id, revision, casos_similares)


# Prueba manual con Gemini: python -m agent.tools.evaluar_texto
if __name__ == "__main__":
    from pprint import pprint
    from agent.tools.revisar_texto import revisar

    muestra = (
        "Hi Jim,\nI wake up at 6.00 am, I take a shower and dress up for line up in the "
        "Alpatacal Courtyard and take breakfast in the mess hall. After that, I have classes "
        "from 8.00 to 1300. Then, I line up in the Alpatacal Courtyard and have lunch in the "
        "Mess Hall. Then, I go to the classroom and have lessons. After that, I go to the "
        "Alpatacal Courtyard and have dinner. Next, I study in the library and go to bed in "
        "the barracks at 10.00 pm."
    )
    revision = revisar(muestra, "cadet_routine")
    resultado = evaluar_texto.invoke({"texto": muestra, "task_id": "cadet_routine",
                                      "revision": revision})
    print(resultado.pop("justificacion"))
    pprint(resultado)