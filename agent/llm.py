"""
Conexión con el modelo de lenguaje.

- crear_llm(): crea el modelo según LLM_PROVIDER y LLM_MODEL del archivo .env.
  Cambiar de proveedor (por ejemplo, de Gemini a Claude) es cambiar esas dos líneas.
- invocar_llm(): llama al modelo, reintenta si está saturado y registra cada intento.
"""

import os
import time

from dotenv import load_dotenv

from config import settings
from agent.observability import registrar_evento

load_dotenv()


def crear_llm(temperature=0.2):
    proveedor = os.getenv("LLM_PROVIDER", "google")
    modelo = os.getenv("LLM_MODEL", "gemini-3.5-flash-lite")

    # max_retries=0: los reintentos los hace invocar_llm, para poder registrar cada uno
    if proveedor == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=modelo, temperature=temperature, max_retries=0)
    if proveedor == "anthropic":
        from langchain_anthropic import ChatAnthropic   # requiere: pip install langchain-anthropic
        return ChatAnthropic(model=modelo, temperature=temperature, max_retries=0)
    raise ValueError(f"Proveedor no soportado: {proveedor}")


def nombre_modelo(llm):
    return getattr(llm, "model", None) or getattr(llm, "model_name", None) or "desconocido"


def clasificar_error(error):
    """Traduce un error del proveedor a un código fijo, para contarlos en la Etapa 3."""
    texto = str(error).lower()
    if "503" in texto or "unavailable" in texto or "overloaded" in texto:
        return "overloaded"
    if "429" in texto or "resource_exhausted" in texto or "rate limit" in texto:
        return "rate_limit"
    if "timeout" in texto or "timed out" in texto:
        return "timeout"
    return "other"


def invocar_llm(llm, mensajes, nombre="llm"):
    """
    Envía los mensajes al modelo y devuelve el texto de la respuesta.
    Si el modelo está saturado o hay límite de solicitudes, espera y reintenta.
    Cada intento queda en el registro de eventos, con su duración y tokens.
    """
    modelo = nombre_modelo(llm)
    for intento in range(1, settings.MAX_REINTENTOS + 1):
        inicio = time.time()
        try:
            respuesta = llm.invoke(mensajes)
        except Exception as error:
            tipo = clasificar_error(error)
            registrar_evento("llm", nombre, "error", int((time.time() - inicio) * 1000),
                             modelo, tipo_error=tipo, detalle=str(error))
            if tipo in ("overloaded", "rate_limit", "timeout") and intento < settings.MAX_REINTENTOS:
                print(f"   Modelo no disponible ({tipo}), reintento {intento + 1} "
                      f"en {settings.ESPERA_REINTENTO} s...")
                time.sleep(settings.ESPERA_REINTENTO)
                continue
            raise

        duracion = int((time.time() - inicio) * 1000)
        uso = getattr(respuesta, "usage_metadata", None) or {}
        texto = respuesta.text

        if not texto.strip():
            registrar_evento("llm", nombre, "error", duracion, modelo,
                             uso.get("input_tokens"), uso.get("output_tokens"),
                             tipo_error="empty_response")
            raise ValueError("El modelo devolvió una respuesta vacía.")

        registrar_evento("llm", nombre, "ok", duracion, modelo,
                         uso.get("input_tokens"), uso.get("output_tokens"))
        return texto


# Prueba manual: python -m agent.llm
if __name__ == "__main__":
    from agent.observability import obtener_eventos
    llm = crear_llm()
    print(invocar_llm(llm, "Reply only: 'Hello from the agent'", nombre="prueba"))
    print(obtener_eventos(limite=1))