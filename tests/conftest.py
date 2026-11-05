"""
conftest.py: pytest lo carga automáticamente antes de los tests.

El fixture base_temporal se aplica a todos los tests (autouse=True):
- apunta la base SQLite y la carpeta de Chroma a una carpeta temporal,
  para que los tests nunca escriban en la memoria ni en el registro reales;
- quita las esperas entre reintentos;
- reemplaza el modelo de embeddings por uno falso, rápido y sin descargas.
"""

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from config import settings
from agent.memory import semantic


@pytest.fixture(autouse=True)
def base_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(settings, "CHROMA_DIR", tmp_path / "chroma")
    monkeypatch.setattr(settings, "ESPERA_REINTENTO", 0)
    monkeypatch.setattr(semantic, "obtener_embeddings", lambda: DeterministicFakeEmbedding(size=64))