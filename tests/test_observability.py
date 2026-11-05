"""Tests del registro de ejecución y de invocar_llm (sin llamar a un modelo real)."""

import pytest
from langchain_core.messages import AIMessage

from agent.observability import registrar_evento, obtener_eventos
from agent.llm import invocar_llm, clasificar_error
from agent.tools.consultar_tarea import consultar_tarea


class LLMFalso:
    """Imita un modelo: devuelve las respuestas de la lista, en orden.
    Si un elemento es una excepción, la lanza en vez de responder."""
    model = "modelo-falso"

    def __init__(self, respuestas):
        self.respuestas = list(respuestas)

    def invoke(self, mensajes):
        respuesta = self.respuestas.pop(0)
        if isinstance(respuesta, Exception):
            raise respuesta
        return AIMessage(content=respuesta,
                         usage_metadata={"input_tokens": 50, "output_tokens": 10,
                                         "total_tokens": 60})


def test_registrar_y_leer_evento():
    registrar_evento("tool", "prueba", "ok", duracion_ms=5)
    evento = obtener_eventos(limite=1)[0]
    assert evento["nombre"] == "prueba"
    assert evento["resultado"] == "ok"


def test_tool_queda_registrada():
    consultar_tarea.invoke({"task_id": "cadet_routine"})
    evento = obtener_eventos(limite=1)[0]
    assert evento["componente"] == "tool"
    assert evento["nombre"] == "consultar_tarea"


def test_tool_con_error_queda_registrada():
    consultar_tarea.invoke({"task_id": "tarea_inventada"})
    assert obtener_eventos(limite=1)[0]["resultado"] == "error"


def test_invocar_llm_registra_tokens():
    texto = invocar_llm(LLMFalso(["Hola"]), "Hi", nombre="prueba")
    evento = obtener_eventos(limite=1)[0]
    assert texto == "Hola"
    assert evento["tokens_entrada"] == 50
    assert evento["modelo"] == "modelo-falso"


def test_invocar_llm_reintenta_si_esta_saturado():
    llm = LLMFalso([Exception("503 UNAVAILABLE high demand"), "Hola"])
    texto = invocar_llm(llm, "Hi", nombre="prueba")
    eventos = obtener_eventos(limite=2)          # el más reciente primero
    assert texto == "Hola"
    assert eventos[1]["tipo_error"] == "overloaded"
    assert eventos[0]["resultado"] == "ok"


def test_invocar_llm_respuesta_vacia():
    with pytest.raises(ValueError):
        invocar_llm(LLMFalso(["   "]), "Hi")
    assert obtener_eventos(limite=1)[0]["tipo_error"] == "empty_response"


def test_clasificar_error():
    assert clasificar_error(Exception("429 RESOURCE_EXHAUSTED")) == "rate_limit"
    assert clasificar_error(Exception("algo raro")) == "other"