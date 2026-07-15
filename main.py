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
from radar.csv_matriz import generar_csv_matriz, generar_nombre_archivo_csv
from radar.render_radar import render_html_radar, generar_mensaje_telegram

PAGES_URL = "https://mmorfe-engineer.github.io/centinela-radar/"
_VERDE = "VERDE_con_cobertura"

# Entidades que confirman que un hallazgo es sobre Venezuela.
# Los conectores en conectores.json pueden ser genéricos (ej: "sanciones", "petróleo");
# este filtro garantiza que el artículo mencione Venezuela de forma explícita.
_ENTIDADES_VENEZUELA = {
    "venezuela", "venezolano", "venezolana", "venezolanos", "venezolanas",
    "venezuelan", "venezuelans",
    "maduro", "nicolas maduro", "nicolás maduro",
    "chavez", "chavez", "chavismo", "chavista", "chavistas",
    "psuv", "bolivariano", "bolivariana",
    "miraflores", "pdvsa", "petro", "bolivar",
    "caracas", "maracaibo",
}


def _es_sobre_venezuela(h: dict) -> bool:
    """True si el hallazgo menciona explícitamente entidades venezolanas."""
    titulo = normalizar_titulo(h.get("titulo", "") or "")
    resumen = normalizar_titulo(h.get("resumen_1_frase", "") or "")
    conectores_str = " ".join(
        normalizar_titulo(c or "") for c in h.get("conectores_activados", [])
    )
    texto = f"{titulo} {resumen} {conectores_str}"
    return any(e in texto for e in _ENTIDADES_VENEZUELA)


def cargar_config():
    with open("config/reporte.json", "r", encoding="utf-8") as f:
        return json.load(f)


def cargar_medios():
    with open("config/radar_medios.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("medios", [])


def cargar_conectores():
    with open("config/conectores.json", "r", encoding="utf-8") as f:
        return json.load(f)


def parse_args():
    parser = argparse.ArgumentParser(description="CENTINELA-RADAR Pipeline")
    parser.add_argument("--corte", type=str, choices=["MATUTINO", "VESPERTINO"], default="MATUTINO",
                       help="Tipo de corte a ejecutar")
    return parser.parse_args()


def main():
    """Pipeline principal del RADAR"""
    args = parse_args()
    corte = args.corte
    corte_pipeline = corte

    # 1. Cargar configuración
    config = cargar_config()
    medios = cargar_medios()
    conectores = cargar_conectores()

    # 2. Inicializar panel de calidad
    panel = PanelCalidad()

    # 3. Capa 1: Determinista (RSS/portada)
    capa1_result = fetch_todos_medios(medios)

    # 4. Cruce con conectores (matching)
    hallazgos_capa1 = cruzar_con_conectores(
        capa1_result["titulares_todos"],
        conectores
    )

    # 5. Registrar métricas de capa 1
    panel.registrar_dedup(
        iniciales=len(capa1_result["titulares_todos"]),
        deduplicados=0,
        agrupados=0
    )

    # 6. Capa 2: Perplexity (búsquedas por región)
    cliente_llm = LLMClient()

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

    # Perplexity devuelve resultados históricos — filtrar a últimas 48h
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
            return True

    hallazgos_capa2_recientes = [
        h
        for region_data in resultados_capa2.get("por_region", {}).values()
        for h in region_data.get("hallazgos", [])
        if _es_reciente(h)
    ]

    # 7. Unificar capa1 + capa2 filtrada
    todos_hallazgos = hallazgos_capa1 + hallazgos_capa2_recientes

    # 8. Deduplicar
    import hashlib as _hashlib
    for h in todos_hallazgos:
        if not h.get('fuente_url'):
            url = h.get('url') or ''
            if not url:
                key = f"{h.get('medio_id', '')}/{h.get('titulo', '')}"
                url = f"synthetic://{_hashlib.md5(key.encode()).hexdigest()}"
            h['fuente_url'] = url
    nuevos, telemetria_dedup = deduplicar(todos_hallazgos, hashes_previos=set())

    # 9. Clasificar
    from radar.clasificacion import clasificar_todos
    nuevos = clasificar_todos(nuevos, cliente_llm)

    # 10. FILTRO ESTRICTO: solo hallazgos que mencionan entidades venezolanas reales.
    # Los conectores pueden ser genéricos ("sanciones", "petróleo") y capturar
    # artículos de Irán, Colombia, etc. Este filtro garantiza que el hallazgo
    # mencione Venezuela de forma explícita en título, resumen o conectores activados.
    hallazgos_venezuela = [h for h in nuevos if _es_sobre_venezuela(h)]

    # 11. Semáforo DEFINITIVO — calculado con hallazgos Venezuela reales.
    # Un medio es VERDE solo si tiene al menos un artículo sobre Venezuela confirmado.
    # La coherencia garantizada: N verdes = exactamente los medios con hallazgos reales.
    hallazgos_por_medio_ve = {}
    for h in hallazgos_venezuela:
        mid = h.get("medio_id", "desconocido")
        hallazgos_por_medio_ve.setdefault(mid, []).append(h)

    estados, tablero, errores_medios = asignar_estados(
        medios,
        capa1_result,
        hallazgos_por_medio_ve
    )

    # 12. Hallazgos del informe = solo medios VERDES con hallazgos Venezuela
    medios_verdes = {mid for mid, est in estados.items() if est == _VERDE}
    hallazgos_informe = [h for h in hallazgos_venezuela if h.get("medio_id") in medios_verdes]

    # 13. Generar CSV
    fecha, corte = generar_nombre_archivo_csv()
    csv_matriz = generar_csv_matriz(hallazgos_informe, medios, fecha, corte)

    # 14. Construir contrato y renderizar informe HTML
    contrato = {
        "correlativo": f"{datetime.now().strftime('%Y%m%d')}-RADAR-{corte_pipeline}",
        "tipo_reporte": "radar",
        "canal": config["canal"],
        "nombre_visible": config["nombre_visible"],
        "tablero_certificacion": tablero,
        "hallazgos": hallazgos_informe,
        "csv_matriz": csv_matriz,
        "panel_calidad": panel.resumen(),
        "estados_medios": estados,
        "errores_medios": errores_medios,
        "medios_config": medios,
    }
    html = render_html_radar(contrato, url_pages=PAGES_URL, corte=corte_pipeline)

    # 14.5 Guardar HTML para GitHub Pages
    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as _f:
        _f.write(html)

    # 15. Entregar — mensaje corto en Telegram + link al informe
    import logging as _logging
    msg_telegram = generar_mensaje_telegram(contrato, url_pages=PAGES_URL, corte=corte_pipeline)
    resultado_tg = enviar_telegram(msg_telegram)
    if resultado_tg.get("success"):
        _logging.info(f"Telegram: {resultado_tg['detalle']}")
    else:
        _logging.warning(f"Telegram falló: {resultado_tg.get('detalle')} | {resultado_tg.get('error')}")
    enviar_discord(html)

    # 16. Guardar en rama datos
    guardar_salida(contrato["correlativo"], contrato)

    # 17. Finalizar
    panel.finalizar()
    print(f"Tiempo de ejecución: {panel.resumen()['tiempo_ejecucion']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
