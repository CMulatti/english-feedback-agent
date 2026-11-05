"""
Memoria semántica: búsqueda por significado con Chroma.

Dos colecciones:
- "criterios": la rúbrica de Cambridge y los criterios institucionales, un fragmento por sección.
- "casos": evaluaciones confirmadas, con un resumen en inglés generado por código y el texto
  del estudiante. Se busca por significado: un texto nuevo encuentra textos parecidos, y una
  pregunta del profesor encuentra los resúmenes que tratan ese tema.
"""

import json
from functools import lru_cache

from config import settings


@lru_cache
def obtener_embeddings():
    """Carga el modelo de embeddings una sola vez (lru_cache guarda el resultado)."""
    from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)


def obtener_coleccion(nombre):
    from langchain_chroma import Chroma
    return Chroma(collection_name=nombre, embedding_function=obtener_embeddings(),
                  persist_directory=str(settings.CHROMA_DIR))


# ---------- Criterios ----------

def dividir_en_secciones(texto, fuente):
    """Divide un documento Markdown en un fragmento por cada sección '## '."""
    from langchain_core.documents import Document
    fragmentos = []
    for seccion in texto.split("\n## ")[1:]:
        titulo = seccion.splitlines()[0].strip()
        fragmentos.append(Document(page_content="## " + seccion.strip(),
                                   metadata={"fuente": fuente, "referencia": titulo}))
    return fragmentos


def indexar_criterios():
    """Reconstruye la colección de criterios a partir de criteria.md y la rúbrica."""
    fragmentos = []
    for archivo in ("criteria.md", "rubric_cambridge_a2.md"):
        texto = (settings.DATA_DIR / archivo).read_text(encoding="utf-8")
        fragmentos += dividir_en_secciones(texto, archivo)

    coleccion = obtener_coleccion("criterios")
    coleccion.reset_collection()
    coleccion.add_documents(fragmentos)
    return len(fragmentos)


# ---------- Casos ----------

def resumir_caso(caso):
    """
    Resumen en inglés, generado por código (no por el LLM), con el mismo formato siempre.
    Ejemplo: 'cadet_routine · Organization: system 2.5 -> teacher 3 (Reason: ...) · Weaknesses: below_length'
    """
    partes = [caso["task_id"]]
    razones = caso.get("razones") or {}
    for criterio, razon in razones.items():
        partes.append(f"{criterio}: system {caso['propuesto'][criterio]} -> teacher "
                      f"{caso['final'][criterio]} (Reason: {razon})")
    if not razones:
        partes.append("Teacher confirmed the proposed scores")
    if caso.get("debilidades"):
        partes.append("Weaknesses: " + ", ".join(caso["debilidades"]))
    return " · ".join(partes)


def agregar_caso(caso, referencia):
    """Agrega una evaluación confirmada a la memoria semántica."""
    from langchain_core.documents import Document
    resumen = resumir_caso(caso)
    documento = Document(
        page_content=resumen + "\nText: " + caso["texto"],
        metadata={"fuente": "caso", "referencia": str(referencia), "task_id": caso["task_id"],
                  "ajustado": bool(caso.get("razones")), "resumen": resumen},
    )
    obtener_coleccion("casos").add_documents([documento])


def indexar_casos_previos():
    """Reconstruye la colección de casos con los casos ficticios de data/casos_previos.json."""
    casos = json.loads((settings.DATA_DIR / "casos_previos.json").read_text(encoding="utf-8"))
    obtener_coleccion("casos").reset_collection()
    for numero, caso in enumerate(casos, start=1):
        agregar_caso(caso, f"mock-{numero}")
    return len(casos)


# ---------- Búsqueda ----------

def buscar_criterios(consulta, k=None):
    resultados = obtener_coleccion("criterios").similarity_search(consulta, k=k or settings.K_RESULTADOS)
    return [{"contenido": d.page_content, "fuente": d.metadata["fuente"],
             "referencia": d.metadata["referencia"]} for d in resultados]


def buscar_casos(consulta, task_id=None, solo_ajustados=False, k=None):
    """Busca casos parecidos. Si se indica task_id, solo busca dentro de esa tarea."""
    condiciones = []
    if task_id:
        condiciones.append({"task_id": task_id})
    if solo_ajustados:
        condiciones.append({"ajustado": True})
    filtro = None
    if len(condiciones) == 1:
        filtro = condiciones[0]
    elif len(condiciones) > 1:
        filtro = {"$and": condiciones}

    resultados = obtener_coleccion("casos").similarity_search(
        consulta, k=k or settings.K_RESULTADOS, filter=filtro)
    return [{"contenido": d.metadata["resumen"], "fuente": "caso",
             "referencia": d.metadata["referencia"]} for d in resultados]