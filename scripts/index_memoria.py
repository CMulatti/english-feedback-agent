"""
Construye la memoria semántica (Chroma) desde cero:
- criterios: secciones de criteria.md y de la rúbrica.
- casos: casos ficticios de data/casos_previos.json.

La primera vez descarga el modelo de embeddings (~80 MB).
Ejecutar desde la carpeta principal: python -m scripts.index_memoria
"""

from agent.memory.semantic import indexar_criterios, indexar_casos_previos

if __name__ == "__main__":
    print(f"Indexados {indexar_criterios()} fragmentos de criterios.")
    print(f"Indexados {indexar_casos_previos()} casos previos.")