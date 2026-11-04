"""Tests de las tools del agente. Ejecutar con: pytest -v"""

from agent.tools.consultar_tarea import consultar_tarea


# ---------- consultar_tarea ----------

def test_consultar_tarea_cadet_routine():
    ficha = consultar_tarea.invoke({"task_id": "cadet_routine"})
    assert ficha["min_palabras"] == 100
    assert ficha["max_palabras"] == 150
    assert ficha["requiere_saludo"] is True
    assert len(ficha["puntos_contenido"]) == 4
    assert ficha["puntos_contenido"][0]["tipo"] == "essential"
    assert "mess hall" in ficha["vocabulario"]


def test_consultar_tarea_santiago_sin_saludo():
    ficha = consultar_tarea.invoke({"task_id": "santiago_tourism"})
    assert ficha["requiere_saludo"] is False
    esenciales = [p for p in ficha["puntos_contenido"] if p["tipo"] == "essential"]
    assert len(esenciales) == 4


def test_consultar_tarea_no_existe():
    ficha = consultar_tarea.invoke({"task_id": "tarea_inventada"})
    assert "error" in ficha