"""Verifica la conexión con Gemini y mide cuánto tarda en responder."""
import os
import time
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

modelo = os.getenv("LLM_MODEL", "gemini-3.8-flash")

# max_retries=0: si Google rechaza la solicitud, queremos ver el error en vez de esperar en silencio
llm = ChatGoogleGenerativeAI(model=modelo, max_retries=0)

# Dos llamadas seguidas, para separar el costo de la primera conexión del tiempo real del modelo
for intento in range(1, 3):
    inicio = time.time()
    respuesta = llm.invoke("Responde solo: 'Hola desde Gemini'")
    duracion = time.time() - inicio
    print(f"Intento {intento}: {respuesta.text} | {duracion:.1f} segundos")

print(f"Modelo: {modelo}")