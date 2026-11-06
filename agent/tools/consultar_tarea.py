"""
Tool: consulta la ficha de una tarea.

Lee el archivo de la tarea en data/tasks/ y devuelve sus datos en un diccionario,
para que el resto del agente no tenga que interpretar el Markdown.
"""

import re

from langchain_core.tools import tool

from agent.observability import registrar_tool

from config.settings import TASKS_DIR
from agent.rag.retrieval import get_field
from agent.rag.checks import get_section, get_task_vocabulary


# ---------- Funciones auxiliares ----------

def leer_instrucciones(texto):
    """Devuelve las líneas desde 'Instructions:' hasta la primera línea vacía o título."""
    lineas = []
    dentro = False
    for linea in texto.splitlines():
        if linea.startswith("Instructions:"):
            dentro = True
            lineas.append(linea.split(":", 1)[1].strip())
        elif dentro:
            if not linea.strip() or linea.startswith("#"):
                break
            lineas.append(linea.strip())
    return " ".join(lineas)


def leer_lista(texto, titulo):
    """
    Lee una sección con elementos que empiezan con '- ' o con un número ('1. ').
    Si un elemento continúa en la línea siguiente (con sangría), se une al anterior.
    """
    elementos = []
    for linea in get_section(texto, titulo):
        limpia = linea.strip()
        if not limpia:
            continue
        if limpia.startswith("- ") or re.match(r"^\d+\.", limpia):
            elementos.append(limpia)
        elif elementos:
            elementos[-1] += " " + limpia
    return elementos


def leer_puntos_contenido(texto):
    """Convierte '1. [essential] Daily routine' en {'tipo': 'essential', 'texto': 'Daily routine'}."""
    puntos = []
    for elemento in leer_lista(texto, "Required content points"):
        encontrado = re.search(r"\[(essential|accessory)\]\s*(.+)", elemento)
        if encontrado:
            puntos.append({"tipo": encontrado.group(1), "texto": encontrado.group(2)})
    return puntos


def leer_ficha(task_id):
    """Lee la ficha de una tarea. Devuelve {'error': ...} si no existe."""
    ruta = TASKS_DIR / f"{task_id}.md"
    if not ruta.exists():
        return {"error": f"Tarea no encontrada: {task_id}"}

    texto = ruta.read_text(encoding="utf-8")
    gramatica = [g[2:] for g in leer_lista(texto, "Target grammar")]

    return {
        "task_id": task_id,
        "nivel": get_field(texto, "Level"),
        "instrucciones": leer_instrucciones(texto),
        "min_palabras": int(get_field(texto, "Minimum words")),
        "max_palabras": int(get_field(texto, "Maximum words")),
        "requiere_saludo": (get_field(texto, "Requires greeting") or "no").lower() == "yes",
        "puntos_contenido": leer_puntos_contenido(texto),
        "gramatica_objetivo": gramatica,
        "vocabulario": get_task_vocabulary(texto),
        "vocabulario_extra": get_field(texto, "Extra vocabulary"),
    }


# ---------- La tool ----------

@tool
@registrar_tool
def consultar_tarea(task_id: str) -> dict:
    """Return the task sheet for a writing task: instructions, expected length,
    whether a greeting is required, content points (essential or accessory),
    target grammar and taught vocabulary. Use it when you need to know what a
    task expects. Valid task_id values are file names in data/tasks/, such as
    'cadet_routine' or 'santiago_tourism'."""
    return leer_ficha(task_id)


# Prueba manual: python -m agent.tools.consultar_tarea
if __name__ == "__main__":
    from pprint import pprint
    pprint(consultar_tarea.invoke({"task_id": "cadet_routine"}))