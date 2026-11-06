"""
retrieval.py

Recupera desde la base de conocimiento (la carpeta data/) la información
necesaria para evaluar el texto de un estudiante en una tarea específica.

- Siempre se incluye: la rúbrica de Cambridge y los criterios institucionales.
- Se recupera según la tarea: la task sheet, su vocabulario adicional (si tiene)
  y las muestras de referencia (benchmarks) de esa tarea.
"""

from config.settings import DATA_DIR


def read_file(path):
    """Lee un archivo de texto y devuelve su contenido como string."""
    return path.read_text(encoding="utf-8")


def get_field(text, field_name):
    """
    Busca una línea como 'Task: cadet_routine' y devuelve el valor después de ':'.
    Devuelve None si no encuentra el campo.
    """
    for line in text.splitlines():
        if line.startswith(field_name + ":"):
            return line.split(":", 1)[1].strip()
    return None


def load_rubric():
    """La rúbrica oficial de Cambridge (se usa en todas las tareas)."""
    return read_file(DATA_DIR / "rubric_cambridge_a2.md")


def load_criteria():
    """Los criterios institucionales (se usan en todas las tareas)."""
    return read_file(DATA_DIR / "criteria.md")


def list_tasks():
    """Devuelve los ids de todas las tareas disponibles, según los archivos de data/tasks/."""
    tasks = []
    for path in sorted((DATA_DIR / "tasks").glob("*.md")):
        tasks.append(path.stem)
    return tasks


def load_task(task_id):
    """Carga la task sheet de una tarea."""
    path = DATA_DIR / "tasks" / f"{task_id}.md"
    if not path.exists():
        raise FileNotFoundError(f"No se encontró la tarea '{task_id}': {path}")
    return read_file(path)


def load_extra_vocabulary(task_text):
    """
    Si la task sheet tiene una línea como 'Extra vocabulary: military.md',
    carga ese archivo desde data/vocabulary/. Si no, devuelve un string vacío.
    """
    file_name = get_field(task_text, "Extra vocabulary")
    if file_name is None:
        return ""
    return read_file(DATA_DIR / "vocabulary" / file_name)


def load_samples(task_id):
    """Carga solo las muestras de referencia cuya línea 'Task:' coincide con esta tarea."""
    samples = []
    for path in sorted((DATA_DIR / "samples").glob("*.md")):
        text = read_file(path)
        if get_field(text, "Task") == task_id:
            samples.append(text)
    return samples


def retrieve_context(task_id):
    """Reúne todo lo que el LLM necesita para evaluar un texto de esta tarea."""
    task = load_task(task_id)
    return {
        "rubric": load_rubric(),
        "criteria": load_criteria(),
        "task": task,
        "vocabulary": load_extra_vocabulary(task),
        "samples": load_samples(task_id),
    }


# Prueba rápida: ejecuta "python retrieval.py" en la terminal
if __name__ == "__main__":
    print("Tareas disponibles:", list_tasks())

    for task_id in list_tasks():
        context = retrieve_context(task_id)
        print(f"\n=== {task_id} ===")
        print("Muestras de referencia encontradas:", len(context["samples"]))
        print("Vocabulario adicional cargado:", "sí" if context["vocabulary"] else "no")
        for sample in context["samples"]:
            print("  -", get_field(sample, "Scores"))