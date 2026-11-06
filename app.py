"""
Interfaz del agente (Streamlit).

- Izquierda: panel de revisión. El profesor envía un texto, revisa la propuesta del agente,
  ajusta los puntajes si es necesario y confirma.
- Derecha: chat de solo lectura, con preguntas sugeridas.

Ejecutar desde la carpeta principal: streamlit run app.py

Cada vez que se hace clic en algo, Streamlit vuelve a ejecutar este archivo completo de arriba
hacia abajo. Las variables normales se reinician; lo que está en st.session_state se conserva.
Por eso ahí se guardan la evaluación abierta, la memoria del chat y la conversación.
"""

import json
import re

import streamlit as st

from config.settings import DATA_DIR
from agent.core import procesar_texto, confirmar_evaluacion
from agent.chat import MemoriaConversacion, responder, preguntas_sugeridas
from agent.rag.retrieval import list_tasks

CRITERIOS = ["Content", "Organization", "Language"]
ESTILO_ACCION = {
    "escalar_profesor": st.error,
    "caso_dudoso": st.warning,
    "priorizar_revision": st.warning,
    "revision_rapida": st.success,
}

st.set_page_config(page_title="A2 Writing Assessment Agent", layout="wide")


# ---------- Estado de la sesión ----------

def iniciar_estado():
    valores = {
        "resultado": None,          # evaluación abierta en el panel (salida de procesar_texto)
        "confirmacion": None,       # resultado de confirmar_evaluacion
        "memoria": MemoriaConversacion(),
        "conversacion": [],         # mensajes para mostrar: (rol, texto, tools usadas)
        "pregunta_pendiente": None, # pregunta enviada con un botón sugerido
        "task_id": list_tasks()[0],
        "cadete_id": "",
        "texto": "",
    }
    for clave, valor in valores.items():
        if clave not in st.session_state:
            st.session_state[clave] = valor


@st.cache_data
def cargar_demos():
    return json.loads((DATA_DIR / "demo_textos.json").read_text(encoding="utf-8"))


# ---------- Acciones (callbacks) ----------

def limpiar_propuesta():
    """
    Borra la propuesta y la confirmación mostradas en el panel.
    Se llama cuando cambia el texto, el cadete o la tarea: la propuesta anterior
    ya no corresponde a lo que está en el formulario.
    """
    st.session_state["resultado"] = None
    st.session_state["confirmacion"] = None


def cargar_demo():
    """Copia el texto de demostración elegido en los campos del formulario."""
    limpiar_propuesta()
    elegido = st.session_state["demo"]
    for demo in cargar_demos():
        if demo["escena"] == elegido:
            st.session_state.update(task_id=demo["task_id"], cadete_id=demo["cadete_id"],
                                    texto=demo["texto"])


def evaluar():
    with st.spinner("Assessing the text (3 runs)..."):
        resultado = procesar_texto(st.session_state["texto"], st.session_state["task_id"],
                                   st.session_state["cadete_id"].strip().upper())
    st.session_state["resultado"] = resultado
    st.session_state["confirmacion"] = None
    if resultado.get("evaluado"):
        for criterio in CRITERIOS:
            st.session_state[f"puntaje_{criterio}"] = resultado["evaluacion"]["mediana"][criterio]
            st.session_state[f"razon_{criterio}"] = ""


def confirmar():
    resultado = st.session_state["resultado"]
    finales = {c: st.session_state[f"puntaje_{c}"] for c in CRITERIOS}
    razones = {c: st.session_state[f"razon_{c}"] for c in CRITERIOS
               if finales[c] != resultado["evaluacion"]["mediana"][c]}
    with st.spinner("Saving and writing the cadet's feedback..."):
        st.session_state["confirmacion"] = confirmar_evaluacion(resultado, finales, razones)


def preguntar(pregunta):
    st.session_state["pregunta_pendiente"] = pregunta


def limpiar_chat():
    st.session_state["memoria"].limpiar()
    st.session_state["conversacion"] = []


# ---------- Panel de revisión ----------

def mostrar_formulario():
    st.selectbox("Load a demo text (optional)", [""] + [d["escena"] for d in cargar_demos()],
                 key="demo", on_change=cargar_demo)
    st.selectbox("Task", list_tasks(), key="task_id", on_change=limpiar_propuesta)
    st.text_input("Cadet code", key="cadete_id", placeholder="CDT-004", on_change=limpiar_propuesta)
    st.text_area("Cadet's text", key="texto", height=220, on_change=limpiar_propuesta)

    codigo_valido = re.fullmatch(r"CDT-\d{3}", st.session_state["cadete_id"].strip().upper())
    if st.session_state["cadete_id"] and not codigo_valido:
        st.caption(":red[The cadet code must look like CDT-004.]")
    st.button("Assess", type="primary", on_click=evaluar,
              disabled=not (codigo_valido and st.session_state["texto"].strip()))


def mostrar_propuesta(resultado):
    accion = resultado.get("accion")
    if accion:
        mostrar = ESTILO_ACCION.get(accion["tipo"], st.info)
        mostrar(f"**{accion['tipo']}** — {accion['razon']}")
    for recomendacion in resultado.get("recomendaciones", []):
        st.info(f"**Recommendation:** {recomendacion['razon']}")

    revision = resultado.get("revision")
    if revision:
        with st.expander("Automatic checks"):
            st.write(f"Words: {revision['palabras']} (minimum {revision['min_palabras']}, "
                     f"{int(revision['porcentaje_minimo'] * 100)}%)")
            st.write(f"Greeting: {revision['tiene_saludo']} · English: {revision['es_ingles']}")
            st.write(f"Taught vocabulary: {', '.join(revision['vocabulario_encontrado']) or 'none'}")
            st.write(f"Weaknesses: {', '.join(revision['debilidades']) or 'none'}")
        with st.expander(f"Cadet history ({len(resultado['historial'])} previous assessments)"):
            for evaluacion in resultado["historial"]:
                st.write(f"{evaluacion['fecha']} · {evaluacion['task_id']} · "
                         f"{evaluacion['puntajes_finales']} · {', '.join(evaluacion['debilidades']) or '-'}")

    if not resultado.get("evaluado"):
        st.caption("This text was not assessed. Grade it manually if appropriate.")
        return

    evaluacion = resultado["evaluacion"]
    if resultado.get("correcciones_usadas"):
        with st.expander(f"Teacher corrections used ({len(resultado['correcciones_usadas'])})"):
            for correccion in resultado["correcciones_usadas"]:
                st.write(f"- {correccion['contenido']} (case {correccion['referencia']})")

    st.markdown("#### Scores")
    st.caption("Runs: " + " · ".join(
        f"{c}: {', '.join(str(corrida[c]) for corrida in evaluacion['corridas'])}" for c in CRITERIOS))
    confirmado = st.session_state["confirmacion"] is not None and \
        "ok" in st.session_state["confirmacion"].get("guardado", {})

    for criterio in CRITERIOS:
        columna_puntaje, columna_razon = st.columns([1, 3])
        alerta = " ⚠️" if criterio in evaluacion["criterios_en_desacuerdo"] else ""
        columna_puntaje.number_input(f"{criterio}{alerta}", min_value=0.0, max_value=5.0, step=0.5,
                                     key=f"puntaje_{criterio}", disabled=confirmado)
        if st.session_state[f"puntaje_{criterio}"] != evaluacion["mediana"][criterio]:
            columna_razon.text_input(f"Reason for adjusting {criterio} (required)",
                                     key=f"razon_{criterio}", disabled=confirmado)

    with st.expander("Justification"):
        st.markdown(evaluacion["justificacion"])

    st.button("Confirm", type="primary", on_click=confirmar, disabled=confirmado)


def mostrar_confirmacion(confirmacion):
    guardado = confirmacion["guardado"]
    if "error" in guardado:
        st.error(guardado["error"] + " " + " ".join(guardado.get("problemas", [])))
        return
    st.success(f"Assessment saved (id {guardado['evaluacion_id']}).")
    st.markdown("#### Feedback for the cadet")
    st.text_area("Review it and copy it to release it to the cadet", confirmacion["retroalimentacion"],
                 height=220)
    for advertencia in confirmacion.get("advertencias", []):
        st.warning(f"Automatic check: {advertencia}")


# ---------- Chat ----------

def mostrar_chat(resultado):
    st.subheader("Ask the agent")
    st.caption("Read-only: the chat can explain and look things up, but cannot change scores.")

    for rol, texto, tools in st.session_state["conversacion"]:
        with st.chat_message(rol):
            st.markdown(texto)
            if tools:
                st.caption("Used: " + ", ".join(tools))

    task_id = resultado["task_id"] if resultado else st.session_state["task_id"]
    for numero, pregunta in enumerate(preguntas_sugeridas(resultado, task_id)):
        st.button(pregunta, key=f"sugerencia_{numero}", on_click=preguntar, args=(pregunta,))

    pregunta = st.chat_input("Type a question...") or st.session_state["pregunta_pendiente"]
    if pregunta:
        st.session_state["pregunta_pendiente"] = None
        with st.spinner("Thinking..."):
            respuesta = responder(pregunta, st.session_state["memoria"], resultado)
        st.session_state["conversacion"] += [("user", pregunta, []),
                                             ("assistant", respuesta["respuesta"],
                                              respuesta["tools_usadas"])]
        st.rerun()

    st.button("Clear conversation", on_click=limpiar_chat)


# ---------- Página ----------

iniciar_estado()
st.title("A2 Writing Assessment Agent")
st.caption("The agent proposes; the teacher decides.")

panel, chat = st.columns([3, 2], gap="large")
with panel:
    st.subheader("Review panel")
    mostrar_formulario()
    if st.session_state["resultado"]:
        st.divider()
        mostrar_propuesta(st.session_state["resultado"])
    if st.session_state["confirmacion"]:
        mostrar_confirmacion(st.session_state["confirmacion"])
with chat:
    mostrar_chat(st.session_state["resultado"])