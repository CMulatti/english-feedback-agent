"""
Carga data/historial.csv en la base de datos SQLite (data/agent.db).
Borra la base anterior, para empezar siempre desde los mismos datos.

Ejecutar desde la carpeta principal: python -m scripts.seed_data
"""

import csv

from config.settings import DATA_DIR, DB_PATH
from agent.memory.long_term import crear_tablas, guardar_evaluacion

if __name__ == "__main__":
    if DB_PATH.exists():
        DB_PATH.unlink()

    crear_tablas()
    with open(DATA_DIR / "historial.csv", encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))

    for fila in filas:
        guardar_evaluacion(fila)

    print(f"Cargadas {len(filas)} evaluaciones en {DB_PATH.name}.")

    