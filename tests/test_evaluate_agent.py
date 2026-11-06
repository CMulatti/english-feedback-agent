"""Tests de las funciones auxiliares de la evaluación (sin llamar al modelo)."""

from scripts.evaluate_agent import leer_puntajes_originales, distancia


def test_leer_puntajes_con_rango():
    puntajes = leer_puntajes_originales("Content 3 | Organization 4 | Language 2.5 or 3")
    assert puntajes["Content"] == (3, 3)
    assert puntajes["Language"] == (2.5, 3)


def test_distancia_dentro_y_fuera_del_rango():
    assert distancia(2.5, (2.5, 3)) == 0
    assert distancia(2, (2.5, 3)) == -0.5
    assert distancia(4, (3, 3)) == 1