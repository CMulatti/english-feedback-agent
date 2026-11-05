"""Tests de evaluar_texto, con un LLM falso (no se llama a Gemini)."""

import pytest

from agent.tools import evaluar_texto as modulo
from agent.tools.evaluar_texto import evaluar_texto, leer_puntajes
from agent.tools.revisar_texto import revisar
from agent.prompts import build_teacher_prompt
from retrieval import retrieve_context
from tests.fakes import LLMFalso

TEXTO = "Hi Jim,\nI wake up at 6.00 am and I have breakfast in the mess hall."


def respuesta(content, organization, language, nota="Justification..."):
    return f"## Justification\n{nota}\n\nScores: Content {content} | Organization {organization} | Language {language}"


def evaluar_con(respuestas, monkeypatch):
    """Ejecuta evaluar_texto reemplazando el LLM real por uno falso."""
    monkeypatch.setattr(modulo, "crear_llm", lambda: LLMFalso(respuestas))
    revision = revisar(TEXTO, "cadet_routine")
    return evaluar_texto.invoke({"texto": TEXTO, "task_id": "cadet_routine", "revision": revision})


def test_leer_puntajes():
    assert leer_puntajes(respuesta(3, 2.5, 3)) == {"Content": 3, "Organization": 2.5, "Language": 3}
    assert leer_puntajes("**Scores:** Content 3 | Organization 2,5 | Language 3")["Organization"] == 2.5
    assert leer_puntajes("Sin línea de puntajes") is None
    assert leer_puntajes("Scores: Content 3.7 | Organization 3 | Language 3") is None


def test_corridas_coinciden(monkeypatch):
    resultado = evaluar_con([respuesta(3, 3, 3), respuesta(3, 3, 2.5), respuesta(3, 2.5, 3)], monkeypatch)
    assert resultado["mediana"] == {"Content": 3, "Organization": 3, "Language": 3}
    assert resultado["criterios_en_desacuerdo"] == []


def test_corridas_en_desacuerdo(monkeypatch):
    # El ejemplo de la Etapa 1: Language 3, 5 y 3.5
    resultado = evaluar_con([respuesta(3, 3, 3), respuesta(3, 3, 5), respuesta(3, 2.5, 3.5)], monkeypatch)
    assert resultado["mediana"]["Language"] == 3.5
    assert resultado["criterios_en_desacuerdo"] == ["Language"]


def test_reintenta_si_falta_scores(monkeypatch):
    resultado = evaluar_con(["Olvidé los puntajes", respuesta(3, 3, 3),
                             respuesta(3, 3, 3), respuesta(3, 3, 3)], monkeypatch)
    assert len(resultado["corridas"]) == 3
    assert "missing_scores" in resultado["errores"]


def test_justificacion_mas_cercana_a_la_mediana(monkeypatch):
    resultado = evaluar_con([respuesta(3, 3, 3, "A"), respuesta(3, 3, 5, "B"),
                             respuesta(3, 3, 3.5, "C")], monkeypatch)
    assert "C" in resultado["justificacion"]


def test_todas_las_corridas_fallan(monkeypatch):
    fallas = ["sin puntajes"] * 6
    resultado = evaluar_con(fallas, monkeypatch)
    assert "error" in resultado


def test_prompt_incluye_revision_y_correcciones():
    revision = revisar(TEXTO, "cadet_routine")
    casos = [{"contenido": "cadet_routine · Organization: system 2.5 -> teacher 3"}]
    prompt = build_teacher_prompt(TEXTO, retrieve_context("cadet_routine"), revision, casos)
    assert "Greeting: present" in prompt
    assert "system 2.5 -> teacher 3" in prompt
    assert "<student_text>" in prompt


def test_una_corrida_falla(monkeypatch):
    # La corrida 3 falla dos veces sin puntajes: quedan 2 corridas (Content 3 y 2)
    resultado = evaluar_con([respuesta(3, 3, 4), respuesta(2, 3, 3.5),
                             "sin puntajes", "sin puntajes"], monkeypatch)
    assert resultado["corridas_validas"] == 2
    assert resultado["mediana"]["Content"] == 2        # median_low: un valor real, no 2.5
    assert resultado["criterios_en_desacuerdo"] == ["Content"]