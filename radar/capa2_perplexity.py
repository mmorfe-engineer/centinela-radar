#!/usr/bin/env python3
"""
RADAR - Capa 2: Búsqueda con Perplexity
=======================================

Funciones para realizar búsquedas en Perplexity cuando la capa determinista
(RSS/portada) no produce resultados o falla.

Funciones principales:
- buscar_con_perplexity(): Ejecutar consulta Perplexity para una región
- ejecutar_capa2(): Ejecutar todas las consultas de Perplexity

Reglas:
- Usar el cliente LLM de core con accion="buscar"
- Max 8-10 llamadas por corrida
- Respetar presupuesto de reintentos
- No evadir paywalls
"""

import json
import logging
from typing import Any, Dict, List, Optional

from core.llm import LLMClient


# Configuración
MAX_CALLS = 10
MODELO_POR_DEFECTO = "sonar-pro"


def crear_prompt_perplexity(
    region: str,
    query: str,
    medios_ids: List[str],
    conectores: List[str]
) -> str:
    """
    Crear prompt para Perplexity con la consulta y el contexto.
    
    Args:
        region: Región a buscar
        query: Consulta de búsqueda
        medios_ids: Lista de IDs de medios para esta región
        conectores: Lista de conectores temáticos
        
    Returns:
        Prompt formateado
    """
    medios_str = ", ".join(medios_ids)
    conectores_str = "; ".join(conectores)
    
    prompt = f"""
Analiza cobertura de prensa sobre Venezuela (análisis de agenda mediática).

CONTEXTO:
- Regiones a cubrir: {region}
- Medios en estas regiones: {medios_str}
- Conectores temáticos relevantes: {conectores_str}

INSTRUCCIÓN:
Busca y analiza piezas de prensa que mencionen Venezuela directa o indirectamente 
mediante los conectores listados. Para cada hallazgo encontrado, devuelve UN OBJETO JSON 
con el siguiente schema:

{{
    "hallazgos": [
        {{
            "titulo": str (título exacto),
            "url": str (URL completa),
            "medio_id": str (de la lista: {medios_str}),
            "fecha": str (ISO 8601 o vacío),
            "tipo_pieza": "portada"|"editorial"|"opinion"|"nota"|"analisis",
            "resumen_1_frase": str (máximo 50 palabras),
            "conectores_activados": [str] (de la lista)
        }}
    ],
    "medios_sin_cobertura": [str] (medios de la lista que NO publicaron nada)
}}

REGLAS:
1. Incluye SOLO piezas de los medios de la lista dada.
2. Para cada medio de la lista: o aparece en hallazgos o en medios_sin_cobertura.
3. Si no encuentras nada sobre Venezuela en un medio, decláralo en medios_sin_cobertura.
4. Nunca inventes piezas o datos.
5. Usa el idioma del medio (si es español, responde en español; inglés, inglés; etc.).
6. Citas deben ser <=25 palabras.
7. No intentes evadir paywalls.

Ejecuta la búsqueda: {query}
"""
    
    return prompt.strip()


def parsear_respuesta_perplexity(
    respuesta: str,
    medios_ids: List[str]
) -> Dict[str, Any]:
    """
    Parsear la respuesta de Perplexity al schema esperado.
    
    Args:
        respuesta: Texto de la respuesta
        medios_ids: Lista de IDs de medios esperados
        
    Returns:
        Dict con {"hallazgos": [...], "medios_sin_cobertura": [...]}
    """
    resultado = {
        "hallazgos": [],
        "medios_sin_cobertura": []
    }
    
    try:
        # Intentar parsear como JSON primero
        if respuesta.strip().startswith("{"):
            data = json.loads(respuesta)
            resultado["hallazgos"] = data.get("hallazgos", [])
            resultado["medios_sin_cobertura"] = data.get("medios_sin_cobertura", [])
        else:
            # Si no es JSON, intentamos extraer información
            # Esto es un fallback, no debería pasar con prompts bien diseñados
            logging.warning(f"Respuesta no es JSON: {respuesta[:200]}")
            
            # Extraer URLs
            import re
            urls = re.findall(r'https?://\S+', respuesta)
            
            # Por ahora, marcar todos como sin cobertura
            resultado["medios_sin_cobertura"] = medios_ids
    
    except json.JSONDecodeError as e:
        logging.error(f"Error parseando JSON: {e}")
        resultado["medios_sin_cobertura"] = medios_ids
    
    except Exception as e:
        logging.error(f"Error en parsear_respuesta_perplexity: {e}")
        resultado["medios_sin_cobertura"] = medios_ids
    
    # Verificar que todos los medios están contabilizados
    hallazgos_medios = {h.get("medio_id") for h in resultado["hallazgos"] if h.get("medio_id")}
    sin_cobertura = set(resultado["medios_sin_cobertura"])
    
    medios_faltantes = set(medios_ids) - hallazgos_medios - sin_cobertura
    if medios_faltantes:
        logging.warning(f"Medios no contabilizados: {medios_faltantes}")
        resultado["medios_sin_cobertura"].extend(list(medios_faltantes))
    
    return resultado


def buscar_con_perplexity(
    region: str,
    query: str,
    medios_ids: List[str],
    conectores: List[str],
    cliente_llm: Optional[LLMClient] = None
) -> Dict[str, Any]:
    """
    Ejecutar una consulta de Perplexity para una región.
    
    Args:
        region: Región a buscar
        query: Consulta de búsqueda
        medios_ids: Lista de IDs de medios para esta región
        conectores: Lista de conectores temáticos
        cliente_llm: Cliente LLM (opcional, por defecto crea uno nuevo)
        
    Returns:
        Dict con hallazgos y medios_sin_cobertura
    """
    # Crear cliente si no se proporciona
    if cliente_llm is None:
        cliente_llm = LLMClient()
    
    try:
        # Crear prompt
        prompt = crear_prompt_perplexity(region, query, medios_ids, conectores)
        
        # Ejecutar consulta con Perplexity
        respuesta = cliente_llm.completar(
            accion="buscar",
            prompt=prompt,
            modelo=MODELO_POR_DEFECTO,
            temp=0.1,
            max_tokens=3000
        )
        
        # Parsear respuesta
        return parsear_respuesta_perplexity(respuesta, medios_ids)
        
    except Exception as e:
        # Fail loud
        logging.error(f"Error en buscar_con_perplexity({region}): {e}")
        return {
            "hallazgos": [],
            "medios_sin_cobertura": medios_ids,
            "error": str(e)
        }


def ejecutar_capa2(
    consultas_config: List[Dict[str, Any]],
    medios_por_region: Dict[str, List[str]],
    conectores_tematicos: List[str],
    cliente_llm: Optional[LLMClient] = None
) -> Dict[str, Any]:
    """
    Ejecutar todas las consultas de la capa 2 (Perplexity).
    
    Args:
        consultas_config: Lista de consultas del config (reporte.json)
        medios_por_region: Dict mapeando región -> lista de medio_ids
        conectores_tematicos: Lista de todos los conectores
        cliente_llm: Cliente LLM opcional
        
    Returns:
        Dict con:
        {
            "por_region": {region: {hallazgos: [...], medios_sin_cobertura: [...]}},
            "total_hallazgos": int,
            "total_sin_cobertura": int
        }
    """
    if cliente_llm is None:
        cliente_llm = LLMClient()
    
    resultado = {
        "por_region": {},
        "total_hallazgos": 0,
        "total_sin_cobertura": 0
    }
    
    try:
        for consulta in consultas_config:
            region = consulta.get("region", "desconocido")
            query = consulta.get("query", "")
            modelo = consulta.get("modelo", MODELO_POR_DEFECTO)
            
            # Obtener medios para esta región
            medios_ids = medios_por_region.get(region, [])
            
            if not medios_ids or not query:
                continue
            
            # Ejecutar consulta
            region_result = buscar_con_perplexity(
                region, query, medios_ids, conectores_tematicos, cliente_llm
            )
            
            resultado["por_region"][region] = region_result
            resultado["total_hallazgos"] += len(region_result.get("hallazgos", []))
            resultado["total_sin_cobertura"] += len(region_result.get("medios_sin_cobertura", []))
        
        return resultado
        
    except Exception as e:
        logging.error(f"Error en ejecutar_capa2: {e}")
        raise RuntimeError(f"Error en capa 2 Perplexity: {e}")


def agrupar_por_medio(
    resultados_capa2: Dict[str, Any]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Agrupar todos los hallazgos de la capa 2 por medio_id.
    
    Args:
        resultados_capa2: Resultado de ejecutar_capa2()
        
    Returns:
        Dict mapeando medio_id -> lista de hallazgos
    """
    hallazgos_por_medio = {}
    
    try:
        for region, data in resultados_capa2.get("por_region", {}).items():
            for hallazgo in data.get("hallazgos", []):
                medio_id = hallazgo.get("medio_id")
                if medio_id:
                    if medio_id not in hallazgos_por_medio:
                        hallazgos_por_medio[medio_id] = []
                    hallazgos_por_medio[medio_id].append(hallazgo)
        
        return hallazgos_por_medio
        
    except Exception as e:
        logging.error(f"Error en agrupar_por_medio: {e}")
        return {}


def obtener_medios_sin_cobertura_capa2(
    resultados_capa2: Dict[str, Any]
) -> List[str]:
    """
    Obtener lista de todos los medios sin cobertura en la capa 2.
    
    Args:
        resultados_capa2: Resultado de ejecutar_capa2()
        
    Returns:
        Lista de medio_ids sin cobertura
    """
    sin_cobertura = []
    
    try:
        for region, data in resultados_capa2.get("por_region", {}).items():
            sin_cobertura.extend(data.get("medios_sin_cobertura", []))
        
        return list(set(sin_cobertura))
        
    except Exception as e:
        logging.error(f"Error en obtener_medios_sin_cobertura_capa2: {e}")
        return []
