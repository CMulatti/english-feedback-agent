
"""
checks.py

Revisiones automáticas que no necesitan un LLM. Producen hechos objetivos
que el LLM recibirá como evidencia:

- Conteo de palabras y comparación con la extensión esperada de la tarea.
- Vocabulario enseñado que aparece en el texto del estudiante.
"""

from agent.rag.retrieval import get_field, load_task, load_extra_vocabulary


# ---------- Funciones auxiliares ----------

def get_section(text, title):
    """
    Devuelve las líneas de una sección Markdown, por ejemplo '## Taught vocabulary',
    hasta el siguiente título '## '.
    """
    lines = []
    inside = False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = (line == "## " + title)
            continue
        if inside:
            lines.append(line)
    return lines


def normalize(text):
    """
    Pasa el texto a minúsculas y reemplaza la puntuación por espacios,
    para que 'Mess Hall,' y 'mess hall' se traten igual.
    Agrega un espacio al inicio y al final para encontrar solo palabras completas.
    """
    clean = ""
    for char in text.lower():
        if char.isalnum():
            clean += char
        else:
            clean += " "
    return " " + " ".join(clean.split()) + " "


def split_items(text):
    """
    Separa una línea como 'wake up, brush my teeth, plebe (first-year cadet)'
    en términos individuales, eliminando lo que está entre paréntesis.
    """
    items = []
    for item in text.split(","):
        item = item.split("(")[0].strip()
        if item:
            items.append(item)
    return items


# ---------- Extensión ----------

def count_words(text):
    """Cuenta las palabras de un texto."""
    return len(text.split())


def check_length(text, task_text):
    """Compara el número de palabras con la extensión esperada de la tarea."""
    words = count_words(text)
    minimum = int(get_field(task_text, "Minimum words"))
    maximum = int(get_field(task_text, "Maximum words"))
    threshold = round(minimum * 0.8)

    if words < threshold:
        status = f"bajo el 80% del mínimo ({threshold} palabras)"
    elif words < minimum:
        status = f"bajo el mínimo, pero igual o sobre el 80% ({threshold} palabras)"
    elif words <= maximum:
        status = "dentro de la extensión esperada"
    else:
        status = "sobre el máximo"

    return {
        "words": words,
        "minimum": minimum,
        "maximum": maximum,
        "threshold": threshold,
        "status": status,
    }


# ---------- Vocabulario enseñado ----------

def get_task_vocabulary(task_text):
    """
    Lee la sección '## Taught vocabulary' de una task sheet.
    En las task sheets, lo que está antes de ':' es una categoría (ej. 'Places'),
    así que solo se usa lo que está después de ':'.
    """
    vocabulary = []
    for line in get_section(task_text, "Taught vocabulary"):
        line = line.strip()
        if line.startswith("- "):
            line = line[2:]
        if ":" in line:
            line = line.split(":", 1)[1]
        vocabulary += split_items(line)
    return vocabulary


def get_file_vocabulary(vocabulary_text):
    """
    Lee un archivo de vocabulario como military.md.
    Aquí lo que está antes de ':' también es un término (ej. 'cadet: CDT'),
    así que se usan ambos lados.
    """
    vocabulary = []
    for line in vocabulary_text.splitlines():
        if line.startswith("- "):
            line = line[2:].replace(":", ",")
            vocabulary += split_items(line)
    return vocabulary


def find_taught_vocabulary(text, task_text, vocabulary_text=""):
    """Devuelve los términos enseñados que aparecen en el texto del estudiante."""
    vocabulary = get_task_vocabulary(task_text) + get_file_vocabulary(vocabulary_text)
    clean_text = normalize(text)

    found = []
    for term in vocabulary:
        if normalize(term) in clean_text and term.lower() not in found:
            found.append(term.lower())
    return found


# ---------- Todas las revisiones juntas ----------

def run_checks(text, task_id):
    """Ejecuta todas las revisiones automáticas para el texto de un estudiante."""
    task_text = load_task(task_id)
    vocabulary_text = load_extra_vocabulary(task_text)
    return {
        "length": check_length(text, task_text),
        "taught_vocabulary": find_taught_vocabulary(text, task_text, vocabulary_text),
    }


# Prueba rápida: ejecuta "python checks.py" en la terminal
if __name__ == "__main__":
    test_text = (
        "get up at 5:45 A.M. a take shower, get dressed, after that form up in "
        "the alpatacal cordid and go to the mess hall where the cadet have a "
        "breakfast. After I go to classroom where have classes at 8.00. Then, "
        "form up at 1.00 for mess hall to have lunch with the company. Then do "
        "sports or classes from 15.00 to 18.00. In the night, go to barracks "
        "and sleep."
    )

    results = run_checks(test_text, "cadet_routine")
    length = results["length"]

    print("Palabras:", length["words"])
    print("Esperado:", length["minimum"], "-", length["maximum"])
    print("Estado:", length["status"])
    print("Vocabulario enseñado encontrado:", results["taught_vocabulary"])