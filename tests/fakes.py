"""Objetos falsos para los tests: imitan al LLM sin llamar a ningún modelo real."""

from langchain_core.messages import AIMessage


class LLMFalso:
    """Devuelve las respuestas de la lista, en orden.
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