"""
Tests del flujo completo, con un LLM falso.
Comprueban que las tools, las memorias y el planner funcionan juntos.
"""

import pytest

from agent import core
from agent.tools import evaluar_texto as modulo_evaluar
from agent.tools import generar_retroalimentacion as modulo_generar
from agent.memory.long_term import guardar_evaluacion as guardar_en_sqlite, obtener_historial
from tests.fakes import LLMFalso

SIN_SALUDO = "I wake up at 6.00 am and I have breakfast in the mess hall. Then I go to the classroom."
RETRO = ("¡Muy bien! Usaste vocabulario de la clase, como mess hall. Para mejorar: Escribiste: "
         "'I wake up at 6.00 am'. Mejor: 'Hello Jim, I wake up at 6.00 am'. Consejo: saluda siempre.")


def respuesta(c, o, l):
    return f"## Justification\nOK\n\nScores: Content {c} | Organization {o} | Language {l}"


def usar_llm(monkeypatch, evaluaciones, retroalimentaciones=()):
    """Reemplaza el LLM real por uno falso en las dos tools que lo usan."""
    monkeypatch.setattr(modulo_evaluar, "crear_llm", lambda: LLMFalso(evaluaciones))
    monkeypatch.setattr(modulo_generar, "crear_llm", lambda **k: LLMFalso(retroalimentaciones))


def historial_sin_saludo(cadete_id, veces):
    for numero in range(veces):
        guardar_en_sqlite({"fecha": f"2026-09-0{numero + 1}", "cadete_id": cadete_id,
                           "task_id": "weekend_email", "corridas": [],
                           "propuesto": {"Content": 3, "Organization": 2.5, "Language": 3},
                           "final": {"Content": 3, "Organization": 2.5, "Language": 3},
                           "razones": {}, "debilidades": ["missing_greeting"],
                           "accion": "revision_rapida", "modelo": "mock", "version_prompt": "mock"})


def test_texto_en_espanol_no_llama_al_llm(monkeypatch):
    usar_llm(monkeypatch, [])          # si se llamara al LLM, la lista vacía causaría un error
    resultado = core.procesar_texto("Yo me levanto a las seis de la mañana y después voy al casino con mis amigos. En la tarde tengo clases y luego hago deporte en el gimnasio con mi compañía.",
                                    "cadet_routine", "CDT-001")
    assert resultado["evaluado"] is False
    assert resultado["accion"]["motivo"] == "idioma"
    assert resultado["recomendaciones"] == []


def test_debilidad_recurrente(monkeypatch):
    historial_sin_saludo("CDT-004", 2)
    usar_llm(monkeypatch, [respuesta(3, 3, 3)] * 3)
    resultado = core.procesar_texto(SIN_SALUDO, "cadet_routine", "CDT-004")
    assert resultado["accion"]["tipo"] == "revision_rapida"
    assert resultado["recomendaciones"][0]["debilidad"] == "missing_greeting"


def test_recomendacion_visible_aunque_haya_desacuerdo(monkeypatch):
    # El caso de la demo real: caso dudoso, pero el profesor igual ve el refuerzo
    historial_sin_saludo("CDT-004", 2)
    usar_llm(monkeypatch, [respuesta(3, 3, 3), respuesta(3, 3, 5), respuesta(3, 3, 3.5)])
    resultado = core.procesar_texto(SIN_SALUDO, "cadet_routine", "CDT-004")
    assert resultado["accion"]["tipo"] == "caso_dudoso"
    assert resultado["recomendaciones"][0]["veces"] == 3


def test_evaluacion_fallida(monkeypatch):
    usar_llm(monkeypatch, ["sin puntajes"] * 6)
    resultado = core.procesar_texto(SIN_SALUDO, "cadet_routine", "CDT-001")
    assert resultado["evaluado"] is False
    assert resultado["accion"]["motivo"] == "evaluacion_fallida"


def test_confirmar_guarda_y_genera_retroalimentacion(monkeypatch):
    usar_llm(monkeypatch, [respuesta(3, 2.5, 3)] * 3, [RETRO])
    resultado = core.procesar_texto(SIN_SALUDO, "cadet_routine", "CDT-002")
    finales = {"Content": 3, "Organization": 3, "Language": 3}
    confirmado = core.confirmar_evaluacion(resultado, finales, {"Organization": "Clear sequence"})
    assert confirmado["guardado"]["ok"] is True
    assert confirmado["retroalimentacion"] == RETRO
    assert obtener_historial("CDT-002")[0]["puntajes_finales"] == finales


def test_confirmar_sin_razon_no_genera_retroalimentacion(monkeypatch):
    usar_llm(monkeypatch, [respuesta(3, 2.5, 3)] * 3, [])   # sin respuestas: no debe llamarse
    resultado = core.procesar_texto(SIN_SALUDO, "cadet_routine", "CDT-002")
    confirmado = core.confirmar_evaluacion(resultado, {"Content": 3, "Organization": 3,
                                                       "Language": 3}, {})
    assert "error" in confirmado["guardado"]
    assert "retroalimentacion" not in confirmado