"""Tests de guardar_evaluacion y generar_retroalimentacion (con LLM falso)."""

from agent.tools.guardar_evaluacion import guardar_evaluacion
from agent.tools import generar_retroalimentacion as modulo
from agent.tools.generar_retroalimentacion import (generar_retroalimentacion, calcular_progreso,
                                                   revisar_retroalimentacion)
from agent.memory.long_term import obtener_historial
from agent.memory.semantic import buscar_casos
from agent.prompts import build_student_prompt
from tests.fakes import LLMFalso

PROPUESTO = {"Content": 3, "Organization": 2.5, "Language": 3}


def datos(finales, razones):
    return {"cadete_id": "CDT-004", "task_id": "cadet_routine", "texto": "Hi Jim, I wake up at 6.",
            "corridas": [PROPUESTO] * 3, "puntajes_propuestos": PROPUESTO,
            "puntajes_finales": finales, "razones": razones, "accion": "revision_rapida",
            "debilidades": ["below_length"], "modelo": "test", "version_prompt": "test"}


# ---------- guardar_evaluacion ----------

def test_guardar_en_sqlite_y_chroma():
    finales = {"Content": 3, "Organization": 3, "Language": 3}
    resultado = guardar_evaluacion.invoke(datos(finales, {"Organization": "Greeting present"}))
    assert resultado["ok"] is True
    assert obtener_historial("CDT-004")[0]["ajustado"] is True
    casos = buscar_casos("greeting", task_id="cadet_routine", k=5)
    assert "Organization: system 2.5 -> teacher 3" in casos[0]["contenido"]


def test_ajuste_sin_razon_no_se_guarda():
    finales = {"Content": 3, "Organization": 3, "Language": 3}
    resultado = guardar_evaluacion.invoke(datos(finales, {}))
    assert "error" in resultado
    assert obtener_historial("CDT-004") == []


def test_puntaje_invalido_no_se_guarda():
    resultado = guardar_evaluacion.invoke(datos({"Content": 3.7, "Organization": 2.5, "Language": 3}, {}))
    assert "error" in resultado


# ---------- progreso ----------

def test_progreso_sin_historial():
    assert calcular_progreso([], ["below_length"])["tiene_historial"] is False


def test_progreso_superadas_y_persistentes():
    historial = [{"debilidades": ["missing_greeting", "below_length"]}]
    progreso = calcular_progreso(historial, ["below_length"])
    assert progreso["debilidades_superadas"] == ["missing_greeting"]
    assert progreso["debilidades_persistentes"] == ["below_length"]


# ---------- generar_retroalimentacion ----------

BUENA = ("¡Muy bien! Esta vez comenzaste tu mensaje con un saludo a Jim. También usaste "
         "vocabulario de la clase, como mess hall. Para mejorar: Escribiste: 'I go sleep'. "
         "Mejor: 'I go to sleep'. Consejo: lee tu texto en voz alta antes de entregarlo.")
CON_PUNTAJE = "Tu banda en Language es 3. " + BUENA


def generar_con(respuestas, monkeypatch):
    monkeypatch.setattr(modulo, "crear_llm", lambda **kwargs: LLMFalso(respuestas))
    return generar_retroalimentacion.invoke({
        "texto": "Hi Jim, I wake up at 6.", "task_id": "cadet_routine",
        "puntajes_finales": {"Content": 3, "Organization": 3, "Language": 3},
        "justificacion": "Justification...", "razones": {}, "progreso": {"tiene_historial": False}})


def test_revision_de_la_retroalimentacion():
    assert revisar_retroalimentacion(BUENA) == []
    assert "mentions_scores" in revisar_retroalimentacion(CON_PUNTAJE)
    assert "not_spanish" in revisar_retroalimentacion("Good job, you wrote a nice text today.")


def test_retroalimentacion_valida(monkeypatch):
    resultado = generar_con([BUENA], monkeypatch)
    assert resultado["retroalimentacion"] == BUENA
    assert resultado["advertencias"] == []


def test_regenera_si_menciona_puntajes(monkeypatch):
    resultado = generar_con([CON_PUNTAJE, BUENA], monkeypatch)
    assert resultado["retroalimentacion"] == BUENA


def test_advierte_si_falla_dos_veces(monkeypatch):
    resultado = generar_con([CON_PUNTAJE, CON_PUNTAJE], monkeypatch)
    assert "mentions_scores" in resultado["advertencias"]


def test_prompt_incluye_progreso_y_razones():
    prompt = build_student_prompt(
        "Hi Jim", "TASK", {"Content": 3}, "Justification", {"Organization": "Greeting present"},
        {"tiene_historial": True, "debilidades_superadas": ["missing_greeting"],
         "debilidades_persistentes": ["below_length"]})
    assert "Improved since the last text: the greeting at the start of the message" in prompt
    assert "Organization: Greeting present" in prompt