#!/usr/bin/env python3
"""
RADAR - Top 10 Global
=====================

Agrupación por embeddings multilingües y ranking del Top 10 Global.

Funciones principales:
- agrupar_por_embeddings(): Agrupar titulares usando embeddings (NIM)
- generar_top10_global(): Generar el Top 10 Global a partir de todos los titulares

Reglas:
- Agrupación por similitud coseno (umbral: 0.78)
- Ranking: repetición cross-medio × diversidad regional × prominencia × authority_score
- Marcar si evento venezolano está en Top 10
"""

import json
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from core.llm import LLMClient
from core.normalizacion import normalizar_titulo


# Umbral de similitud coseno para agrupar eventos
UMBRAL_COSENO = 0.78

# Palabras clave que indican temas NO relevantes para el RADAR
PALABRAS_IRRELEVANTES = {
    "deporte", "deportes", "futbol", "fútbol", "beisbol", "básquet",
    "tenis", "golf", "atletismo", "olimpico", "jolímpico", "mundial",
    "cultura", "arte", "música", "cine", "teatro", "literatura",
    "entretenimiento", "espectaculo", "espectáculo", "famoso", "celebridad",
    "horoscopo", "farandula", "farándula"
}


def es_grupo_relevante(grupo: Dict[str, Any]) -> bool:
    """
    Determinar si un grupo de titulares es relevante para el RADAR.
    Excluye grupos con temas genéricos como deportes o cultura.
    """
    # Si el grupo es venezolano, SIEMPRE incluirlo
    if grupo.get("es_venezolano", False):
        return True

    titulares = grupo.get("titulares", [])
    if not titulares:
        return True

    # titulo_canonico NO existe aún en el grupo al momento del filtro;
    # se usa el título más corto de los titulares como representativo.
    titulo_repr = min((t.get("titulo", "") for t in titulares), key=len)
    titulo_norm = normalizar_titulo(titulo_repr)

    for palabra in PALABRAS_IRRELEVANTES:
        if palabra in titulo_norm:
            return False

    return True


def generar_embedding(texto: str, cliente_llm: Optional[LLMClient] = None) -> List[float]:
    """
    Generar embedding para un texto usando NIM (o el cliente LLM configurado).
    
    Args:
        texto: Texto a embeddizar
        cliente_llm: Cliente LLM opcional (para testing)
        
    Returns:
        Lista de floats representando el embedding
    """
    if texto is None:
        return [0.0] * 384
    
    # Normalizar texto: minúsculas, sin espacios extra
    texto_norm = texto.lower().strip()
    
    if not texto_norm:
        # Para textos vacíos, devolver embedding cero
        return [0.0] * 384
    
    # Usar NIM para embeddings multilingües
    # Por ahora, simulamos con un embedding basado en hash (en producción, usar NIM)
    # Esto es un placeholder que será reemplazado por la integración real con NIM
    try:
        # Generar un embedding determinista basado en el hash del texto
        # En producción, esto debe ser reemplazado por una llamada a NIM
        from core.normalizacion import normalizar_titulo
        texto_norm = normalizar_titulo(texto)
        texto_hash = hash(texto_norm)
        
        # Crear embedding simulado (384 dimensiones como NIM)
        np.random.seed(texto_hash % (2**32))
        embedding = np.random.randn(384).tolist()
        
        # Normalizar a longitud 1
        norm = (sum(x**2 for x in embedding)) ** 0.5
        if norm > 0:
            embedding = [x / norm for x in embedding]
        
        return embedding
        
    except Exception as e:
        # Fail loud
        raise RuntimeError(f"Error generando embedding para '{texto}': {e}")


def similitud_coseno(emb1: List[float], emb2: List[float]) -> float:
    """
    Calcular similitud coseno entre dos embeddings.
    
    Args:
        emb1: Primer embedding
        emb2: Segundo embedding
        
    Returns:
        Similitud coseno (0.0 a 1.0)
    """
    try:
        # Asegurar que son numpy arrays
        v1 = np.array(emb1)
        v2 = np.array(emb2)
        
        # Normalizar vectores
        v1_norm = v1 / (np.linalg.norm(v1) + 1e-9)
        v2_norm = v2 / (np.linalg.norm(v2) + 1e-9)
        
        # Producto punto
        dot_product = np.dot(v1_norm, v2_norm)
        
        # Clampar entre -1 y 1
        return float(np.clip(dot_product, -1.0, 1.0))
        
    except Exception as e:
        raise RuntimeError(f"Error calculando similitud coseno: {e}")


def agrupar_por_embeddings(
    titulares: List[Dict[str, Any]],
    umbral: float = UMBRAL_COSENO
) -> List[Dict[str, Any]]:
    """
    Agrupar titulares por similitud de embeddings.
    
    Args:
        titulares: Lista de dicts con {"titulo": str, "medio_id": str, "region": str, ...}
        umbral: Umbral de similitud coseno para agrupar (default: 0.78)
        
    Returns:
        Lista de grupos, donde cada grupo es:
        {
            "evento_id": str,
            "titulares": [dicts],
            "embedding_promedio": List[float],
            "tamanio": int,
            "regiones": set[str],
            "medio_ids": set[str]
        }
    """
    if not titulares:
        return []
    
    grupos = []
    
    try:
        # Generar embeddings para todos los titulares
        embeddings = []
        for t in titulares:
            titulo = t.get("titulo", "")
            embedding = generar_embedding(titulo)
            embeddings.append({
                "titulo": titulo,
                "medio_id": t.get("medio_id", "desconocido"),
                "region": t.get("region", "desconocido"),
                "url": t.get("url", ""),
                "fecha": t.get("fecha"),
                "embedding": embedding,
                "indice": len(embeddings)
            })
        
        # Algoritmo de clustering greedy
        usados = set()
        
        for i, e1 in enumerate(embeddings):
            if i in usados:
                continue
            
            # Crear nuevo grupo
            grupo = {
                "evento_id": f"evento_{i}",
                "titulares": [{
                    "titulo": e1["titulo"],
                    "medio_id": e1["medio_id"],
                    "region": e1["region"],
                    "url": e1["url"],
                    "fecha": e1["fecha"]
                }],
                "embeddings": [e1["embedding"]],
                "regiones": {e1["region"]},
                "medio_ids": {e1["medio_id"]},
                "tamanio": 1
            }
            usados.add(i)
            
            # Comparar con el resto
            for j, e2 in enumerate(embeddings):
                if j in usados:
                    continue
                
                similitud = similitud_coseno(e1["embedding"], e2["embedding"])
                
                if similitud >= umbral:
                    grupo["titulares"].append({
                        "titulo": e2["titulo"],
                        "medio_id": e2["medio_id"],
                        "region": e2["region"],
                        "url": e2["url"],
                        "fecha": e2["fecha"]
                    })
                    grupo["embeddings"].append(e2["embedding"])
                    grupo["regiones"].add(e2["region"])
                    grupo["medio_ids"].add(e2["medio_id"])
                    grupo["tamanio"] += 1
                    usados.add(j)
            
            # Calcular embedding promedio del grupo
            emb_prom = np.mean(grupo["embeddings"], axis=0).tolist()
            grupo["embedding_promedio"] = emb_prom
            
            grupos.append(grupo)
        
        # Ordenar por tamaño (mayor primero)
        grupos.sort(key=lambda g: g["tamanio"], reverse=True)
        
        return grupos
        
    except Exception as e:
        raise RuntimeError(f"Error en agrupar_por_embeddings: {e}")


def calcular_prominencia_media(grupo: Dict[str, Any]) -> float:
    """
    Calcular prominencia media de un grupo de titulares.
    
    Args:
        grupo: Grupo de titulares
        
    Returns:
        Prominencia media (0.0 a 1.0)
    """
    prominencias = {
        "portada": 1.0,
        "apertura_seccion": 0.8,
        "interior": 0.5,
        "": 0.3  # Default
    }
    
    total = 0.0
    count = 0
    
    for t in grupo.get("titulares", []):
        prominencia = t.get("prominencia", "")
        total += prominencias.get(prominencia.lower(), 0.3)
        count += 1
    
    return total / count if count > 0 else 0.3


def calcular_authority_score_promedio(
    grupo: Dict[str, Any],
    medios_config: List[Dict[str, Any]]
) -> float:
    """
    Calcular authority score promedio de un grupo.
    
    Args:
        grupo: Grupo de titulares
        medios_config: Configuración de medios
        
    Returns:
        Authority score promedio
    """
    # Crear mapeo de medio_id -> authority_score
    authority_map = {}
    for medio in medios_config:
        authority_map[medio.get("id", "")] = medio.get("authority_score", 0.5)
    
    total = 0.0
    count = 0
    
    for t in grupo.get("titulares", []):
        medio_id = t.get("medio_id", "")
        score = authority_map.get(medio_id, 0.5)
        total += score
        count += 1
    
    return total / count if count > 0 else 0.5


def generar_top10_global(
    todos_titulares: List[Dict[str, Any]],
    medios_config: List[Dict[str, Any]],
    umbral: float = UMBRAL_COSENO
) -> List[Dict[str, Any]]:
    """
    Generar el Top 10 Global a partir de todos los titulares de la capa determinista.
    
    Args:
        todos_titulares: Todos los titulares descargados (de todos los medios)
        medios_config: Configuración de medios
        umbral: Umbral de similitud coseno
        
    Returns:
        Lista de los Top 10 eventos, ordenados por ranking:
        [
            {
                "rank": int,
                "evento_id": str,
                "titulo_canonico": str,
                "resumen": str,
                "cuenta_medios": int,
                "cuenta_total": int,
                "regiones": [str],
                "titulares": [dict],
                "es_venezolano": bool,
                "etiqueta_especial": str | None
            },
            ...
        ]
    """
    try:
        # Agrupar titulares
        grupos = agrupar_por_embeddings(todos_titulares, umbral)
        
        # Si no hay grupos, volver vacío
        if not grupos:
            return []
        
        # Calcular score de ranking para cada grupo
        for grupo in grupos:
            # Repetición cross-medio
            repeticion = len(grupo["medio_ids"])
            
            # Diversidad regional
            diversidad_regional = len(grupo["regiones"])
            
            # Prominencia media
            prominencia = calcular_prominencia_media(grupo)
            
            # Authority score promedio
            authority = calcular_authority_score_promedio(grupo, medios_config)
            
            # Score compuesto
            score = repeticion * diversidad_regional * prominencia * authority
            
            # Determinar si es venezolano
            es_venezolano = False
            for t in grupo["titulares"]:
                titulo_norm = normalizar_titulo(t["titulo"])
                if "venezuela" in titulo_norm:
                    es_venezolano = True
                    break
            
            # Guardar datos
            grupo["repeticion_cross_medio"] = repeticion
            grupo["diversidad_regional"] = diversidad_regional
            grupo["prominencia_media"] = prominencia
            grupo["authority_score_promedio"] = authority
            grupo["score"] = score
            grupo["es_venezolano"] = es_venezolano
        
        # Ordenar por score descendente
        grupos.sort(key=lambda g: g["score"], reverse=True)
        
        # Filtrar grupos relevantes (excluir deportes, cultura, etc.)
        grupos_relevantes = [g for g in grupos if es_grupo_relevante(g)]
        
        # Tomar Top 10 de los relevantes
        top10 = grupos_relevantes[:10]
        
        # Formatear resultado
        resultado = []
        for idx, grupo in enumerate(top10, 1):
            # Título canónico: el más corto o el primero
            titulo_canonico = min(
                [t["titulo"] for t in grupo["titulares"]],
                key=len
            )
            
            # Resumen: contadores
            contraste_str = f"📰 {grupo['tamanio']}/{len(todos_titulares)} titulares · " \
                           f"{len(grupo['regiones'])} regiones · " \
                           f"{len(grupo['medio_ids'])} medios"
            
            # Etiqueta especial
            etiqueta_especial = None
            if grupo["es_venezolano"]:
                etiqueta_especial = "🔥 Venezuela en agenda global"
            
            resultado.append({
                "rank": idx,
                "evento_id": grupo["evento_id"],
                "titulo_canonico": titulo_canonico,
                "resumen": contraste_str,
                "cuenta_medios": len(grupo["medio_ids"]),
                "cuenta_total": grupo["tamanio"],
                "regiones": sorted(list(grupo["regiones"])),
                "titulares": grupo["titulares"],
                "es_venezolano": grupo["es_venezolano"],
                "etiqueta_especial": etiqueta_especial
            })
        
        return resultado
        
    except Exception as e:
        raise RuntimeError(f"Error generando Top 10 Global: {e}")


def extraer_titulares_para_top10(
    resultados_fetch: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Extraer todos los titulares de los resultados de fetch para el Top 10.
    
    Args:
        resultados_fetch: Resultado de fetch_todos_medios()
        
    Returns:
        Lista de titulares con medio_id y región
    """
    todos_titulares = []
    
    for resultado in resultados_fetch.get("medios", []):
        medio_id = resultado.get("id", "desconocido")
        for titular in resultado.get("titulares", []):
            todos_titulares.append({
                "titulo": titular.get("titulo", ""),
                "url": titular.get("url", ""),
                "fecha": titular.get("fecha"),
                "medio_id": medio_id,
                "fuente": "rss" if resultado.get("es_rss") else "portada"
            })
    
    return todos_titulares
