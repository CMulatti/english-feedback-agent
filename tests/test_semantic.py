"""
Tests de la memoria semántica.

Usan embeddings falsos (ver conftest.py): prueban que se guarda, se filtra y se
recupera correctamente, pero no la calidad de la búsqueda por significado.
Esa calidad se comprueba con el modelo real: python -m agent.tools.buscar_contexto
"""

from agent.memory.semantic import (indexar_criterios, indexar_casos_previos, resumir_caso,
                                   buscar_casos, dividir_en_secciones)
from agent.tools.buscar_contexto import buscar_contexto

CASO = {
    "task_id": "cadet_routine",
    "texto": "Hi Jim, I wake up at 6.",
    "propuesto": {"Content": 3, "Organization": 2.5, "Language": 3},
    "final": {"Content": 3, "Organization": 3, "Language": 3},
    "razones": {"Organization": "Informal greeting is valid"},
    "debilidades": ["below_length"],
}


def test_resumen_del_caso():
    resumen = resumir_caso(CASO)
    assert resumen.startswith("cadet_routine")
    assert "Organization: system 2.5 -> teacher 3" in resumen
    assert "Weaknesses: below_length" in resumen


def test_resumen_sin_ajustes():
    resumen = resumir_caso({**CASO, "razones": {}})
    assert "Teacher confirmed the proposed scores" in resumen


def test_dividir_en_secciones():
    fragmentos = dividir_en_secciones("# Title\n## Scale\nA\n## Format\nB", "criteria.md")
    assert [f.metadata["referencia"] for f in fragmentos] == ["Scale", "Format"]


def test_indexar_y_buscar_criterios():
    assert indexar_criterios() > 0
    resultados = buscar_contexto.invoke({"consulta": "greeting"})
    assert any(r["fuente"] == "criteria.md" for r in resultados)


def test_casos_filtrados_por_tarea():
    indexar_casos_previos()
    resultados = buscar_casos("beaches and tourists", task_id="santiago_tourism", k=5)
    assert len(resultados) == 1                      # solo hay un caso de Santiago
    assert resultados[0]["contenido"].startswith("santiago_tourism")


def test_solo_casos_ajustados():
    indexar_casos_previos()
    resultados = buscar_casos("routine", task_id="cadet_routine", solo_ajustados=True, k=5)
    assert len(resultados) == 3
    assert all("teacher" in r["contenido"] for r in resultados)