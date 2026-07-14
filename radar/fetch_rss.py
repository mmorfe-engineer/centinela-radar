#!/usr/bin/env python3
"""
RADAR - Capa determinista: Fetch RSS/portada
=============================================

Módulo para descargar y parsear feeds RSS y portadas de medios.

Funciones principales:
- fetch_medio(): Descargar RSS o portada de un solo medio
- fetch_todos_medios(): Descargar todos los medios del config
- parse_feed(): Parsear contenido RSS
- parse_portada(): Extraer titulares de una portada HTML

Reglas:
- Timeout: 20 segundos por medio
- Reintentos: 2
- Prohibido evadir paywalls (403/402/429 = no verificable)
- Conservar TODOS los titulares (matcheen o no) -> insumo Top 10 Global
"""

import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import feedparser
import requests

from core.normalizacion import normalizar_titulo, normalizar_texto

# Configuración
TIMEOUT_SEGUNDOS = 20
MAX_REINTENTOS = 2
USER_AGENT = "CENTINELA-RADAR/1.0 (Monitoreo de prensa; +https://github.com/mmorfe-engineer/centinela-radar)"


def obtener_headers() -> Dict[str, str]:
    """Headers estándar para requests"""
    return {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,es;q=0.9",
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
    
    Args:
        url: URL a fetch
        
    Returns:
        Tuple[exito: bool, contenido: str | None, error: str | None]
        
    Raises:
        Ninguna - siempre retira (fail loud en el return)
    """
    headers = obtener_headers()
    
    for intento in range(MAX_REINTENTOS):
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=TIMEOUT_SEGUNDOS,
                allow_redirects=True
            )
            
            # Paywall o bloqueo: NO intentar reparsear
            if response.status_code in (403, 402, 429):
                return False, None, f"Bloqueado: HTTP {response.status_code}"
            
            if response.status_code == 200:
                return True, response.text, None
            elif response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}"
                if intento < MAX_REINTENTOS - 1:
                    time.sleep(2)
                    continue
                return False, None, error_msg
            else:
                if intento < MAX_REINTENTOS - 1:
                    time.sleep(2)
                    continue
                return False, None, f"HTTP {response.status_code}"
                
        except requests.exceptions.Timeout:
            if intento == MAX_REINTENTOS - 1:
                return False, None, "Timeout después de 2 reintentos"
            time.sleep(2)
        except requests.exceptions.RequestException as e:
            if intento == MAX_REINTENTOS - 1:
                return False, None, str(e)
            time.sleep(2)
    
    return False, None, "Error desconocido después de reintentos"


def parse_feed(contenido: str, url_base: str, medio_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Parsear contenido RSS/Atom y extraer titulares.

    Args:
        contenido: Contenido del feed en texto
        url_base: URL base para resolver URLs relativas
        medio_id: ID del medio para asociar cada titular

    Returns:
        Lista de dicts: [{"titulo": str, "url": str, "fecha": str | None, "medio_id": str | None}, ...]
        Si el feed es inválido, vuelve lista vacía
    """
    try:
        feed = feedparser.parse(contenido)

        titulares = []
        for entry in feed.get("entries", []):
            titulo = entry.get("title", "")
            if not titulo:
                continue

            # Obtener URL
            url = entry.get("link", "")
            if not url:
                url = entry.get("id", "")

            # Resolver URL relativa
            if url and not es_url_valida(url):
                url = urljoin(url_base, url)

            # Obtener fecha
            fecha = None
            if hasattr(entry, "published_parsed"):
                # Convertir a ISO format
                import datetime
                try:
                    ts = entry.published_parsed
                    fecha = datetime.datetime(*ts[:6]).isoformat()
                except (ValueError, TypeError):
                    pass

            titulares.append({
                "titulo": titulo.strip(),
                "url": url,
                "fecha": fecha,
                "medio_id": medio_id
            })

        return titulares

    except Exception as e:
        # Log detallado (fail loud)
        import logging
        logging.error(f"Error parseando feed: {e}")
        return []


def parse_portada(html: str, url_base: str, medio_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extraer titulares de una portada HTML.

    Estrategia:
    1. Usar feedparser (intenta extraer titulares de HTML)
    2. Buscar <h1>, <h2>, <h3> tags
    3. Buscar <a> tags con clases como "titulo", "headline", "title"

    Args:
        html: Contenido HTML
        url_base: URL base para resolver URLs relativas
        medio_id: ID del medio para asociar cada titular

    Returns:
        Lista de dicts con titulares y URLs
    """
    import re

    titulares = []

    try:
        # Estrategia 1: Usar feedparser (intenta extraer titulares de HTML)
        feed = feedparser.parse(html)
        for entry in feed.get("entries", []):
            titulo = entry.get("title", "")
            if not titulo:
                continue
            url = entry.get("link", "")
            if url and not es_url_valida(url):
                url = urljoin(url_base, url)

            fecha = None
            if hasattr(entry, "published_parsed"):
                import datetime
                try:
                    ts = entry.published_parsed
                    fecha = datetime.datetime(*ts[:6]).isoformat()
                except (ValueError, TypeError):
                    pass

            titulares.append({
                "titulo": titulo.strip(),
                "url": url,
                "fecha": fecha,
                "medio_id": medio_id
            })

        if titulares:
            return titulares

        # Estrategia 2: Buscar etiquetas <h1>, <h2>, <h3>
        h_pattern = re.compile(
            r'<(h[1-3])\b[^>]*>(.*?)</\1>',
            re.IGNORECASE | re.DOTALL
        )
        for match in h_pattern.findall(html):
            level, text = match[0], match[1]
            text = re.sub(r'<[^>]+>', '', text).strip()
            if len(text) > 5:
                titulares.append({
                    "titulo": text,
                    "url": None,
                    "fecha": None,
                    "medio_id": medio_id
                })

        # Estrategia 3: Buscar links con clases comunes de titulares
        link_pattern = re.compile(
            r'<a\s+[^>]*(class=["\'][^"\']*(headline|titulo|title|nota|article)[^"\']*["\'])[^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL
        )
        for match in link_pattern.findall(html):
            # match[2] es el contenido del link (grupo 3), no match[1] (palabra clave de la clase)
            text = re.sub(r'<[^>]+>', '', match[2]).strip()
            if len(text) > 5:
                titulares.append({
                    "titulo": text,
                    "url": None,
                    "fecha": None,
                    "medio_id": medio_id
                })

        return titulares

    except Exception as e:
        import logging
        logging.error(f"Error parseando portada: {e}")
        return []


def fetch_medio(medio: Dict[str, Any], timeout: int = TIMEOUT_SEGUNDOS, 
                 max_reintentos: int = MAX_REINTENTOS) -> Dict[str, Any]:
    """
    Fetch RSS o portada de un medio.
    
    Lógica:
    1. Si rss_url existe → intentar fetch RSS
    2. Si RSS falla o no existe → intentar fetch portada
    3. Parsear el contenido obtenido
    
    Args:
        medio: Dict con id, nombre, rss_url, url
        timeout: Timeout en segundos
        max_reintentos: Máximo de reintentos
        
    Returns:
        Dict con:
        - id: str
        - exito: bool
        - url_usada: str
        - titulares: List[Dict]
        - error: str | None
        - es_rss: bool
        - es_portada: bool
    """
    medio_id = medio.get("id", "desconocido")
    rss_url = medio.get("rss_url")
    portada_url = medio.get("url") or medio.get("portada_url")
    
    # Intentar RSS primero si existe
    if rss_url and es_url_valida(rss_url):
        exito, contenido, error = fetch_url(rss_url)
        if exito and contenido:
            titulares = parse_feed(contenido, rss_url, medio_id)
            return {
                "id": medio_id,
                "exito": True,
                "url_usada": rss_url,
                "titulares": titulares,
                "error": None,
                "es_rss": True,
                "es_portada": False
            }

    # RSS falló o no existe, intentar portada
    if portada_url and es_url_valida(portada_url):
        exito, contenido, error = fetch_url(portada_url)
        if exito and contenido:
            # Intentar parsear como feed primero (algunas portadas devuelven RSS)
            titulares = parse_feed(contenido, portada_url, medio_id)
            if not titulares:
                # Parsear como HTML
                titulares = parse_portada(contenido, portada_url, medio_id)
            return {
                "id": medio_id,
                "exito": True,
                "url_usada": portada_url,
                "titulares": titulares,
                "error": None,
                "es_rss": False,
                "es_portada": True
            }
        else:
            # Portada también falló
            return {
                "id": medio_id,
                "exito": False,
                "url_usada": portada_url,
                "titulares": [],
                "error": error,
                "es_rss": False,
                "es_portada": True
            }
    
    # No hay URLs válidas
    return {
        "id": medio_id,
        "exito": False,
        "url_usada": None,
        "titulares": [],
        "error": "No hay URLs válidas (rss_url o url)",
        "es_rss": False,
        "es_portada": False
    }


def fetch_todos_medios(medios_config: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Fetch todos los medios del configuración.
    
    Args:
        medios_config: Lista de dicts de medios
        
    Returns:
        Dict con:
        - medios: [resultado de fetch_medio para cada medio]
        - titulares_todos: [todos los titulares descargados]
        - errores: [medios que fallaron]
    """
    resultados_medios = []
    todos_titulares = []
    errores = []
    
    for medio in medios_config:
        resultado = fetch_medio(medio)
        resultados_medios.append(resultado)
        
        if resultado["exito"]:
            todos_titulares.extend(resultado["titulares"])
        else:
            errores.append(resultado)
    
    return {
        "medios": resultados_medios,
        "titulares_todos": todos_titulares,
        "errores": errores
    }
