"""
conftest.py: pytest lo carga automáticamente antes de los tests.

El fixture base_temporal se aplica a todos los tests (autouse=True):
apunta DB_PATH a una base nueva en una carpeta temporal, para que los
tests nunca escriban en el historial ni en el registro de eventos reales.
"""

import pytest

from config import settings


@pytest.fixture(autouse=True)
def base_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(settings, "ESPERA_REINTENTO", 0)   # sin esperas en los tests