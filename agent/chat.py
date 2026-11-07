"""
Chat con el agente: responde preguntas abiertas del profesor.

A diferencia del flujo principal (core.py), aquí el LLM DECIDE qué tool usar:
recibe la pregunta, elige una tool, lee el resultado y repite hasta poder responder.
Ese ciclo lo ejecuta create_agent de LangChain.

El chat es de solo lectura: solo tiene tools que consultan. No puede evaluar,
cambiar puntajes ni guardar nada; eso se hace únicamente desde el panel.

Memoria de corto plazo: la clase MemoriaConversacion guarda los mensajes de la sesión
(en la interfaz, vive en st.session_state). Se pierde al cerrar la sesión.
"""

import time

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from config import settings
from agent.llm import crear_llm, clasificar_error, nombre_modelo
from agent.observability import registrar_evento
from agent.tools.consultar_tarea import consultar_tarea
from agent.tools.consultar_historial import consultar_historial
from agent.tools.buscar_contexto import buscar_contexto

TOOLS_CHAT = [consultar_tarea, consultar_historial, buscar_contexto]
MAX_PASOS = 10   # límite de pasos del ciclo, para que el agente no entre en un ciclo infinito

CHAT_SYSTEM_PROMPT = """You are an assistant for English teachers at a military academy in Chile. Teachers use you while reviewing A2 writing assessments of cadets.

You can:
- Explain the assessment criteria and the Cambridge rubric (use buscar_contexto).
- Explain what a task expects (use consultar_tarea).
- Report a cadet's previous assessments and progress (use consultar_historial).
- Find how teachers resolved similar cases (use buscar_contexto).
- Explain the assessment currently open in the review panel (see <current_assessment>).

Rules:
- Use the tools to get facts. Never invent scores, cases or history.
- When you use the criteria or a previous case, cite it, for example (criteria.md, Format) or (case mock-3).
- You are read-only: you cannot change scores, confirm assessments or send feedback. If the teacher asks for that, explain that it is done in the review panel.
- Cadets are identified only by codes such as CDT-004. Do not speculate about the cadet beyond their writing.
- Answer in English, briefly and clearly.

<current_assessment>
{evaluacion_actual}
</current_assessment>"""


# ---------- Memoria de corto plazo ----------

class MemoriaConversacion:
    """Guarda los últimos mensajes de la conversación (pregunta del profesor y respuesta)."""

    def __init__(self, max_mensajes=20):
        self.max_mensajes = max_mensajes
        self.mensajes = []

    def agregar(self, pregunta, respuesta):
        self.mensajes += [HumanMessage(content=pregunta), AIMessage(content=respuesta)]
        # Si la conversación es muy larga, se descartan los mensajes más antiguos
        self.mensajes = self.mensajes[-self.max_mensajes:]

    def obtener(self):
        return list(self.mensajes)

    def limpiar(self):
        self.mensajes = []


# ---------- Contexto de la evaluación abierta ----------

def resumir_evaluacion(resultado):
    """Resume el resultado de procesar_texto para incluirlo en el prompt del chat."""
    if not resultado:
        return "No assessment is open in the review panel."
    lineas = [f"Cadet: {resultado['cadete_id']} · Task: {resultado['task_id']}",
              f"Text:\n{resultado['texto']}"]
    if resultado.get("accion"):
        lineas.append(f"Planner action: {resultado['accion']['tipo']} ({resultado['accion']['razon']})")
    for recomendacion in resultado.get("recomendaciones", []):
        lineas.append(f"Recommendation: {recomendacion['razon']}")
    if resultado.get("evaluado"):
        evaluacion = resultado["evaluacion"]
        lineas.append(f"Runs: {evaluacion['corridas']}")
        lineas.append(f"Proposed scores (median): {evaluacion['mediana']}")
        lineas.append(f"Criteria with disagreement: {evaluacion['criterios_en_desacuerdo'] or 'none'}")
        lineas.append(f"Justification:\n{evaluacion['justificacion']}")
    return "\n".join(lineas)


# ---------- Respuesta ----------

def describir_tools_usadas(mensajes):
    """
    Lista las tools que el agente decidió usar, con sus argumentos,
    por ejemplo: "consultar_historial(cadete_id=CDT-002)".
    Mostrar los argumentos hace visible qué decidió el agente, no solo qué tool eligió.
    """
    descripciones = []
    for mensaje in mensajes:
        for llamada in getattr(mensaje, "tool_calls", None) or []:
            argumentos = ", ".join(f"{k}={v}" for k, v in llamada["args"].items())
            descripciones.append(f"{llamada['name']}({argumentos})")
    return descripciones


def responder(pregunta, memoria, evaluacion_actual=None, llm=None):
    """
    Responde una pregunta del profesor. Devuelve la respuesta y las tools que el agente usó,
    para mostrarlas en la interfaz (así se ve qué decidió hacer el agente).
    """
    llm = llm or crear_llm()
    agente = create_agent(model=llm, tools=TOOLS_CHAT)
    mensajes = ([SystemMessage(content=CHAT_SYSTEM_PROMPT.format(
                    evaluacion_actual=resumir_evaluacion(evaluacion_actual)))]
                + memoria.obtener()
                + [HumanMessage(content=pregunta)])

    for intento in range(1, settings.MAX_REINTENTOS + 1):
        inicio = time.time()
        try:
            resultado = agente.invoke({"messages": mensajes},
                                      config={"recursion_limit": MAX_PASOS})
            break
        except Exception as error:
            tipo = clasificar_error(error)
            registrar_evento("llm", "chat", "error", int((time.time() - inicio) * 1000),
                             nombre_modelo(llm), tipo_error=tipo, detalle=str(error))
            if tipo in ("overloaded", "rate_limit", "timeout") and intento < settings.MAX_REINTENTOS:
                time.sleep(settings.ESPERA_REINTENTO)
                continue
            raise

    nuevos = resultado["messages"][len(mensajes):]
    respuesta = nuevos[-1].text
    tools_usadas = describir_tools_usadas(nuevos)

    # Registro: tokens sumados de todos los pasos del agente
    entrada = sum((getattr(m, "usage_metadata", None) or {}).get("input_tokens", 0) for m in nuevos)
    salida = sum((getattr(m, "usage_metadata", None) or {}).get("output_tokens", 0) for m in nuevos)
    registrar_evento("llm", "chat", "ok", int((time.time() - inicio) * 1000), nombre_modelo(llm),
                     entrada, salida, detalle="tools: " + ", ".join(tools_usadas))

    memoria.agregar(pregunta, respuesta)
    return {"respuesta": respuesta, "tools_usadas": tools_usadas}


# ---------- Preguntas sugeridas ----------

def preguntas_sugeridas(evaluacion_actual=None, task_id="cadet_routine"):
    """Botones de preguntas, según el momento: sin texto, después de evaluar o caso dudoso."""
    if not evaluacion_actual:
        return [f"What does the {task_id} task expect?",
                "Explain the criteria for Organization",
                "Why is half a band deducted when there is no greeting?"]

    cadete = evaluacion_actual["cadete_id"]
    tarea = evaluacion_actual["task_id"]
    if evaluacion_actual.get("accion", {}).get("tipo") == "caso_dudoso":
        return ["Why is this a doubtful case?",
                f"How did teachers resolve similar {tarea} cases?",
                f"How has {cadete} progressed?"]
    return ["Why did you give these scores?",
            f"How has {cadete} progressed?",
            f"Show similar past cases for {tarea}"]


# Prueba manual con Gemini: python -m agent.chat
if __name__ == "__main__":
    memoria = MemoriaConversacion()
    for pregunta in ["How has CDT-004 progressed?",
                     "Why is half a band deducted when there is no greeting?",
                     "And what do the criteria say about the ending?"]:
        print(f"\nTeacher: {pregunta}")
        r = responder(pregunta, memoria)
        print(f"Agent (tools: {', '.join(r['tools_usadas']) or 'none'}): {r['respuesta']}")