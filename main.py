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
import os
import sys
import argparse
from datetime import datetime, timezone, timedelta

# Importar desde centinela-core
from core.llm import LLMClient
from core.dedupe import deduplicar
from core.normalizacion import normalizar_titulo, normalizar_texto
from core.auditor import ejecutar_con_auditoria
from core.calidad import PanelCalidad
from core.entrega import enviar_telegram, enviar_discord
from core.persistencia import guardar_salida, cargar_hashes_previos

# Importar módulos propios del RADAR
from radar.fetch_rss import fetch_todos_medios
from radar.matching import cruzar_con_conectores
from radar.capa2_perplexity import ejecutar_capa2
from radar.semaforo import asignar_estados, generar_tablero
from radar.top5_venezuela import generar_top5_venezuela
from radar.top_global import generar_top10_global, extraer_titulares_para_top10
from radar.csv_matriz import generar_csv_matriz, generar_nombre_archivo_csv
from radar.render_radar import render_html_radar, generar_mensaje_telegram

PAGES_URL = "https://mmorfe-engineer.github.io/centinela-radar/"


def cargar_config():
    """Cargar configuración del canal RADAR"""
    with open("config/reporte.json", "r", encoding="utf-8") as f:
        return json.load(f)


def cargar_medios():
    """Cargar lista de medios"""
    with open("config/radar_medios.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("medios", [])


def cargar_conectores():
    """Cargar conectores temáticos"""
    with open("config/conectores.json", "r", encoding="utf-8") as f:
        return json.load(f)


def parse_args():
    """Parsear argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(description="CENTINELA-RADAR Pipeline")
    parser.add_argument("--corte", type=str, choices=["MATUTINO", "VESPERTINO"], default="MATUTINO",
                       help="Tipo de corte a ejecutar")
    return parser.parse_args()


def main():
    """Pipeline principal del RADAR"""
    args = parse_args()
    corte = args.corte
    corte_pipeline = corte  # preservar antes de que generar_nombre_archivo_csv lo sobrescriba
    # 1. Cargar configuración
    config = cargar_config()
    medios = cargar_medios()
    conectores = cargar_conectores()
    
    # 2. Inicializar panel de calidad
    panel = PanelCalidad()
    
    # 3. Capa 1: Determinista (RSS/portada)
    # fetch_todos_medios devuelve: {"medios": [...], "errores": [...], "titulares_todos": [...]}
    capa1_result = fetch_todos_medios(medios)
    
    # 4. Cruce con conectores (matching)
    hallazgos_capa1 = cruzar_con_conectores(
        capa1_result["titulares_todos"],
        conectores
    )
    
    # 4.5. Agrupar hallazgos por medio
    hallazgos_por_medio = {}
    for hallazgo in hallazgos_capa1:
        medio_id = hallazgo.get("medio_id", "desconocido")
        if medio_id not in hallazgos_por_medio:
            hallazgos_por_medio[medio_id] = []
        hallazgos_por_medio[medio_id].append(hallazgo)
    
    # 5. Asignar estados (semáforo)
    estados, tablero, errores_medios = asignar_estados(
        medios,
        capa1_result,
        hallazgos_por_medio
    )
    
    # 6. Registrar métricas de capa 1
    panel.registrar_dedup(
        iniciales=len(capa1_result["titulares_todos"]),
        deduplicados=0,  # dedup se hace después
        agrupados=0
    )
    
    # 7. Capa 2: Perplexity (búsquedas por región)
    cliente_llm = LLMClient()

    # Construir mapeo región → medio_ids desde la configuración de medios
    medios_por_region: dict = {}
    for medio in medios:
        region = medio.get("region")
        if region:
            medios_por_region.setdefault(region, []).append(medio.get("id"))

    conectores_tematicos = list(conectores.get("grupos", {}).keys())

    resultados_capa2 = ejecutar_capa2(
        consultas_config=config.get("consultas_perplexity", []),
        medios_por_region=medios_por_region,
        conectores_tematicos=conectores_tematicos,
        cliente_llm=cliente_llm
    )

    hallazgos_capa2 = []
    for region, data in resultados_capa2.get("por_region", {}).items():
        hallazgos_capa2.extend(data.get("hallazgos", []))

    # 8. Unificar hallazgos (capa1 + capa2) y filtrar por ventana temporal
    # Perplexity devuelve resultados históricos de su índice aunque el prompt
    # diga "hoy". Descartamos cualquier hallazgo con fecha fuera de las últimas 48h.
    _limite_48h = datetime.now(tz=timezone.utc) - timedelta(hours=48)

    def _es_reciente(h: dict) -> bool:
        fecha_str = (h.get("fecha") or "").strip()
        if not fecha_str:
            return True  # sin fecha = RSS actual, se incluye
        try:
            f = datetime.fromisoformat(fecha_str.replace("Z", "+00:00"))
            if f.tzinfo is None:
                f = f.replace(tzinfo=timezone.utc)
            return f >= _limite_48h
        except Exception:
            return True  # no parseable = incluir

    todos_hallazgos = hallazgos_capa1 + [h for h in hallazgos_capa2 if _es_reciente(h)]
    
    # 9. Deduplicar
    # core.dedupe requiere 'fuente_url'; matching.py usa 'url' (y portadas tienen url=None)
    import hashlib as _hashlib
    for h in todos_hallazgos:
        if not h.get('fuente_url'):
            url = h.get('url') or ''
            if not url:
                key = f"{h.get('medio_id', '')}/{h.get('titulo', '')}"
                url = f"synthetic://{_hashlib.md5(key.encode()).hexdigest()}"
            h['fuente_url'] = url
    nuevos, telemetria_dedup = deduplicar(todos_hallazgos, hashes_previos=set())
    
    # 10. Clasificar (DeepSeek-R1)
    from radar.clasificacion import clasificar_todos
    nuevos = clasificar_todos(nuevos, cliente_llm)
    
    # 11. Top 5 Venezuela y Top 10 Global
    top5_ve = generar_top5_venezuela(nuevos, medios)
    
    # Extraer todos los titulares para Top 10 Global
    todos_titulares = extraer_titulares_para_top10(capa1_result)
    top10_global = generar_top10_global(todos_titulares, medios)
    
    # 12. Generar CSV
    fecha, corte = generar_nombre_archivo_csv()
    csv_matriz = generar_csv_matriz(nuevos, medios, fecha, corte)
    
    # 13. Construir contrato y renderizar informe HTML
    contrato = {
        "correlativo": f"{datetime.now().strftime('%Y%m%d')}-RADAR-{corte_pipeline}",
        "tipo_reporte": "radar",
        "canal": config["canal"],
        "nombre_visible": config["nombre_visible"],
        "tablero_certificacion": tablero,
        "top5_venezuela": top5_ve,
        "top10_global": top10_global,
        "hallazgos": nuevos,
        "csv_matriz": csv_matriz,
        "panel_calidad": panel.resumen(),
        "estados_medios": estados,
        "errores_medios": errores_medios,
        "medios_config": medios,
    }
    html = render_html_radar(contrato, url_pages=PAGES_URL, corte=corte_pipeline)

    # 13.5 Guardar HTML para GitHub Pages (docs/index.html en rama main)
    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as _f:
        _f.write(html)

    # 14. Entregar — mensaje corto en Telegram + link al informe
    import logging as _logging
    msg_telegram = generar_mensaje_telegram(contrato, url_pages=PAGES_URL, corte=corte_pipeline)
    resultado_tg = enviar_telegram(msg_telegram)
    if resultado_tg.get("success"):
        _logging.info(f"Telegram: {resultado_tg['detalle']}")
    else:
        _logging.warning(f"Telegram falló: {resultado_tg.get('detalle')} | {resultado_tg.get('error')}")
    enviar_discord(html)
    
    # 15. Guardar en rama datos
    guardar_salida(contrato["correlativo"], contrato)
    
    # 16. Finalizar
    panel.finalizar()
    print(f"Tiempo de ejecución: {panel.resumen()['tiempo_ejecucion']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
