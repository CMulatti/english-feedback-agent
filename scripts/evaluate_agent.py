"""
Evalúa el agente con los textos de evaluation/ y compara con los puntajes originales
de la profesora (su corrección habitual, antes de los criterios escritos).

Para cada texto ejecuta procesar_texto (que no guarda nada en las memorias) y registra:
puntajes de cada corrida, propuesta, desacuerdos, acción del planner, errores y tiempo.

Los resultados se guardan en evidence/stage2/<modelo>_<versión>_<fecha-hora>/:
- un archivo .json por texto, con la evaluación completa y su justificación;
- resumen.md, con las tablas y las métricas.

Antes de evaluar, conviene dejar las memorias en su estado inicial:
    python -m scripts.seed_data
    python -m scripts.index_memoria

Ejecutar desde la carpeta principal: python -m scripts.evaluate_agent
"""

import json
import os
import time
from datetime import datetime

from config import settings
from config.settings import BASE_DIR
from agent.core import procesar_texto
from agent.rag.retrieval import get_field
from agent.rag.checks import get_section

EVALUATION_DIR = BASE_DIR / "evaluation"
EVIDENCE_DIR = BASE_DIR / "evidence" / "stage2"
CRITERIOS = ["Content", "Organization", "Language"]
CADETE_EVALUACION = "EVAL"   # sin historial: la evaluación no depende de la memoria de largo plazo


# ---------- Lectura de los textos ----------

def leer_puntajes_originales(linea):
    """'Content 3 | Organization 4 | Language 2.5 or 3' -> {'Content': (3, 3), ..., 'Language': (2.5, 3)}"""
    puntajes = {}
    for parte in linea.split("|"):
        palabras = parte.split()
        valores = [float(p.replace(",", ".")) for p in palabras[1:] if p != "or"]
        puntajes[palabras[0]] = (min(valores), max(valores))
    return puntajes


def leer_muestra(ruta):
    texto = ruta.read_text(encoding="utf-8")
    return {
        "nombre": ruta.stem,
        "task_id": get_field(texto, "Task"),
        "originales": leer_puntajes_originales(get_field(texto, "Original scores")),
        "texto": "\n".join(get_section(texto, "Text")).strip(),
    }


# ---------- Comparación ----------

def distancia(puntaje, rango):
    """0 si el puntaje está dentro del rango de la profesora; si no, la diferencia (con signo)."""
    minimo, maximo = rango
    if puntaje < minimo:
        return puntaje - minimo
    if puntaje > maximo:
        return puntaje - maximo
    return 0.0


def formato_rango(rango):
    return str(rango[0]) if rango[0] == rango[1] else f"{rango[0]}-{rango[1]}"


# ---------- Evaluación ----------

def evaluar_muestra(muestra):
    inicio = time.time()
    resultado = procesar_texto(muestra["texto"], muestra["task_id"], CADETE_EVALUACION)
    resultado["duracion_s"] = round(time.time() - inicio, 1)
    return resultado


def main():
    modelo = os.getenv("LLM_MODEL", "desconocido")
    carpeta = EVIDENCE_DIR / f"{modelo}_{settings.VERSION_PROMPT}_{datetime.now():%Y%m%d-%H%M}"
    carpeta.mkdir(parents=True, exist_ok=True)

    lineas = [f"# Evaluación del agente", "",
              f"- Modelo: `{modelo}`", f"- Versión del prompt: `{settings.VERSION_PROMPT}`",
              f"- Corridas por texto: {settings.N_EVALUACIONES}",
              f"- Fecha: {datetime.now():%Y-%m-%d %H:%M}", ""]
    diferencias, textos_con_desacuerdo, acciones, duraciones, errores = [], 0, {}, [], []

    for ruta in sorted(EVALUATION_DIR.glob("*.md")):
        muestra = leer_muestra(ruta)
        print(f"\n=== {muestra['nombre']} ===  evaluando...")
        resultado = evaluar_muestra(muestra)
        (carpeta / f"{muestra['nombre']}.json").write_text(
            json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")

        accion = resultado.get("accion", {}).get("tipo", "error")
        acciones[accion] = acciones.get(accion, 0) + 1
        duraciones.append(resultado["duracion_s"])
        lineas += [f"## {muestra['nombre']}", "",
                   f"Acción: `{accion}` · Tiempo: {resultado['duracion_s']} s", ""]

        if not resultado.get("evaluado"):
            print(f"No evaluado: {resultado.get('accion') or resultado.get('error')}")
            lineas += ["No evaluado.", ""]
            continue

        evaluacion = resultado["evaluacion"]
        errores += evaluacion["errores"]
        if evaluacion["criterios_en_desacuerdo"]:
            textos_con_desacuerdo += 1

        tabla = ["| Criterio | Profesora | " + " | ".join(f"Corrida {i + 1}" for i in range(len(evaluacion["corridas"])))
                 + " | Propuesta | Diferencia |",
                 "|---|---|" + "---|" * len(evaluacion["corridas"]) + "---|---|"]
        for criterio in CRITERIOS:
            original = muestra["originales"][criterio]
            propuesta = evaluacion["mediana"][criterio]
            diferencia = distancia(propuesta, original)
            diferencias.append(abs(diferencia))
            corridas = " | ".join(str(c[criterio]) for c in evaluacion["corridas"])
            tabla.append(f"| {criterio} | {formato_rango(original)} | {corridas} | {propuesta} | {diferencia:+} |")
        print("\n".join(tabla))
        lineas += tabla + [""]

    # ---------- Resumen ----------
    total = len(diferencias)
    resumen = ["## Resumen", ""]
    if total:
        exactos = sum(1 for d in diferencias if d == 0)
        cercanos = sum(1 for d in diferencias if d <= 0.5)
        evaluados = total // len(CRITERIOS)
        resumen += [
            f"- Puntajes comparados: {total}",
            f"- Dentro del rango de la profesora: {exactos} ({exactos / total:.0%})",
            f"- Diferencia de 0,5 o menos: {cercanos} ({cercanos / total:.0%})",
            f"- Diferencia promedio: {sum(diferencias) / total:.2f}",
            f"- Textos con desacuerdo entre corridas: {textos_con_desacuerdo} de {evaluados}",
        ]
    resumen += [
        f"- Acciones: " + ", ".join(f"{a} ({n})" for a, n in acciones.items()),
        f"- Tiempo promedio por texto: {sum(duraciones) / len(duraciones):.1f} s",
        f"- Errores en las corridas: {', '.join(errores) or 'ninguno'}",
    ]
    print("\n" + "\n".join(resumen))
    (carpeta / "resumen.md").write_text("\n".join(lineas + resumen) + "\n", encoding="utf-8")
    print(f"\nResultados guardados en {carpeta}")


if __name__ == "__main__":
    main()