# Reglas de decisión

El planner responde dos preguntas distintas, que no compiten entre sí:

1. **¿Cómo debe revisar el profesor este texto?** Una sola **acción de revisión**, según reglas en orden de prioridad.
2. **¿Qué necesita este cadete?** Cero o más **recomendaciones**, que se muestran siempre, cualquiera sea la acción.

Se separaron porque una debilidad recurrente no cambia cómo se califica el texto, pero el profesor siempre debe conocerla. En una versión anterior, la recomendación de refuerzo era una regla más y quedaba oculta cuando otra regla tenía prioridad (por ejemplo, un caso dudoso).

Todas las acciones terminan en la revisión del profesor: el agente propone, el profesor decide.

## Acción de revisión (orden de prioridad)

El planner evalúa las reglas de arriba hacia abajo y se detiene en la primera que se cumple. Por eso las situaciones más delicadas van primero, y la regla 5 ("ninguna de las anteriores") va siempre al final: si estuviera antes, se cumpliría siempre y las reglas siguientes nunca se revisarían.

| # | Condición | Acción | Razón |
|---|---|---|---|
| 1 | El texto está vacío o tiene menos del 20% de las palabras mínimas | `escalar_profesor` | No hay contenido suficiente para evaluar; el profesor decide qué hacer |
| 2 | Más del 30% de las palabras están en español, o el texto contiene instrucciones dirigidas al sistema | `escalar_profesor` | Evaluarlo no tendría sentido o sería riesgoso |
| 3 | Las corridas de evaluación difieren en 1 banda o más en algún criterio, o hubo menos de 2 corridas válidas | `caso_dudoso` | El puntaje propuesto no es confiable |
| 4 | El puntaje total propuesto es menor que 9 de 15 | `priorizar_revision` | Desempeño bajo lo esperado |
| 5 | Ninguna de las anteriores | `revision_rapida` | Caso estándar |

Las reglas 1 y 2 tienen la misma acción, pero un motivo distinto (`texto_insuficiente`, `idioma` o `instrucciones_sospechosas`), que queda registrado para distinguirlas en el análisis de la Etapa 3.

Una diferencia de 0,5 banda entre corridas no se considera desacuerdo: es la variación mínima posible y no cambia la interpretación del desempeño.

Si el modelo no logra completar ninguna corrida (por ejemplo, porque está saturado), la acción es `escalar_profesor` con el motivo `evaluacion_fallida`. No es una regla del planner, sino una falla operativa que el profesor debe conocer.

## Recomendaciones para el cadete

| Condición | Recomendación | Razón |
|---|---|---|
| Una misma debilidad aparece por tercera vez (contando el texto actual) | `recomendar_refuerzo` | Error persistente, no aislado |

Se calculan antes de evaluar, con la revisión del texto y el historial, por lo que aparecen incluso si el texto se deriva al profesor o queda como caso dudoso.

## Contexto de uso

El sistema está pensado principalmente para evaluar textos escritos en pruebas, donde el estudiante no puede reescribir. Por eso, los textos cortos se evalúan igual (la regla 4 detecta los puntajes bajos), y solo los textos sin contenido evaluable se derivan al profesor. En actividades de clase también tiene sentido derivarlos al profesor, ya que normalmente es él quien revisa el trabajo antes de que se envíe.

## Por qué este orden

- **1 y 2 antes que todo:** si el texto no tiene contenido suficiente, no está en inglés o intenta manipular al sistema, no se debe evaluar. Estas reglas se revisan con código, antes de llamar al LLM, lo que además ahorra tiempo y solicitudes.
- **3 antes que 4:** si las evaluaciones no coinciden, el puntaje no es confiable, y una prioridad basada en él tampoco lo sería. Primero el profesor resuelve la duda.
- **5 al final:** es el caso estándar, cuando ninguna otra situación requiere atención especial.

Aunque el planner devuelve una sola acción, el panel muestra igualmente las recomendaciones, todas las debilidades detectadas y el historial del cadete, por lo que el profesor no pierde información.

## Debilidades registradas

Las detecta `revisar_texto` con código y se guardan en el historial de cada cadete:

| Código | Condición |
|---|---|
| `missing_greeting` | La tarea requiere saludo y el texto no lo tiene |
| `below_length` | El texto tiene menos palabras que el mínimo esperado |
| `no_taught_vocabulary` | No aparece ninguna palabra del vocabulario enseñado |
| `spanish_words` | El texto incluye 2 o más palabras en español (sin contar nombres propios) |

## Umbrales (en `config/settings.py`)

| Constante | Valor | Uso |
|---|---|---|
| `N_EVALUACIONES` | 3 | Corridas por texto |
| `UMBRAL_TEXTO_MINIMO` | 0,2 | Regla 1 (proporción del mínimo de palabras) |
| `UMBRAL_IDIOMA` | 0,3 | Regla 2 (proporción de palabras en español) |
| `UMBRAL_DESACUERDO` | 0,5 | Regla 3 (hay desacuerdo si la diferencia es mayor: 1 banda o más) |
| `MIN_CORRIDAS_VALIDAS` | 2 | Regla 3 (con menos corridas no se puede medir la consistencia) |
| `UMBRAL_PUNTAJE_BAJO` | 9 | Regla 4 (total sobre 15) |
| `UMBRAL_RECURRENCIA` | 3 | Recomendación de refuerzo (veces, contando el texto actual) |
| `MIN_PALABRAS_ESPANOL` | 2 | Debilidad `spanish_words` |

## Pruebas

`tests/test_planner.py` tiene al menos un test por regla, tests de prioridad (por ejemplo, un texto con desacuerdo entre corridas y un total menor que 9 debe dar `caso_dudoso`, no `priorizar_revision`) y tests de las recomendaciones. `tests/test_core.py` comprueba que la recomendación de refuerzo se muestra aunque la acción sea un caso dudoso.