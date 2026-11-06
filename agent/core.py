"""
Núcleo del agente: ejecuta el flujo completo de una evaluación.

- procesar_texto(): desde que el profesor envía el texto hasta la propuesta del panel.
  Revisión → historial → planner (reglas 1-2 y recomendaciones) → correcciones similares →
  evaluación ×3 → planner (reglas 3-5).
- confirmar_evaluacion(): después de que el profesor revisa y confirma.
  Guardar en las memorias → retroalimentación para el cadete.

Este flujo es determinista: siempre ejecuta las mismas tools en el mismo orden, y el
planner decide la acción. El LLM solo se usa dentro de evaluar_texto y
generar_retroalimentacion. Así cada decisión queda trazable.
"""

from dataclasses import asdict

from agent.planner import (Accion, construir_estado, revisar_antes_de_evaluar, decidir_accion,
                           recomendar)
from agent.memory.semantic import buscar_casos
from agent.observability import registrar_evento
from agent.tools.revisar_texto import revisar_texto
from agent.tools.consultar_historial import consultar_historial
from agent.tools.evaluar_texto import evaluar_texto
from agent.tools.guardar_evaluacion import guardar_evaluacion
from agent.tools.generar_retroalimentacion import generar_retroalimentacion, calcular_progreso


def buscar_correcciones(texto, task_id):
    """
    Correcciones de profesores en textos parecidos de la misma tarea.
    Si la memoria semántica no está disponible, se evalúa igual (sin correcciones).
    """
    try:
        return buscar_casos(texto, task_id=task_id, solo_ajustados=True)
    except Exception as error:
        registrar_evento("memoria", "buscar_correcciones", "error",
                         tipo_error="semantic_unavailable", detalle=str(error))
        return []


def procesar_texto(texto, task_id, cadete_id):
    """Ejecuta el flujo hasta la propuesta. No guarda nada: eso ocurre al confirmar."""
    resultado = {"texto": texto, "task_id": task_id, "cadete_id": cadete_id}

    # 1. Hechos objetivos y memoria de largo plazo
    revision = revisar_texto.invoke({"texto": texto, "task_id": task_id})
    if "error" in revision:
        return {**resultado, "evaluado": False, "error": revision["error"]}
    historial = consultar_historial.invoke({"cadete_id": cadete_id})
    resultado.update({"revision": revision, "historial": historial,
                      "progreso": calcular_progreso(historial, revision["debilidades"])})

    # 2. Planner: recomendaciones para el cadete (se muestran siempre)
    #    y reglas 1 y 2: si el texto no se debe evaluar, no se llama al LLM
    estado_previo = construir_estado(revision, None, historial)
    resultado["recomendaciones"] = recomendar(estado_previo)
    accion = revisar_antes_de_evaluar(estado_previo)
    if accion:
        return {**resultado, "evaluado": False, "accion": asdict(accion)}

    # 3. Memoria semántica y evaluación
    correcciones = buscar_correcciones(texto, task_id)
    evaluacion = evaluar_texto.invoke({"texto": texto, "task_id": task_id,
                                       "revision": revision, "casos_similares": correcciones})
    if "error" in evaluacion:
        accion = Accion("escalar_profesor", "evaluacion_fallida",
                        "The model could not complete the assessment. Try again later or grade manually.")
        return {**resultado, "evaluado": False, "accion": asdict(accion)}

    # 4. Planner, reglas 3 a 5
    accion = decidir_accion(construir_estado(revision, evaluacion, historial))
    return {**resultado, "evaluado": True, "correcciones_usadas": correcciones,
            "evaluacion": evaluacion, "accion": asdict(accion)}


def confirmar_evaluacion(resultado, puntajes_finales, razones):
    """Guarda la evaluación confirmada y genera la retroalimentación con los puntajes finales."""
    evaluacion = resultado["evaluacion"]
    guardado = guardar_evaluacion.invoke({
        "cadete_id": resultado["cadete_id"],
        "task_id": resultado["task_id"],
        "texto": resultado["texto"],
        "corridas": evaluacion["corridas"],
        "puntajes_propuestos": evaluacion["mediana"],
        "puntajes_finales": puntajes_finales,
        "razones": razones,
        "accion": resultado["accion"]["tipo"],
        "debilidades": resultado["revision"]["debilidades"],
        "modelo": evaluacion["modelo"],
        "version_prompt": evaluacion["version_prompt"],
    })
    if "error" in guardado:
        return {"guardado": guardado}

    retroalimentacion = generar_retroalimentacion.invoke({
        "texto": resultado["texto"],
        "task_id": resultado["task_id"],
        "puntajes_finales": puntajes_finales,
        "justificacion": evaluacion["justificacion"],
        "razones": razones,
        "progreso": resultado["progreso"],
    })
    return {"guardado": guardado, **retroalimentacion}


# Prueba manual: python -m agent.core
if __name__ == "__main__":
    from pprint import pprint

    print("=== Escenario 1: texto en español (reglas 1-2, sin llamar al LLM)")
    r = procesar_texto("Yo me levanto a las seis de la mañana y después voy al casino con mis amigos. En la tarde tengo clases y luego hago deporte en el gimnasio con mi compañía.",
                       "cadet_routine", "CDT-001")
    pprint(r["accion"])

    print("\n=== Escenario 2: tercer texto de CDT-004 sin saludo (evaluación completa con Gemini)")
    muestra = (
        "Every day I wake up at 6:00 in the barracks. I make my bed and I put on my uniform. "
        "At 6:30 we form up in the formation area and after that we go to the mess hall for "
        "breakfast. In the morning I have classes of English, history and military subjects. "
        "At 1 pm I have lunch with my company. In the afternoon I do PT in the gym or we practice "
        "for the parade. Sometimes I have fireguard duty at night. Before sleep I study in the "
        "library. I think the life in the academy is hard but is good for me."
    )
    r = procesar_texto(muestra, "cadet_routine", "CDT-004")
    print("Debilidades:", r["revision"]["debilidades"])
    print("Historial previo:", [h["debilidades"] for h in r["historial"]])
    if r["evaluado"]:
        print("Corridas:", r["evaluacion"]["corridas"])
        print("Propuesta:", r["evaluacion"]["mediana"])
    print("Acción de revisión:")
    pprint(r["accion"])
    print("Recomendaciones:")
    pprint(r["recomendaciones"])