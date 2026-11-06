# Comparación de evaluaciones

Cuatro textos de `evaluation/` (tarea `cadet_routine`), comparados con los puntajes originales de la profesora. Cada evaluación usa 3 corridas por texto.

## Resultados por ejecución

| Modelo | Versión | Ejecución | Dentro del rango | A 0,5 o menos | Diferencia promedio | Textos con desacuerdo |
|---|---|---|---|---|---|---|
| MiniMax M3 (Etapa 1) | Etapa 1 | Mejor (M5) | 25% | 58% | 0,62 | – |
| Nemotron 3 Super (Etapa 1) | Etapa 1 | Mejor (N1) | 67% | 83% | 0,38 | – |
| Nemotron 3 Super (Etapa 1) | Etapa 1 | N2 | 42% | 67% | 0,62 | – |
| gemini-3.5-flash-lite | v2 | 1 | 33% | 67% | 0,71 | 2 de 4 |
| gemini-3.5-flash-lite | v3 | 1 | 67% | 83% | 0,29 | 1 de 4 |
| gemini-3.5-flash-lite | v3 | 2 | 58% | 75% | 0,46 | 1 de 4 |
| gemini-3.5-flash-lite | v3 | 3 | 67% | 83% | 0,29 | 3 de 4 |
| **gemini-3.5-flash-lite** | **v3** | **Promedio de 3** | **64%** | **80%** | **0,35** | **5 de 12** |

## Cambio entre v2 y v3

En v3 se reescribió la sección Content de `criteria.md`: los criterios solo indicaban qué impide la banda 5, sin orientación para las bandas inferiores. El modelo completaba ese vacío con severidad y asignaba Content 1 a textos cortos con algún punto faltante.

- Content 1 en las muestras 2 y 6: 6 de 6 corridas en v2; 1 de 18 corridas en v3. En ese caso, la mediana lo corrigió.
- La muestra 8 (banda 5) no se vio afectada por el cambio.

## Observaciones

- **La muestra 4 sigue siendo inestable:** Organization y Language 5 en 4 de 9 corridas de v3, el mismo patrón observado con Nemotron y MiniMax en este texto (pocos errores, estructuras repetitivas). En la ejecución 2, dos de tres corridas dieron 5, por lo que la mediana no lo corrigió; aun así, el texto se marcó como caso dudoso en las tres ejecuciones.
- **Las diferencias en Organization** se mantienen siempre por debajo de la profesora: corresponden a la regla del saludo y a la distancia entre la corrección intuitiva y el descriptor de la banda, documentada en la Etapa 1.
- **Los resultados varían entre ejecuciones del mismo sistema**, por lo que se informan promedios de varias ejecuciones y no una sola.
- **Operación:** entre 10 y 13 segundos por texto. Hubo errores de sobrecarga y límite de solicitudes, pero los reintentos los resolvieron en todos los casos.

## Limitaciones

Cuatro textos de una sola tarea y los puntajes de una sola profesora. El cambio de v3 se motivó observando estos mismos textos; se justifica porque completa un vacío de los criterios y coincide con una decisión ya tomada en una muestra de referencia (cadet_routine_01, Content 3 con un perfil similar), pero los resultados deben entenderse como indicativos.