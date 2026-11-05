"""
Tests de la memoria de largo plazo. Ejecutar con: pytest -v

La base de datos temporal se configura en tests/conftest.py.
"""

from agent.memory.long_term import guardar_evaluacion, obtener_historial
from agent.tools.consultar_historial import consultar_historial


def evaluacion_de_prueba(cadete_id, fecha, debilidades, final_organization=3):
    return {
        "fecha": fecha,
        "cadete_id": cadete_id,
        "task_id": "cadet_routine",
        "corridas": [],
        "propuesto": {"Content": 3, "Organization": 3, "Language": 3},
        "final": {"Content": 3, "Organization": final_organization, "Language": 3},
        "razones": {},
        "debilidades": debilidades,
        "accion": "revision_rapida",
        "modelo": "test",
        "version_prompt": "test",
    }


def test_guardar_y_recuperar_historial():
    guardar_evaluacion(evaluacion_de_prueba("CDT-001", "2026-10-01", ["below_length"]))
    historial = obtener_historial("CDT-001")
    assert len(historial) == 1
    assert historial[0]["debilidades"] == ["below_length"]
    assert historial[0]["ajustado"] is False


def test_historial_ordenado_y_ajuste_detectado():
    guardar_evaluacion(evaluacion_de_prueba("CDT-002", "2026-09-01", []))
    guardar_evaluacion(evaluacion_de_prueba("CDT-002", "2026-10-01", [], final_organization=3.5))
    historial = obtener_historial("CDT-002")
    assert historial[0]["fecha"] == "2026-10-01"     # la más reciente primero
    assert historial[0]["ajustado"] is True          # el profesor cambió Organization


def test_cadete_sin_historial():
    assert consultar_historial.invoke({"cadete_id": "CDT-999"}) == []