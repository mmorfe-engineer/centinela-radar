#!/usr/bin/env python3
"""
CENTINELA-RADAR: Pipeline principal de monitoreo automatizado
========================

Pipeline en dos capas:
1. Capa determinista: fetch RSS/portada de ~35 medios internacionales
2. Capa semántica: búsquedas Perplexity por región + clasificación DeepSeek

Estructura:
- config/reporte.json: identidad del canal (consultas, semáforo, tops)
- radar/: módulos propios del RADAR (fetch, matching, semáforo, tops, CSV)
- main.py: orchestrador que importa core y ejecuta
"""

import json
import sys
from datetime import datetime

# Importar desde centinela-core
from core.llm import LLMClient
from core.dedupe import deduplicar
from core.normalizacion import normalizar_titulo, normalizar_texto
from core.auditor import ejecutar_con_auditoria
from core.calidad import PanelCalidad
from core.render import render_informe
from core.entrega import enviar_telegram, enviar_discord
from core.persistencia import guardar_salida, cargar_hashes_previos

# Importar módulos propios del RADAR
from radar.fetch_rss import fetch_todos_medios
from radar.matching import cruzar_con_conectores
from radar.semaforo import asignar_estados, generar_tablero
from radar.top_global import calcular_top5_venezuela, calcular_top10_global
from radar.csv_matriz import generar_csv_matriz


def cargar_config():
    """Cargar configuración del canal RADAR"""
    with open("config/reporte.json", "r", encoding="utf-8") as f:
        return json.load(f)


def cargar_medios():
    """Cargar lista de medios"""
    with open("config/radar_medios.json", "r", encoding="utf-8") as f:
        return json.load(f)


def cargar_conectores():
    """Cargar conectores temáticos"""
    with open("config/conectores.json", "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    """Pipeline principal del RADAR"""
    # 1. Cargar configuración
    config = cargar_config()
    medios = cargar_medios()
    conectores = cargar_conectores()
    
    # 2. Inicializar panel de calidad
    panel = PanelCalidad()
    panel.iniciar()
    
    # 3. Capa 1: Determinista (RSS/portada)
    # fetch_todos_medios devuelve: {"medios": [...], "errores": [...], "titulares_todos": [...]}
    capa1_result = fetch_todos_medios(medios)
    
    # 4. Cruce con conectores (matching)
    hallazgos_capa1 = cruzar_con_conectores(
        capa1_result["titulares_todos"],
        conectores
    )
    
    # 5. Asignar estados (semáforo)
    estados, tablero = asignar_estados(
        medios,
        capa1_result["medios"],
        capa1_result["errores"],
        hallazgos_capa1
    )
    
    # 6. Registrar métricas de capa 1
    panel.registrar_dedup(
        iniciales=len(capa1_result["titulares_todos"]),
        deduplicados=0,  # dedup se hace después
        agrupados=0
    )
    
    # 7. Capa 2: Perplexity (búsquedas por región)
    cliente_llm = LLMClient()
    hallazgos_capa2 = []
    
    for consulta in config.get("consultas_perplexity", []):
        # Ejecutar búsqueda
        resultado = cliente_llm.completar(
            accion="buscar",
            prompt=consulta["query"],
            modelo=consulta.get("modelo", "sonar"),
            max_tokens=2000
        )
        hallazgos_capa2.extend(resultado.get("hallazgos", []))
    
    # 8. Unificar hallazgos (capa1 + capa2)
    todos_hallazgos = hallazgos_capa1 + hallazgos_capa2
    
    # 9. Deduplicar
    nuevos, telemetria_dedup = deduplicar(todos_hallazgos, hashes_previos=set())
    
    # 10. Clasificar (DeepSeek-R1)
    for hallazgo in nuevos:
        clasif = cliente_llm.completar(
            accion="clasificar",
            prompt=f"Clasifica este hallazgo: {hallazgo.get('titulo', '')} {hallazgo.get('texto', '')[:200]}",
            modelo="deepseek-r1",
            temp=0
        )
        hallazgo.update(clasif)
    
    # 11. Top 5 Venezuela y Top 10 Global
    top5_ve = calcular_top5_venezuela(nuevos)
    top10_global = calcular_top10_global(capa1_result["titulares_todos"])
    
    # 12. Generar CSV
    csv_matriz = generar_csv_matriz(nuevos, medios, tablero)
    
    # 13. Renderizar informe
    contrato = {
        "correlativo": f"{datetime.now().strftime('%Y%m%d')}-RADAR",
        "tipo_reporte": "radar",
        "canal": config["canal"],
        "nombre_visible": config["nombre_visible"],
        "tablero_certificacion": tablero,
        "top5_venezuela": top5_ve,
        "top10_global": top10_global,
        "hallazgos": nuevos,
        "csv_matriz": csv_matriz,
        "panel_calidad": panel.resumen()
    }
    html = render_informe(contrato)
    
    # 14. Entregar
    enviar_telegram(html[:3500])
    enviar_discord(html)
    
    # 15. Guardar en rama datos
    guardar_salida(contrato["correlativo"], contrato)
    
    # 16. Finalizar
    panel.finalizar()
    print(f"Tiempo de ejecución: {panel.resumen()['tiempo_ejecucion']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
