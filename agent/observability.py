"""
Registro de ejecución (observabilidad, preparado para la Etapa 3).

Se guarda en su propia base de datos (data/eventos.db), separada de la memoria del agente:
así, reiniciar las memorias para una demo o una evaluación no borra el registro.

Cada llamada a una tool o al LLM guarda una fila en la tabla 'eventos':
cuándo ocurrió, qué se ejecutó, cuánto tardó, cuántos tokens usó y si hubo un error.

Todo pasa por dos piezas:
- registrar_evento(): guarda una fila.
- @registrar_tool: decorador que mide y registra una tool automáticamente.
"""

import functools
import sqlite3
import time
import uuid
from datetime import datetime

from config import settings

# Identificador de la sesión actual, para agrupar los eventos de una misma sesión
SESION_ID = uuid.uuid4().hex[:8]


def crear_tabla_eventos():
    with sqlite3.connect(settings.EVENTOS_DB_PATH) as conexion:
        conexion.execute("""
            CREATE TABLE IF NOT EXISTS eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_hora TEXT NOT NULL,
                sesion_id TEXT,
                componente TEXT,
                nombre TEXT,
                modelo TEXT,
                duracion_ms INTEGER,
                tokens_entrada INTEGER,
                tokens_salida INTEGER,
                resultado TEXT,
                tipo_error TEXT,
                detalle TEXT
            )
        """)


def registrar_evento(componente, nombre, resultado, duracion_ms=None, modelo=None,
                     tokens_entrada=None, tokens_salida=None, tipo_error=None, detalle=None):
    """Guarda un evento. componente es 'tool' o 'llm'; resultado es 'ok' o 'error'."""
    crear_tabla_eventos()
    with sqlite3.connect(settings.EVENTOS_DB_PATH) as conexion:
        conexion.execute("""
            INSERT INTO eventos (fecha_hora, sesion_id, componente, nombre, modelo, duracion_ms,
                                 tokens_entrada, tokens_salida, resultado, tipo_error, detalle)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(timespec="seconds"), SESION_ID, componente, nombre,
              modelo, duracion_ms, tokens_entrada, tokens_salida, resultado, tipo_error,
              (detalle or "")[:300]))


def obtener_eventos(limite=20):
    """Devuelve los últimos eventos registrados (para revisar o probar)."""
    crear_tabla_eventos()
    with sqlite3.connect(settings.EVENTOS_DB_PATH) as conexion:
        conexion.row_factory = sqlite3.Row
        filas = conexion.execute(
            "SELECT * FROM eventos ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
    return [dict(fila) for fila in filas]


def registrar_tool(funcion):
    """
    Decorador: mide cuánto tarda una tool y registra si terminó bien o con error.
    Se escribe justo debajo de @tool. functools.wraps conserva el nombre y el
    docstring de la función, que LangChain necesita para describir la tool al LLM.
    """
    @functools.wraps(funcion)
    def envoltura(*args, **kwargs):
        inicio = time.time()
        try:
            resultado = funcion(*args, **kwargs)
        except Exception as error:
            registrar_evento("tool", funcion.__name__, "error",
                             duracion_ms=int((time.time() - inicio) * 1000),
                             tipo_error="exception", detalle=str(error))
            raise
        estado = "error" if isinstance(resultado, dict) and "error" in resultado else "ok"
        registrar_evento("tool", funcion.__name__, estado,
                         duracion_ms=int((time.time() - inicio) * 1000),
                         tipo_error="tool_error" if estado == "error" else None)
        return resultado
    return envoltura