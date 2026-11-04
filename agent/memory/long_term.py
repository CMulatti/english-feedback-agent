"""
Memoria de largo plazo: evaluaciones confirmadas, guardadas en SQLite.

SQLite es una base de datos completa guardada en un solo archivo (data/agent.db).
Las listas y diccionarios (corridas, puntajes, razones, debilidades) se guardan
como texto JSON, porque SQLite no tiene columnas de tipo lista.

Este módulo no usa el LLM: solo guarda y recupera.
"""

import json
import sqlite3

from config import settings

CRITERIOS = ["Content", "Organization", "Language"]


def conectar():
    """Abre la base de datos. row_factory permite leer las filas por nombre de columna."""
    conexion = sqlite3.connect(settings.DB_PATH)
    conexion.row_factory = sqlite3.Row
    return conexion


def crear_tablas():
    """Crea la tabla de evaluaciones si no existe."""
    with conectar() as conexion:
        conexion.execute("""
            CREATE TABLE IF NOT EXISTS evaluaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                cadete_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                corridas TEXT,
                propuesto TEXT,
                final TEXT,
                razones TEXT,
                debilidades TEXT,
                accion TEXT,
                modelo TEXT,
                version_prompt TEXT
            )
        """)


def guardar_evaluacion(evaluacion):
    """
    Guarda una evaluación confirmada y devuelve su id.
    Los campos corridas, propuesto, final, razones y debilidades pueden venir
    como listas o diccionarios: se convierten a JSON aquí.
    """
    datos = dict(evaluacion)
    for campo in ("corridas", "propuesto", "final", "razones", "debilidades"):
        if not isinstance(datos.get(campo), str):
            datos[campo] = json.dumps(datos.get(campo))

    crear_tablas()
    with conectar() as conexion:
        cursor = conexion.execute("""
            INSERT INTO evaluaciones
                (fecha, cadete_id, task_id, corridas, propuesto, final,
                 razones, debilidades, accion, modelo, version_prompt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (datos["fecha"], datos["cadete_id"], datos["task_id"], datos["corridas"],
              datos["propuesto"], datos["final"], datos["razones"], datos["debilidades"],
              datos["accion"], datos["modelo"], datos["version_prompt"]))
        return cursor.lastrowid


def obtener_historial(cadete_id, limite=10):
    """Devuelve las evaluaciones del cadete, de la más reciente a la más antigua."""
    crear_tablas()
    with conectar() as conexion:
        filas = conexion.execute("""
            SELECT * FROM evaluaciones
            WHERE cadete_id = ?
            ORDER BY fecha DESC, id DESC
            LIMIT ?
        """, (cadete_id, limite)).fetchall()

    historial = []
    for fila in filas:
        propuesto = json.loads(fila["propuesto"])
        final = json.loads(fila["final"])
        historial.append({
            "fecha": fila["fecha"],
            "task_id": fila["task_id"],
            "puntajes_finales": final,
            "debilidades": json.loads(fila["debilidades"]),
            "accion": fila["accion"],
            "ajustado": any(final[c] != propuesto[c] for c in CRITERIOS),
        })
    return historial

