"""
Planner: decide qué hacer con un texto, según las reglas de docs/reglas.md.

El planner responde dos preguntas distintas:
- ¿Cómo debe revisar el profesor este texto? Una sola acción, según 5 reglas en orden
  de prioridad: se detiene en la primera que se cumple (cada regla termina en return).
- ¿Qué necesita este cadete? Recomendaciones (cero o más) que se muestran siempre,
  sin competir con la acción: por ejemplo, reforzar una debilidad recurrente.

Funciones:
- construir_estado(): el "traductor". Toma lo que devuelven las tools y arma el estado,
  un diccionario simple con los hechos que necesitan las reglas.
- revisar_antes_de_evaluar(): reglas 1 y 2, que no necesitan al LLM.
- decidir_accion(): las 5 reglas de revisión.
- recomendar(): las recomendaciones para el cadete.

Son funciones puras: no llaman al LLM ni a la base de datos. Con los mismos datos,
siempre dan el mismo resultado (son deterministas), por eso son fáciles de probar.
"""

from dataclasses import dataclass

from config import settings


@dataclass
class Accion:
    """@dataclass crea automáticamente el constructor de una clase que solo guarda datos."""
    tipo: str        # la acción: escalar_profesor, caso_dudoso, ...
    motivo: str      # código fijo, para contar en la Etapa 3
    razon: str       # explicación para el profesor (en inglés)


# ---------- Estado ----------

def contar_recurrencias(debilidades_actuales, historial):
    """Cuántas veces aparece cada debilidad actual, contando el texto actual."""
    conteo = {}
    for debilidad in debilidades_actuales:
        anteriores = sum(1 for evaluacion in historial if debilidad in evaluacion["debilidades"])
        conteo[debilidad] = anteriores + 1
    return conteo


def construir_estado(revision, evaluacion=None, historial=None):
    """
    Arma el estado que consume el planner.
    revision viene de revisar_texto, evaluacion de evaluar_texto y historial de consultar_historial.
    Antes de evaluar, evaluacion es None: solo se pueden aplicar las reglas 1 y 2.
    """
    conteo = contar_recurrencias(revision["debilidades"], historial or [])
    estado = {
        "porcentaje_minimo": revision["porcentaje_minimo"],
        "es_ingles": revision["es_ingles"],
        "instrucciones_sospechosas": revision["instrucciones_sospechosas"],
        "debilidades_recurrentes": {d: n for d, n in conteo.items()
                                    if n >= settings.UMBRAL_RECURRENCIA},
    }
    if evaluacion:
        estado.update({
            "criterios_en_desacuerdo": evaluacion["criterios_en_desacuerdo"],
            "rango": evaluacion["rango"],
            "corridas_validas": evaluacion["corridas_validas"],
            "total": sum(evaluacion["mediana"].values()),
        })
    return estado


# ---------- Reglas ----------

def revisar_antes_de_evaluar(estado):
    """Reglas 1 y 2. Devuelve una Accion si el texto no debe evaluarse, o None si puede evaluarse."""
    # Regla 1: sin contenido suficiente para evaluar
    if estado["porcentaje_minimo"] < settings.UMBRAL_TEXTO_MINIMO:
        return Accion("escalar_profesor", "texto_insuficiente",
                      f"The text has {int(estado['porcentaje_minimo'] * 100)}% of the minimum "
                      f"length: there is not enough content to assess.")

    # Regla 2: no está en inglés, o intenta manipular la evaluación
    if not estado["es_ingles"]:
        return Accion("escalar_profesor", "idioma",
                      "Most of the text is not in English.")
    if estado["instrucciones_sospechosas"]:
        return Accion("escalar_profesor", "instrucciones_sospechosas",
                      "The text contains instructions aimed at the assessment system.")
    return None


def decidir_accion(estado):
    """Aplica las 5 reglas de revisión en orden de prioridad. Necesita el estado completo."""
    # Reglas 1 y 2
    accion = revisar_antes_de_evaluar(estado)
    if accion:
        return accion

    # Regla 3: las corridas no coinciden (1 banda o más), o hubo muy pocas corridas válidas
    if estado["corridas_validas"] < settings.MIN_CORRIDAS_VALIDAS:
        return Accion("caso_dudoso", "pocas_corridas",
                      f"Only {estado['corridas_validas']} valid assessment run(s): "
                      f"consistency cannot be measured.")
    if estado["criterios_en_desacuerdo"]:
        detalle = ", ".join(f"{c} (runs differ by {estado['rango'][c]} bands)"
                            for c in estado["criterios_en_desacuerdo"])
        return Accion("caso_dudoso", "desacuerdo",
                      f"The assessment runs disagree on: {detalle}.")

    # Regla 4: puntaje total bajo
    if estado["total"] < settings.UMBRAL_PUNTAJE_BAJO:
        return Accion("priorizar_revision", "puntaje_bajo",
                      f"Total score {estado['total']} is below {settings.UMBRAL_PUNTAJE_BAJO} out of 15.")

    # Regla 5: caso estándar
    return Accion("revision_rapida", "estandar", "Standard case within the criteria.")


# ---------- Recomendaciones ----------

def recomendar(estado):
    """
    Recomendaciones para el cadete. No compiten con la acción de revisión:
    se muestran siempre, cualquiera sea la acción.
    Hoy hay una: reforzar una debilidad que aparece por tercera vez (o más).
    """
    return [
        {"tipo": "recomendar_refuerzo", "debilidad": debilidad, "veces": veces,
         "razon": f"Recurring weakness: {debilidad} ({veces} times, including this text)."}
        for debilidad, veces in estado["debilidades_recurrentes"].items()
    ]