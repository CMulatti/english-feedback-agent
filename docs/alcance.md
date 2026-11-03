# Alcance del agente (EA2)

Resumen de referencia para no perder el panorama general durante el desarrollo.

## Propósito

Un agente que asiste al profesor de inglés a procesar textos de cadetes: evalúa cada texto con la rúbrica de Cambridge y los criterios de la Academia, decide qué necesita cada caso, recuerda el historial de cada cadete y responde preguntas del profesor. **El agente prepara; el profesor decide.**

## Qué hará

- Revisar el texto con código: extensión, vocabulario enseñado, saludo, idioma e instrucciones sospechosas.
- Evaluar el texto 3 veces con el LLM (RAG por tarea) y proponer la mediana de los puntajes.
- Decidir una acción según reglas priorizadas (planner).
- Consultar el historial del cadete y detectar debilidades recurrentes.
- Buscar por significado en los criterios y en casos anteriores corregidos por profesores.
- Responder preguntas abiertas del profesor en un chat, con botones de preguntas sugeridas.
- Guardar la evaluación confirmada y generar la retroalimentación para el cadete (en español) a partir de los puntajes finales.

## Qué NO hará

- Asignar notas finales por su cuenta: todo puntaje pasa por la confirmación del profesor.
- Enviar retroalimentación al cadete sin aprobación.
- Cambiar puntajes desde el chat: el chat es de solo lectura.
- Modificar la rúbrica o los criterios (sí puede informar patrones para que el equipo los revise).
- Guardar nombres o grados: solo códigos anónimos (`CDT-001`).
- Tomar decisiones académicas o disciplinarias, ni sacar conclusiones sobre el cadete más allá de su escritura.

## Idioma

Todo en inglés (prompts, evaluación, chat, memoria semántica), excepto la retroalimentación para el cadete, en español.

## Memoria

| Tipo | Qué recuerda | Dónde | Ejemplo |
|---|---|---|---|
| Corto plazo | La conversación de la sesión y el texto abierto | RAM (`st.session_state`) | "Why did you give Language 2.5?" sin repetir el cadete |
| Largo plazo | Evaluaciones confirmadas por cadete: puntajes, ajustes, razones, acción | SQLite | Tercer saludo faltante de CDT-004 → recomendar refuerzo |
| Semántica | Criterios por sección y resúmenes de casos (en inglés, generados por código) | Chroma | Casos similares corregidos se agregan como ejemplos al prompt |

## Tools

| # | Tool | Tipo | Entrada | Salida |
|---|---|---|---|---|
| 1 | `consultar_tarea` | Consulta | `task_id` | Ficha de la tarea (puntos, extensión, formato, vocabulario) |
| 2 | `revisar_texto` | Razonamiento (código) | `texto`, `task_id` | Palabras, estado de extensión, vocabulario encontrado, saludo, idioma, instrucciones sospechosas |
| 3 | `evaluar_texto` | Razonamiento (LLM + RAG) | `texto`, `task_id` | Puntajes por corrida, mediana, criterios en desacuerdo, justificación |
| 4 | `consultar_historial` | Consulta (largo plazo) | `cadete_id` | Lista de evaluaciones anteriores |
| 5 | `buscar_contexto` | Consulta (semántica) | `consulta`, `task_id` opcional | Fragmentos de criterios y casos similares, con su fuente |
| 6 | `guardar_evaluacion` | Escritura | Cadete, tarea, puntajes propuestos y finales, razones, acción | Confirmación (SQLite + Chroma) |
| 7 | `generar_retroalimentacion` | Escritura (LLM) | `texto`, evaluación final, `task_id` | Retroalimentación en español |

## Reglas del planner (en orden de prioridad)

| # | Condición | Acción |
|---|---|---|
| 1 | Texto vacío o muy por debajo del mínimo (umbral a definir) | `solicitar_reescritura` |
| 2 | Texto no está en inglés o contiene instrucciones al sistema | `escalar_profesor` |
| 3 | Las 3 evaluaciones difieren en más de 0,5 banda en algún criterio | `caso_dudoso` |
| 4 | Debilidad recurrente en el historial (≥3 veces) | `recomendar_refuerzo` |
| 5 | Puntaje total bajo (umbral a definir) | `priorizar_revision` |
| 6 | Caso estándar | `revision_rapida` |

Todas las acciones terminan en la revisión del profesor.

## Interfaz

- **Panel de revisión:** tarea, código del cadete, texto → Evaluar → decisión, puntajes y justificación → aceptar o ajustar cada criterio → Confirmar → retroalimentación.
- **Chat de solo lectura:** preguntas abiertas, con botones sugeridos según el momento (sin texto, después de evaluar, caso dudoso).

## Escenarios de la demo

1. **Caso estándar:** se evalúa, el profesor confirma, se guarda.
2. **Memoria:** tercer saludo faltante de CDT-004 → recomendar refuerzo; preguntas de seguimiento en el chat.
3. **Adaptación:** una corrección del profesor se guarda y aparece como ejemplo en el siguiente texto similar.
4. **Escalamiento:** las 3 evaluaciones no coinciden → caso dudoso.

## Decisiones adicionales

- **Ajuste de puntajes:** el profesor puede modificar cada puntaje en el panel antes de confirmar (0 a 5, en pasos de 0,5). Todo ajuste requiere una razón.
- **Confirmado es final:** una evaluación confirmada no se modifica en esta etapa (corrección con versiones: trabajo futuro).

## Preparación para la Etapa 3 (observabilidad)

Para medir precisión, consistencia y frecuencia de errores, el agente registrará desde el inicio:

- **Registro de ejecución:** una fila por cada llamada a una tool o al LLM (hora, sesión, tool, modelo, duración, tokens, resultado, tipo de error), mediante una única función auxiliar.
- **Las 3 corridas de cada evaluación**, no solo la mediana (consistencia).
- **Puntaje propuesto y puntaje final del profesor** (precisión).
- **Modelo y versión del prompt** en cada evaluación, para comparar cambios.
- **Tipos de error con códigos fijos:** `missing_scores`, `truncated`, `empty_response`, `rate_limit`, `wrong_language`, entre otros.
- Se mantienen `evaluation/` y `evaluate.py` como conjunto de prueba controlado.

## Métricas de éxito

- Evaluación de un caso estándar con 3 corridas en menos de 90 segundos (medir con Gemini).
- Al menos 70% de los puntajes propuestos a 0,5 banda o menos de la profesora en los textos de `evaluation/`.
- 100% de los textos con desacuerdo mayor a 0,5 banda marcados como caso dudoso.
- 6 de 6 reglas del planner con test aprobado; 12 o más tests aprobados en total.
- La pregunta sobre el saludo recupera la sección "Format" de los criterios entre los 2 primeros resultados.
- 0 puntajes guardados o retroalimentaciones generadas sin confirmación del profesor.
- Retroalimentación al cadete en español, en 200 palabras o menos.
- 4 escenarios distintos demostrables en 10 minutos.