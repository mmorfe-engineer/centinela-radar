#!/usr/bin/env python3
"""
RADAR - Validación del universo de medios
==========================================

Script para validar todos los feeds RSS de config/radar_medios.json.

Funcionamiento:
1. Recorre cada medio en radar_medios.json
2. Si rss_url es null, intenta descubrir el feed probando:
   - {url}/rss
   - {url}/feed
   - {url}/arc/outboundfeeds/rss
   - <link rel='alternate' type='application/rss+xml'> en la portada
3. Genera reporte estructurado con estados: OK, CORREGIDO, SIN_FEED, ERROR
4. Opcionalmente actualiza radar_medios.json con los feeds descubiertos

Uso:
    python radar/validar_medios.py --dry-run          # Solo validar, no modificar
    python radar/validar_medios.py --update           # Validar y actualizar config
    python radar/validar_medios.py --verbose          # Mostrar detalles
"""

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import feedparser
import requests

# Configuración
TIMEOUT_SEGUNDOS = 20
REINTENTOS = 2
USER_AGENT = "CENTINELA-RADAR/1.0 (Monitoreo de prensa; +https://github.com/mmorfe-engineer/centinela-radar)"


def obtener_con_headers() -> Dict[str, str]:
    """Headers para requests"""
    return {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }


def es_url_valida(url: str) -> bool:
    """Verificar si una URL tiene formato válido"""
    try:
        resultado = urlparse(url)
        return all([resultado.scheme in ("http", "https"), resultado.netloc])
    except (ValueError, AttributeError):
        return False


def fetch_url(url: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Fetch una URL con timeout y reintentos.
    
    Returns:
        (exito, contenido, error)
    """
    headers = obtener_con_headers()
    
    for intento in range(REINTENTOS):
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=TIMEOUT_SEGUNDOS,
                allow_redirects=True
            )
            # Paywall o bloqueo: no intentar reparsear
            if response.status_code in (403, 402, 429):
                return False, None, f"Bloqueado: HTTP {response.status_code}"
            
            if response.status_code == 200:
                return True, response.text, None
            elif response.status_code >= 400:
                return False, None, f"HTTP {response.status_code}"
            else:
                time.sleep(2)  # Esperar antes de reintentar
        except requests.exceptions.Timeout:
            if intento == REINTENTOS - 1:
                return False, None, "Timeout"
            time.sleep(2)
        except requests.exceptions.RequestException as e:
            if intento == REINTENTOS - 1:
                return False, None, str(e)
            time.sleep(2)
    
    return False, None, "Error desconocido"


def probar_feed_rss(url: str) -> Tuple[bool, str, Optional[str]]:
    """
    Probar si una URL es un feed RSS válido.
    
    Returns:
        (es_feed, url_normalizada, error)
    """
    if not es_url_valida(url):
        return False, url, "URL inválida"
    
    exito, contenido, error = fetch_url(url)
    
    if not exito:
        return False, url, error
    
    try:
        feed = feedparser.parse(contenido)
        # Verificar si tiene entradas (es un feed válido)
        if len(feed.get("entries", [])) > 0 or feed.get("version"):
            return True, url, None
        else:
            return False, url, "No es un feed válido (sin entradas)"
    except Exception as e:
        return False, url, f"Error parseando feed: {e}"


def extraer_rss_de_html(html: str, base_url: str) -> Optional[str]:
    """
    Extraer URL de RSS de la página HTML usando <link rel='alternate'>
    """
    try:
        import re
        # Buscar todos los link tags
        pattern = re.compile(r'<link\s+([^>]*)>', re.IGNORECASE)
        link_tags = pattern.findall(html)
        
        for tag_content in link_tags:
            # Extraer href y type del tag
            href_match = re.search(r'href=["\']([^"\']+)["\']', tag_content, re.IGNORECASE)
            type_match = re.search(r'type=["\']([^"\']+)["\']', tag_content, re.IGNORECASE)
            
            if href_match and type_match:
                href = href_match.group(1)
                link_type = type_match.group(1)
                # Verificar si es un feed
                if "rss" in link_type.lower() or "atom" in link_type.lower():
                    if not es_url_valida(href):
                        href = urljoin(base_url, href)
                    return href
        
        # También probar con feedparser
        try:
            feed = feedparser.parse(html)
            # Buscar en feed.links
            for link in feed.get("links", []):
                link_type = link.get("type", "")
                if "rss" in link_type.lower() or "atom" in link_type.lower():
                    rss_url = link.get("href")
                    if rss_url:
                        if not es_url_valida(rss_url):
                            rss_url = urljoin(base_url, rss_url)
                        return rss_url
        except Exception:
            pass
            
    except Exception:
        pass
    
    return None


def descubrir_feed(url_portada: str) -> Tuple[Optional[str], str]:
    """
    Intentar descubrir el feed RSS de una portada.
    
    Prueba:
    1. /rss
    2. /feed
    3. /arc/outboundfeeds/rss
    4. Extraer de <link rel='alternate'> en la portada
    
    Returns:
        (rss_url, status) donde status es: "OK", "SIN_FEED", "ERROR"
    """
    if not es_url_valida(url_portada):
        return None, "ERROR"
    
    # Normalizar URL base
    parsed = urlparse(url_portada)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    # Listas de sufijos a probar
    sufijos = ["/rss", "/feed", "/arc/outboundfeeds/rss"]
    
    for sufijo in sufijos:
        url_candidata = f"{base_url}{sufijo}"
        es_feed, url_normalizada, _ = probar_feed_rss(url_candidata)
        if es_feed:
            return url_normalizada, "OK"
    
    # Intentar extraer de la portada
    exito, html, error = fetch_url(url_portada)
    if exito and html:
        rss_url = extraer_rss_de_html(html, base_url)
        if rss_url:
            # Verificar que el RSS encontrado es válido
            es_feed, url_final, _ = probar_feed_rss(rss_url)
            if es_feed:
                return url_final, "OK"
    
    # Si no se encontró feed
    return None, "SIN_FEED"


def validar_medio(medio: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validar un solo medio.
    
    Returns:
        Dict con: id, rss_url_original, rss_url_validado, status, error
    """
    medio_id = medio.get("id", "desconocido")
    rss_url = medio.get("rss_url")
    portada_url = medio.get("url") or medio.get("portada_url")
    
    # Si ya tiene rss_url, validarlo
    if rss_url:
        if rss_url is None:
            # Intentar descubrir
            rss_descubierto, status = descubrir_feed(portada_url)
            if rss_descubierto:
                return {
                    "id": medio_id,
                    "rss_url_original": None,
                    "rss_url_validado": rss_descubierto,
                    "status": "CORREGIDO",
                    "error": None
                }
            else:
                return {
                    "id": medio_id,
                    "rss_url_original": None,
                    "rss_url_validado": None,
                    "status": "SIN_FEED",
                    "error": None
                }
        else:
            # Validar el feed existente
            es_feed, url_normalizada, error = probar_feed_rss(rss_url)
            if es_feed:
                return {
                    "id": medio_id,
                    "rss_url_original": rss_url,
                    "rss_url_validado": url_normalizada,
                    "status": "OK",
                    "error": None
                }
            else:
                # Intentar descubrir
                rss_descubierto, status_desc = descubrir_feed(portada_url)
                if rss_descubierto:
                    return {
                        "id": medio_id,
                        "rss_url_original": rss_url,
                        "rss_url_validado": rss_descubierto,
                        "status": "CORREGIDO",
                        "error": f"Original inválido: {error}"
                    }
                else:
                    return {
                        "id": medio_id,
                        "rss_url_original": rss_url,
                        "rss_url_validado": None,
                        "status": "ERROR",
                        "error": error
                    }
    else:
        # No tiene rss_url, intentar descubrir
        rss_descubierto, status = descubrir_feed(portada_url)
        if rss_descubierto:
            return {
                "id": medio_id,
                "rss_url_original": None,
                "rss_url_validado": rss_descubierto,
                "status": "CORREGIDO",
                "error": None
            }
        else:
            return {
                "id": medio_id,
                "rss_url_original": None,
                "rss_url_validado": None,
                "status": "SIN_FEED",
                "error": None
            }


def validar_todos_medios(medios_config: List[Dict[str, Any]], verbose: bool = False) -> Dict[str, Any]:
    """
    Validar todos los medios del config.
    
    Returns:
        Dict con:
        - total: int
        - ok: List[Dict]
        - corregido: List[Dict]
        - sin_feed: List[Dict]
        - errores: List[Dict]
        - resumen: Dict[str, int]
    """
    resultados = {
        "total": len(medios_config),
        "ok": [],
        "corregido": [],
        "sin_feed": [],
        "errores": [],
        "resumen": {
            "ok": 0,
            "corregido": 0,
            "sin_feed": 0,
            "errores": 0
        }
    }
    
    for i, medio in enumerate(medios_config, 1):
        if verbose:
            print(f"[{i}/{len(medios_config)}] Validando {medio.get('id', 'desconocido')}...", end=" ")
        
        resultado = validar_medio(medio)
        
        status = resultado["status"]
        if status == "OK":
            resultados["ok"].append(resultado)
        elif status == "CORREGIDO":
            resultados["corregido"].append(resultado)
        elif status == "SIN_FEED":
            resultados["sin_feed"].append(resultado)
        else:
            resultados["errores"].append(resultado)
        
        # Asegurar que la clave existe
        clave = status.lower()
        if clave not in resultados["resumen"]:
            resultados["resumen"][clave] = 0
        resultados["resumen"][clave] += 1
        
        if verbose:
            print(f"{status}")
    
    return resultados


def actualizar_config_medios(config_path: str, resultados: Dict[str, Any]) -> bool:
    """
    Actualizar radar_medios.json con los feeds validados.
    
    Returns:
        True si se actualizó correctamente
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # Crear mapeo de id -> rss_url_validado
        rss_updates = {}
        for resultado in resultados["ok"]:
            rss_updates[resultado["id"]] = resultado["rss_url_validado"]
        for resultado in resultados["corregido"]:
            rss_updates[resultado["id"]] = resultado["rss_url_validado"]
        # sin_feed y errores mantienen su rss_url (o null)
        
        # Actualizar medios
        for medio in config.get("medios", []):
            if medio["id"] in rss_updates:
                medio["rss_url"] = rss_updates[medio["id"]]
        
        # Guardar
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"Error actualizando config: {e}")
        return False


def generar_reporte(resultados: Dict[str, Any]) -> str:
    """Generar reporte en texto"""
    lines = []
    lines.append("=" * 70)
    lines.append("REPORTE DE VALIDACIÓN DE MEDIOS - RADAR")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"Total de medios: {resultados['total']}")
    lines.append(f"Resumen: {json.dumps(resultados['resumen'], indent=2)}")
    lines.append("")
    
    # OK
    if resultados["ok"]:
        lines.append("-" * 70)
        lines.append("🟢 FEEDS OK:")
        lines.append("-" * 70)
        for r in resultados["ok"]:
            lines.append(f"  {r['id']:20} -> {r['rss_url_validado']}")
        lines.append("")
    
    # Corregido
    if resultados["corregido"]:
        lines.append("-" * 70)
        lines.append("🟡 FEEDS CORREGIDOS:")
        lines.append("-" * 70)
        for r in resultados["corregido"]:
            lines.append(f"  {r['id']:20} -> {r['rss_url_validado']}")
        lines.append("")
    
    # Sin feed
    if resultados["sin_feed"]:
        lines.append("-" * 70)
        lines.append("⚪ SIN FEED (usarán capa 2 Perplexity):")
        lines.append("-" * 70)
        for r in resultados["sin_feed"]:
            lines.append(f"  {r['id']:20}")
        lines.append("")
    
    # Errores
    if resultados["errores"]:
        lines.append("-" * 70)
        lines.append("❌ ERRORES:")
        lines.append("-" * 70)
        for r in resultados["errores"]:
            lines.append(f"  {r['id']:20} -> {r['error']}")
        lines.append("")
    
    lines.append("=" * 70)
    return "\n".join(lines)


def guardar_reporte_json(resultados: Dict[str, Any], output_path: str) -> bool:
    """Guardar reporte en JSON"""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(resultados, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error guardando reporte: {e}")
        return False


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description="Validar feeds RSS de radar_medios.json")
    parser.add_argument("--dry-run", action="store_true", help="Solo validar, no actualizar config")
    parser.add_argument("--update", action="store_true", help="Validar y actualizar config")
    parser.add_argument("--verbose", action="store_true", help="Mostrar detalles")
    parser.add_argument("--output", type=str, default="reporte_validacion_medios.json", 
                        help="Archivo de salida del reporte JSON")
    args = parser.parse_args()
    
    # Cargar config
    config_path = Path("config/radar_medios.json")
    if not config_path.exists():
        print(f"Error: {config_path} no encontrado")
        return 1
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    medios = config.get("medios", [])
    
    print(f"Validando {len(medios)} medios...")
    print()
    
    # Validar todos
    resultados = validar_todos_medios(medios, verbose=args.verbose)
    
    # Mostrar reporte
    reporte_texto = generar_reporte(resultados)
    print(reporte_texto)
    
    # Guardar reporte JSON
    guardar_reporte_json(resultados, args.output)
    print(f"Reporte guardado en: {args.output}")
    
    # Actualizar config si --update
    if args.update:
        if actualizar_config_medios(str(config_path), resultados):
            print("Config actualizado: config/radar_medios.json")
        else:
            print("Error actualizando config")
            return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
