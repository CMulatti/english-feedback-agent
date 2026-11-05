"""
settings.py

Configuración central del agente: rutas y umbrales.
Los números que usan varias partes del código viven aquí, para cambiarlos en un solo lugar.
"""

from pathlib import Path

# ---------- Rutas ----------
# settings.py está en config/, así que la raíz del proyecto es dos niveles arriba
BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
TASKS_DIR = DATA_DIR / "tasks"
VOCABULARY_DIR = DATA_DIR / "vocabulary"
SAMPLES_DIR = DATA_DIR / "samples"
DB_PATH = DATA_DIR / "agent.db"          # memoria de largo plazo (SQLite)
CHROMA_DIR = DATA_DIR / "chroma_db"      # memoria semántica (Chroma)

# ---------- Evaluación ----------
N_EVALUACIONES = 3        # corridas por texto
VERSION_PROMPT = "v1"     # se guarda con cada evaluación (Etapa 3)

# ---------- Reglas del planner (ver docs/reglas.md) ----------
UMBRAL_TEXTO_MINIMO = 0.2     # regla 1: proporción del mínimo de palabras
UMBRAL_IDIOMA = 0.3           # regla 2: proporción de palabras en español
UMBRAL_DESACUERDO = 0.5       # regla 3: diferencia máxima entre corridas (bandas)
UMBRAL_RECURRENCIA = 3        # regla 4: veces, contando el texto actual
UMBRAL_PUNTAJE_BAJO = 9       # regla 5: total sobre 15
MIN_PALABRAS_ESPANOL = 2      # debilidad spanish_words

# ---------- LLM ----------
MAX_REINTENTOS = 3        # intentos por llamada al LLM si el modelo está saturado
ESPERA_REINTENTO = 10     # segundos de espera entre intentos