"""
Genera datos ficticios para probar la memoria de largo plazo:

- data/cadetes.csv: cadetes con códigos anónimos (CDT-001, CDT-002, ...).
- data/historial.csv: evaluaciones anteriores ya confirmadas por un profesor.

random.seed(42) hace que cada ejecución genere exactamente los mismos datos,
para que las pruebas y la demo sean repetibles.

Ejecutar desde la carpeta principal: python -m scripts.generate_mock_data
"""

import csv
import json
import random
from datetime import date, timedelta

from config.settings import DATA_DIR

random.seed(42)

# Tareas anteriores ficticias (unidades previas del curso).
# La segunda columna indica si la tarea requería saludo.
TAREAS_PREVIAS = {
    "A2": [("weekend_email", True), ("invitation_email", True), ("family_description", False)],
    "A2+": [("past_vacation", False), ("city_description", False)],
}

PUNTAJES = [2, 2.5, 3, 3, 3.5, 3.5, 4, 4.5, 5]
RAZONES_AJUSTE = [
    "Greeting present but informal; accepted as valid",
    "Taught vocabulary used correctly, deserves more credit",
    "Frequent errors with the target grammar",
    "Content point answered implicitly",
]
FECHA_INICIAL = date(2026, 9, 1)

CRITERIOS = ["Content", "Organization", "Language"]


def crear_cadetes():
    """12 cadetes: 8 de primer año (A2) y 4 de segundo año (A2+)."""
    cadetes = []
    for numero in range(1, 13):
        nivel = "A2" if numero <= 8 else "A2+"
        cadetes.append({"cadete_id": f"CDT-{numero:03d}", "nivel": nivel})
    return cadetes


def crear_evaluacion(cadete_id, task_id, requiere_saludo, fecha,
                     debilidades=None, propuesto=None):
    """Crea una evaluación confirmada ficticia, con sus 3 corridas y el puntaje final."""
    if propuesto is None:
        propuesto = {c: random.choice(PUNTAJES) for c in CRITERIOS}

    # 3 corridas: una igual o menor, una igual y una igual o mayor que el propuesto,
    # para que la mediana sea exactamente el puntaje propuesto
    corridas = [
        {c: max(0, propuesto[c] - random.choice([0, 0.5])) for c in CRITERIOS},
        dict(propuesto),
        {c: min(5, propuesto[c] + random.choice([0, 0.5])) for c in CRITERIOS},
    ]

    # En 1 de cada 4 evaluaciones, el profesor ajusta un criterio
    final = dict(propuesto)
    razones = {}
    if random.random() < 0.25:
        criterio = random.choice(CRITERIOS)
        final[criterio] = max(0, min(5, propuesto[criterio] + random.choice([-0.5, 0.5])))
        razones[criterio] = random.choice(RAZONES_AJUSTE)

    if debilidades is None:
        debilidades = []
        if requiere_saludo and random.random() < 0.2:
            debilidades.append("missing_greeting")
        if random.random() < 0.25:
            debilidades.append("below_length")
        if random.random() < 0.15:
            debilidades.append("spanish_words")

    return {
        "fecha": fecha.isoformat(),
        "cadete_id": cadete_id,
        "task_id": task_id,
        "corridas": json.dumps(corridas),
        "propuesto": json.dumps(propuesto),
        "final": json.dumps(final),
        "razones": json.dumps(razones),
        "debilidades": json.dumps(debilidades),
        "accion": "revision_rapida",
        "modelo": "mock",
        "version_prompt": "mock",
    }


def crear_historial(cadetes):
    historial = []
    for cadete in cadetes:
        cadete_id = cadete["cadete_id"]

        #Caso especial para la demo: CDT-004 ya omitió el saludo dos veces
        if cadete_id == "CDT-004":
            historial.append(crear_evaluacion(
                cadete_id, "weekend_email", True, FECHA_INICIAL, ["missing_greeting"],
                {"Content": 3, "Organization": 2.5, "Language": 3}))
            historial.append(crear_evaluacion(
                cadete_id, "invitation_email", True, FECHA_INICIAL + timedelta(days=21),
                ["missing_greeting", "below_length"],
                {"Content": 2.5, "Organization": 2.5, "Language": 3}))
            continue

        #CDT-008 y CDT-012 no tienen historial: así se prueba el caso "sin evaluaciones previas"
        if cadete_id in ("CDT-008", "CDT-012"):
            continue

        tareas = TAREAS_PREVIAS[cadete["nivel"]]
        for indice, (task_id, requiere_saludo) in enumerate(random.sample(tareas, random.randint(1, 2))):
            fecha = FECHA_INICIAL + timedelta(days=21 * indice + random.randint(0, 3))
            historial.append(crear_evaluacion(cadete_id, task_id, requiere_saludo, fecha))
    return historial


def guardar_csv(ruta, filas):
    with open(ruta, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=filas[0].keys())
        escritor.writeheader()
        escritor.writerows(filas)


if __name__ == "__main__":
    cadetes = crear_cadetes()
    historial = crear_historial(cadetes)
    guardar_csv(DATA_DIR / "cadetes.csv", cadetes)
    guardar_csv(DATA_DIR / "historial.csv", historial)
    print(f"Generados {len(cadetes)} cadetes y {len(historial)} evaluaciones anteriores.")