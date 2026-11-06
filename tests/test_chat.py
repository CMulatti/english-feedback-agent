"""Tests del chat (agente con tools), con un modelo falso que simula las decisiones del LLM."""

from langchain_core.messages import AIMessage

from agent.chat import MemoriaConversacion, responder, preguntas_sugeridas, resumir_evaluacion
from agent.memory.long_term import guardar_evaluacion
from agent.observability import obtener_eventos
from tests.fakes import ChatFalsoConTools


def modelo(*respuestas):
    return ChatFalsoConTools(messages=iter(respuestas))


def usa_tool(nombre, argumentos):
    """Simula que el modelo decide llamar a una tool."""
    return AIMessage(content="", tool_calls=[{"name": nombre, "args": argumentos, "id": "1"}])


def test_el_agente_usa_la_tool_elegida():
    guardar_evaluacion({"fecha": "2026-09-01", "cadete_id": "CDT-004", "task_id": "weekend_email",
                        "corridas": [], "propuesto": {"Content": 3, "Organization": 3, "Language": 3},
                        "final": {"Content": 3, "Organization": 3, "Language": 3}, "razones": {},
                        "debilidades": ["missing_greeting"], "accion": "revision_rapida",
                        "modelo": "mock", "version_prompt": "mock"})
    memoria = MemoriaConversacion()
    llm = modelo(usa_tool("consultar_historial", {"cadete_id": "CDT-004"}),
                 AIMessage(content="CDT-004 has one previous assessment."))
    resultado = responder("How has CDT-004 progressed?", memoria, llm=llm)
    assert resultado["tools_usadas"] == ["consultar_historial"]
    assert resultado["respuesta"] == "CDT-004 has one previous assessment."


def test_respuesta_sin_tools():
    resultado = responder("Hello", MemoriaConversacion(), llm=modelo(AIMessage(content="Hi!")))
    assert resultado["tools_usadas"] == []


def test_memoria_guarda_la_conversacion():
    memoria = MemoriaConversacion()
    responder("First question", memoria, llm=modelo(AIMessage(content="First answer")))
    responder("Second question", memoria, llm=modelo(AIMessage(content="Second answer")))
    assert [m.content for m in memoria.obtener()] == ["First question", "First answer",
                                                       "Second question", "Second answer"]


def test_memoria_descarta_los_mensajes_antiguos():
    memoria = MemoriaConversacion(max_mensajes=4)
    for numero in range(3):
        memoria.agregar(f"Q{numero}", f"A{numero}")
    assert memoria.obtener()[0].content == "Q1"


def test_el_chat_queda_registrado():
    responder("Hello", MemoriaConversacion(), llm=modelo(AIMessage(content="Hi!")))
    assert obtener_eventos(limite=1)[0]["nombre"] == "chat"


def test_preguntas_sugeridas_segun_el_momento():
    assert "Explain the criteria for Organization" in preguntas_sugeridas()
    caso = {"cadete_id": "CDT-004", "task_id": "cadet_routine", "accion": {"tipo": "caso_dudoso"}}
    assert "Why is this a doubtful case?" in preguntas_sugeridas(caso)
    normal = {**caso, "accion": {"tipo": "revision_rapida"}}
    assert "How has CDT-004 progressed?" in preguntas_sugeridas(normal)


def test_resumen_sin_evaluacion():
    assert "No assessment is open" in resumir_evaluacion(None)