# Evaluación del agente

- Modelo: `gemini-3.5-flash-lite`
- Versión del prompt: `v2`
- Corridas por texto: 3
- Fecha: 2026-11-06 16:24

## cadet_routine_02

Acción: `priorizar_revision` · Tiempo: 13.6 s

| Criterio | Profesora | Corrida 1 | Corrida 2 | Corrida 3 | Propuesta | Diferencia |
|---|---|---|---|---|---|---|
| Content | 3.0 | 1.0 | 1.0 | 1.0 | 1.0 | -2.0 |
| Organization | 4.0 | 2.5 | 2.5 | 2.0 | 2.5 | -1.5 |
| Language | 2.5-3.0 | 2.0 | 2.0 | 2.0 | 2.0 | -0.5 |

## cadet_routine_04

Acción: `caso_dudoso` · Tiempo: 8.2 s

| Criterio | Profesora | Corrida 1 | Corrida 2 | Corrida 3 | Propuesta | Diferencia |
|---|---|---|---|---|---|---|
| Content | 3.5 | 3.0 | 3.0 | 3.0 | 3.0 | -0.5 |
| Organization | 4.0 | 3.0 | 3.0 | 5.0 | 3.0 | -1.0 |
| Language | 2.5-3.0 | 3.0 | 3.0 | 5.0 | 3.0 | +0.0 |

## cadet_routine_06

Acción: `caso_dudoso` · Tiempo: 8.2 s

| Criterio | Profesora | Corrida 1 | Corrida 2 | Corrida 3 | Propuesta | Diferencia |
|---|---|---|---|---|---|---|
| Content | 3.0 | 1.0 | 1.0 | 1.0 | 1.0 | -2.0 |
| Organization | 3.5 | 3.0 | 3.0 | 2.0 | 3.0 | -0.5 |
| Language | 2.5-3.0 | 2.0 | 3.0 | 2.0 | 2.0 | -0.5 |

## cadet_routine_08

Acción: `revision_rapida` · Tiempo: 8.1 s

| Criterio | Profesora | Corrida 1 | Corrida 2 | Corrida 3 | Propuesta | Diferencia |
|---|---|---|---|---|---|---|
| Content | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | +0.0 |
| Organization | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | +0.0 |
| Language | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | +0.0 |

## Resumen

- Puntajes comparados: 12
- Dentro del rango de la profesora: 4 (33%)
- Diferencia de 0,5 o menos: 8 (67%)
- Diferencia promedio: 0.71
- Textos con desacuerdo entre corridas: 2 de 4
- Acciones: priorizar_revision (1), caso_dudoso (2), revision_rapida (1)
- Tiempo promedio por texto: 9.5 s
- Errores en las corridas: ninguno
