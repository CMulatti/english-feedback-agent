# Contratos de las tools

Cada tool tiene un contrato: qué recibe y qué devuelve. Si se respeta el contrato, el interior de una tool puede cambiar sin afectar al resto del agente.

Todas las tools registran su ejecución en el registro de eventos (hora, duración, resultado y tipo de error), para la Etapa 3.

## Resumen

| # | Tool | Entrada | Salida | Se usa en |
|---|---|---|---|---|
| 1 | `consultar_tarea` | `task_id` | Ficha de la tarea | Siempre |
| 2 | `revisar_texto` | `texto`, `task_id` | Hechos objetivos y debilidades | Reglas 1, 2 y 4 |
| 3 | `evaluar_texto` | `texto`, `task_id`, `revision`, `casos_similares` | Puntajes de cada corrida, mediana y desacuerdos | Reglas 3 y 5 |
| 4 | `consultar_historial` | `cadete_id` | Evaluaciones anteriores | Regla 4 |
| 5 | `buscar_contexto` | `consulta`, `task_id` (opcional) | Fragmentos de criterios y casos similares | RAG semántico y chat |
| 6 | `guardar_evaluacion` | Datos de la evaluación confirmada | Confirmación | Después de confirmar |
| 7 | `generar_retroalimentacion` | `texto`, `task_id`, evaluación final | Retroalimentación en español | Después de confirmar |

## Detalle

### 1. `consultar_tarea`
- **Entrada:** `task_id: str`
- **Salida:** `dict` con `task_id`, `nivel`, `instrucciones`, `min_palabras`, `max_palabras`, `requiere_saludo` (bool), `puntos_contenido` (lista con texto y tipo essential/accessory), `gramatica_objetivo` y `vocabulario` (lista).
- **Error:** `{"error": "Tarea no encontrada"}`
- **Nota:** las fichas necesitan una línea nueva, `Requires greeting: yes/no`, para que el código lo lea sin interpretar texto.

### 2. `revisar_texto`
- **Entrada:** `texto: str`, `task_id: str`
- **Salida:** `dict` con:
  - `palabras`, `min_palabras`, `porcentaje_minimo`, `estado_extension`
  - `vocabulario_encontrado` (lista)
  - `tiene_saludo` (bool, o `None` si la tarea no lo requiere)
  - `es_ingles` (bool)
  - `instrucciones_sospechosas` (bool)
  - `debilidades`: códigos fijos, por ejemplo `missing_greeting`, `below_length`, `no_taught_vocabulary`
- **No usa el LLM:** son reglas objetivas que el código aplica con exactitud.

### 3. `evaluar_texto`
- **Entrada:** `texto: str`, `task_id: str`, `revision: dict` (salida de `revisar_texto`), `casos_similares: list` (salida de `buscar_contexto`, puede estar vacía)
- **Salida:** `dict` con:
  - `corridas`: puntajes de cada una de las `N_EVALUACIONES` corridas
  - `mediana`: puntaje propuesto por criterio
  - `criterios_en_desacuerdo`: criterios donde las corridas difieren en más de 0,5 banda
  - `justificacion`: la de la corrida más cercana a la mediana
  - `modelo`, `version_prompt`
  - `errores`: códigos de error ocurridos (por ejemplo `missing_scores`, `overloaded`)
- **Usa:** la recuperación por tarea de la Etapa 1 (rúbrica, criterios, ficha, vocabulario, muestras).

### 4. `consultar_historial`
- **Entrada:** `cadete_id: str`, `limite: int = 10`
- **Salida:** `list[dict]`, cada uno con `fecha`, `task_id`, `puntajes_finales`, `debilidades`, `accion` y `ajustado` (si el profesor cambió algún puntaje).
- **Memoria:** largo plazo (SQLite).

### 5. `buscar_contexto`
- **Entrada:** `consulta: str`, `task_id: str | None = None`, `k: int = 2`
- **Salida:** `list[dict]`, cada uno con `contenido`, `fuente` (`criteria.md` o `caso`) y `referencia` (sección o id del caso).
- **Memoria:** semántica (Chroma). Si se indica `task_id`, los casos se filtran por tarea antes de buscar por similitud.

### 6. `guardar_evaluacion`
- **Entrada:** `cadete_id`, `task_id`, `corridas`, `puntajes_propuestos`, `puntajes_finales`, `razones` (por criterio ajustado), `accion`, `debilidades`, `modelo`, `version_prompt`
- **Salida:** `{"ok": True, "evaluacion_id": ...}`
- **Escribe en:** SQLite (registro completo) y Chroma (resumen del caso en inglés, generado por código).
- **Solo se ejecuta** cuando el profesor presiona Confirmar.

### 7. `generar_retroalimentacion`
- **Entrada:** `texto: str`, `task_id: str`, `puntajes_finales: dict`, `justificacion: str`, `razones: dict`, `progreso: dict`
- **`progreso`** (calculado por código a partir de `consultar_historial`):
  - `tiene_historial` (bool)
  - `debilidades_superadas`: estaban en la evaluación anterior y ya no aparecen
  - `debilidades_persistentes`: aparecen en ambas
- **Salida:** `str`, en español y de máximo 200 palabras.
- **Solo se ejecuta** después de confirmar, a partir de los puntajes finales del profesor.
- **Reglas del prompt:** si una razón del profesor contradice la justificación, prevalece la razón del profesor. El progreso se menciona solo si `tiene_historial` es verdadero y solo a partir de las debilidades, nunca comparando puntajes.
- **Verificación por código:** 200 palabras o menos, en español y sin puntajes ni bandas. Si falla, se regenera una vez y se registra el error.

## Cómo se conectan

| Salida de | Alimenta a |
|---|---|
| `consultar_tarea` | `revisar_texto` (extensión, saludo, vocabulario) |
| `revisar_texto` | `evaluar_texto` (hechos para el prompt) y el planner (reglas 1, 2 y 4) |
| `buscar_contexto` | `evaluar_texto` (casos similares como ejemplos) y el chat |
| `consultar_historial` | El planner (regla 4), `generar_retroalimentacion` (progreso) y el chat |
| `evaluar_texto` | El planner (reglas 3 y 5) y el panel de revisión |
| Confirmación del profesor | `guardar_evaluacion` y `generar_retroalimentacion` |

## Tools disponibles en el chat

El chat es de solo lectura: el agente del chat solo tiene acceso a `consultar_tarea`, `consultar_historial` y `buscar_contexto`. La evaluación abierta en el panel se le entrega como contexto, para responder preguntas como "Why did you give Language 2.5?". Las tools que escriben (`guardar_evaluacion`, `generar_retroalimentacion`) y la evaluación (`evaluar_texto`) solo se ejecutan desde el panel.