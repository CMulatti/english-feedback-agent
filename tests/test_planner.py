"""
Tests del planner: una prueba por regla, pruebas de prioridad y recomendaciones.
No usan el LLM ni la base de datos: el planner es una función pura.
"""

from agent.planner import decidir_accion, revisar_antes_de_evaluar, construir_estado, recomendar


def estado(**cambios):
    """Estado de un caso estándar; cada test cambia solo lo que necesita."""
    base = {
        "porcentaje_minimo": 1.0,
        "es_ingles": True,
        "instrucciones_sospechosas": False,
        "debilidades_recurrentes": {},
        "criterios_en_desacuerdo": [],
        "rango": {"Content": 0, "Organization": 0, "Language": 0},
        "corridas_validas": 3,
        "total": 10,
    }
    base.update(cambios)
    return base


# ---------- Una prueba por regla ----------

def test_regla_1_texto_insuficiente():
    accion = decidir_accion(estado(porcentaje_minimo=0.1))
    assert (accion.tipo, accion.motivo) == ("escalar_profesor", "texto_insuficiente")


def test_regla_2_idioma():
    accion = decidir_accion(estado(es_ingles=False))
    assert (accion.tipo, accion.motivo) == ("escalar_profesor", "idioma")


def test_regla_2_instrucciones_sospechosas():
    accion = decidir_accion(estado(instrucciones_sospechosas=True))
    assert accion.motivo == "instrucciones_sospechosas"


def test_regla_3_desacuerdo():
    accion = decidir_accion(estado(criterios_en_desacuerdo=["Language"],
                                   rango={"Content": 0, "Organization": 0, "Language": 2}))
    assert accion.tipo == "caso_dudoso"
    assert "Language" in accion.razon


def test_regla_3_pocas_corridas():
    accion = decidir_accion(estado(corridas_validas=1))
    assert (accion.tipo, accion.motivo) == ("caso_dudoso", "pocas_corridas")


def test_regla_3_diferencia_de_media_banda_no_es_desacuerdo():
    # El desacuerdo lo calcula evaluar_texto; aquí basta con que no venga marcado
    accion = decidir_accion(estado(rango={"Content": 0.5, "Organization": 0, "Language": 0}))
    assert accion.tipo == "revision_rapida"


def test_regla_4_puntaje_bajo():
    accion = decidir_accion(estado(total=8.5))
    assert accion.tipo == "priorizar_revision"


def test_regla_5_estandar():
    assert decidir_accion(estado()).tipo == "revision_rapida"


# ---------- Prioridad ----------

def test_desacuerdo_antes_que_puntaje_bajo():
    accion = decidir_accion(estado(criterios_en_desacuerdo=["Content"], total=7))
    assert accion.tipo == "caso_dudoso"


def test_texto_insuficiente_antes_que_idioma():
    accion = decidir_accion(estado(porcentaje_minimo=0.1, es_ingles=False))
    assert accion.motivo == "texto_insuficiente"


def test_debilidad_recurrente_no_cambia_la_accion():
    accion = decidir_accion(estado(debilidades_recurrentes={"missing_greeting": 3}))
    assert accion.tipo == "revision_rapida"


# ---------- Recomendaciones ----------

def test_recomendacion_de_refuerzo():
    recomendaciones = recomendar(estado(debilidades_recurrentes={"missing_greeting": 3}))
    assert recomendaciones[0]["tipo"] == "recomendar_refuerzo"
    assert recomendaciones[0]["debilidad"] == "missing_greeting"


def test_sin_recomendaciones():
    assert recomendar(estado()) == []


# ---------- Antes de evaluar y construcción del estado ----------

def test_texto_normal_se_puede_evaluar():
    assert revisar_antes_de_evaluar(estado()) is None


def test_construir_estado_cuenta_recurrencias():
    revision = {"porcentaje_minimo": 0.9, "es_ingles": True, "instrucciones_sospechosas": False,
                "debilidades": ["missing_greeting", "below_length"]}
    historial = [{"debilidades": ["missing_greeting"]},
                 {"debilidades": ["missing_greeting", "below_length"]}]
    evaluacion = {"criterios_en_desacuerdo": [], "rango": {}, "corridas_validas": 3,
                  "mediana": {"Content": 3, "Organization": 2.5, "Language": 3}}
    resultado = construir_estado(revision, evaluacion, historial)
    assert resultado["debilidades_recurrentes"] == {"missing_greeting": 3}   # below_length: solo 2
    assert resultado["total"] == 8.5