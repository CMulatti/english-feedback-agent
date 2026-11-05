"""
Tool: revisa el texto de un estudiante con código, sin usar el LLM.

Produce hechos objetivos que usan el planner (reglas 1, 2 y 4) y el prompt de evaluación:
extensión, vocabulario enseñado, saludo, palabras en español e instrucciones sospechosas.
"""

import re

from langchain_core.tools import tool

from agent.observability import registrar_tool

from config import settings
from retrieval import load_task, load_extra_vocabulary
from checks import count_words, find_taught_vocabulary
from agent.tools.consultar_tarea import leer_ficha


# ---------- Listas de referencia ----------

SALUDOS = ("dear", "hi", "hello", "hey", "good morning", "good afternoon",
           "good evening", "greetings")

# Palabras en español que no existen en inglés. Se dejan fuera las ambiguas,
# como "a", "me", "no", "son" o "pan", que también son palabras en inglés.
PALABRAS_ESPANOL = {
    "de", "del", "que", "para", "por", "muy", "pero", "porque", "con", "en", "y",
    "el", "la", "los", "las", "lo", "una", "uno", "unos", "unas", "es", "se",
    "mi", "mis", "tu", "su", "sus", "yo", "nosotros", "también", "cuando", "donde",
    "como", "entonces", "después", "luego", "hoy", "día", "mañana", "tarde", "noche",
    "semana", "amigos", "casa", "comida", "aprox", "ingles", "inglés", "hay", "tengo",
    "estoy", "está", "están", "más", "todos", "todas", "bueno", "buena",
}

# Frases típicas de un intento de manipular la evaluación (prompt injection)
PATRONES_SOSPECHOSOS = [
    r"ignore (all |the |any |previous |above |your )*(instructions|rules|rubric|criteria)",
    r"(give|assign) (me |this text |this |it )?(a |an )?(5|five|full|maximum|top|perfect)",
    r"you are (now )?(a|an|the) ",
    r"system prompt",
    r"ignora (las |todas las )?(instrucciones|reglas)",
    r"(ponme|dame|pon) (un |una )?(5|7|nota)",
]


# ---------- Funciones auxiliares ----------

def tiene_saludo(texto):
    """Revisa si la primera línea con contenido empieza con un saludo."""
    for linea in texto.splitlines():
        if linea.strip():
            primera = linea.strip().lower()
            return any(re.match(rf"{saludo}\b", primera) for saludo in SALUDOS)
    return False


def buscar_palabras_espanol(texto):
    """
    Devuelve las palabras en español del texto.
    No cuenta las que forman parte de un nombre propio, como "del" en "Viña del Mar"
    (una palabra entre dos palabras con mayúscula), ni nombres con tilde como "Pucón".
    """
    palabras = re.findall(r"[A-Za-zÁÉÍÓÚÑÜáéíóúñü]+", texto)
    encontradas = []
    for i, palabra in enumerate(palabras):
        anterior = palabras[i - 1] if i > 0 else ""
        siguiente = palabras[i + 1] if i + 1 < len(palabras) else ""
        dentro_de_nombre = anterior[:1].isupper() and siguiente[:1].isupper()
        es_nombre_con_tilde = palabra[:1].isupper() and re.search(r"[áéíóúñ]", palabra)

        if dentro_de_nombre or es_nombre_con_tilde:
            continue
        minuscula = palabra.lower()
        if minuscula in PALABRAS_ESPANOL or re.search(r"[áéíóúñ]", minuscula):
            encontradas.append(minuscula)
    return encontradas


def tiene_instrucciones_sospechosas(texto):
    minuscula = texto.lower()
    return any(re.search(patron, minuscula) for patron in PATRONES_SOSPECHOSOS)


def estado_extension(porcentaje):
    """Traduce el porcentaje del mínimo de palabras a un código fijo."""
    if porcentaje < settings.UMBRAL_TEXTO_MINIMO:
        return "insufficient"
    if porcentaje < 0.8:
        return "below_80_percent"
    if porcentaje < 1:
        return "below_minimum"
    return "within_or_above"


# ---------- Revisión completa ----------

def revisar(texto, task_id):
    """Ejecuta todas las revisiones. Devuelve {'error': ...} si la tarea no existe."""
    ficha = leer_ficha(task_id)
    if "error" in ficha:
        return ficha

    palabras = count_words(texto)
    porcentaje = palabras / ficha["min_palabras"]

    task_text = load_task(task_id)
    vocabulario = find_taught_vocabulary(texto, task_text, load_extra_vocabulary(task_text))

    saludo = tiene_saludo(texto) if ficha["requiere_saludo"] else None
    espanol = buscar_palabras_espanol(texto)
    proporcion_espanol = len(espanol) / palabras if palabras else 0

    debilidades = []
    if saludo is False:
        debilidades.append("missing_greeting")
    if palabras < ficha["min_palabras"]:
        debilidades.append("below_length")
    if not vocabulario:
        debilidades.append("no_taught_vocabulary")
    if len(espanol) >= settings.MIN_PALABRAS_ESPANOL:
        debilidades.append("spanish_words")

    return {
        "palabras": palabras,
        "min_palabras": ficha["min_palabras"],
        "porcentaje_minimo": round(porcentaje, 2),
        "estado_extension": estado_extension(porcentaje),
        "vocabulario_encontrado": vocabulario,
        "tiene_saludo": saludo,
        "palabras_espanol": espanol,
        "proporcion_espanol": round(proporcion_espanol, 2),
        "es_ingles": proporcion_espanol <= settings.UMBRAL_IDIOMA,
        "instrucciones_sospechosas": tiene_instrucciones_sospechosas(texto),
        "debilidades": debilidades,
    }


# ---------- La tool ----------

@tool
@registrar_tool
def revisar_texto(texto: str, task_id: str) -> dict:
    """Check a student's text with exact, rule-based code (no AI): word count
    against the task's expected length, taught vocabulary found, whether the
    required greeting is present, Spanish words, whether the text is in English,
    and suspicious instructions aimed at the system. Returns a list of weakness
    codes such as 'missing_greeting', 'below_length', 'no_taught_vocabulary'
    and 'spanish_words'."""
    return revisar(texto, task_id)


# Prueba manual: python -m agent.tools.revisar_texto
if __name__ == "__main__":
    from pprint import pprint
    ejemplo = ("I wake up at 6.00 am. Next, I go to the mess hall con mis amigos "
               "and have breakfast. Finally I go to sleep in the barracks.")
    pprint(revisar_texto.invoke({"texto": ejemplo, "task_id": "cadet_routine"}))