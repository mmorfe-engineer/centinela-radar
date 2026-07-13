#!/usr/bin/env python3
"""
RADAR - Top 5 Venezuela
=====================

Ranking de los 5 hallazgos más relevantes sobre Venezuela.

Funciones principales:
- generar_top5_venezuela(): Generar el Top 5 a partir de hallazgos VERDES

Reglas:
- Fuente: hallazgos VERDES (con cobertura confirmada)
- Ranking: prominencia × authority_score × repetición cross-medio × (×2 si editorial/opinión)
- Solo se incluyen hallazgos sobre Venezuela
"""

from typing import Any, Dict, List


# Peso adicional para editoriales y opiniones
MULTIPLICADOR_EDITORIAL = 2.0


def calcular_puntuacion_top5(
    hallazgo: Dict[str, Any],
    authority_map: Dict[str, float]
) -> float:
    """
    Calcular puntuación para ranking Top 5.
    
    Args:
        hallazgo: Dict con datos del hallazgo
        authority_map: Dict mapeando medio_id -> authority_score
        
    Returns:
        Puntuación numérica
    """
    try:
        # Obtener valores con defaults
        prominencia = hallazgo.get("prominencia", "")
        medio_id = hallazgo.get("medio_id", "")
        es_editorial = hallazgo.get("es_editorial_u_opinion", False)
        
        # Peso por prominencia
        pesos_prominencia = {
            "portada": 1.0,
            "apertura_seccion": 0.8,
            "interior": 0.5,
            "": 0.3
        }
        peso_prominencia = pesos_prominencia.get(prominencia.lower(), 0.3)
        
        # Authority score del medio
        authority = authority_map.get(medio_id, 0.5)
        
        # Repetición cross-medio (contar cuántas veces aparece este tema)
        # Por ahora usamos 1.0 (esto se ajustará en el ranking final)
        repeticion = 1.0
        
        # Multiplicador por editorial/opinión
        multiplicador_editorial = MULTIPLICADOR_EDITORIAL if es_editorial else 1.0
        
        # Cálculo final
        puntuacion = peso_prominencia * authority * repeticion * multiplicador_editorial
        
        return puntuacion
        
    except Exception as e:
        # Fail loud
        raise RuntimeError(f"Error calculando puntuación para hallazgo: {e}")


def calcular_repeticion_cross_medio(
    hallazgo: Dict[str, Any],
    todos_hallazgos: List[Dict[str, Any]]
) -> int:
    """
    Calcular cuántos medios reportaron este hallazgo o uno similar.
    
    Args:
        hallazgo: Hallazgo a evaluar
        todos_hallazgos: Todos los hallazgos para comparar
        
    Returns:
        Número de medios que reportaron este tema
    """
    try:
        titulo = hallazgo.get("titulo", "")
        if not titulo:
            return 1
        
        # Contar cuántos hallazgos tienen el mismo título o similar
        count = 0
        for h in todos_hallazgos:
            other_titulo = h.get("titulo", "")
            if titulo.lower() == other_titulo.lower():
                count += 1
            # Podríamos usar similitud de texto, pero por ahora usamos igualdad exacta
        
        return max(count, 1)
        
    except Exception as e:
        raise RuntimeError(f"Error calculando repetición: {e}")


def generar_top5_venezuela(
    hallazgos_verdes: List[Dict[str, Any]],
    medios_config: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Generar el Top 5 Venezuela a partir de los hallazgos VERDES.
    
    Args:
        hallazgos_verdes: Lista de hallazgos con estado VERDE (con cobertura)
        medios_config: Configuración de medios
        
    Returns:
        Lista de los Top 5 hallazgos, ordenados por puntuación:
        [
            {
                "rank": int,
                "hallazgo": dict,
                "puntuacion": float
            },
            ...
        ]
    """
    if not hallazgos_verdes:
        return []
    
    try:
        # Crear mapeo de authority scores
        authority_map = {}
        for medio in medios_config:
            authority_map[medio.get("id", "")] = medio.get("authority_score", 0.5)
        
        # Calcular puntuación para cada hallazgo
        hallazgos_con_puntuacion = []
        for hallazgo in hallazgos_verdes:
            puntuacion = calcular_puntuacion_top5(hallazgo, authority_map)
            hallazgos_con_puntuacion.append({
                "hallazgo": hallazgo,
                "puntuacion": puntuacion
            })
        
        # Ordenar por puntuación descendente
        hallazgos_con_puntuacion.sort(key=lambda x: x["puntuacion"], reverse=True)
        
        # Tomar Top 5
        top5 = hallazgos_con_puntuacion[:5]
        
        # Formatear resultado
        resultado = []
        for idx, item in enumerate(top5, 1):
            resultado.append({
                "rank": idx,
                "hallazgo": item["hallazgo"],
                "puntuacion": item["puntuacion"]
            })
        
        return resultado
        
    except Exception as e:
        raise RuntimeError(f"Error generando Top 5 Venezuela: {e}")


def generar_top5_con_repeticion(
    hallazgos_verdes: List[Dict[str, Any]],
    medios_config: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Generar Top 5 con cálculo de repetición cross-medio.
    
    Args:
        hallazgos_verdes: Lista de hallazgos VERDES
        medios_config: Configuración de medios
        
    Returns:
        Top 5 con puntuación ajustada por repetición
    """
    if not hallazgos_verdes:
        return []
    
    try:
        # Crear mapeo de authority scores
        authority_map = {}
        for medio in medios_config:
            authority_map[medio.get("id", "")] = medio.get("authority_score", 0.5)
        
        # Calcular puntuación final (incluyendo repetición)
        hallazgos_con_puntuacion = []
        for hallazgo in hallazgos_verdes:
            # Puntuación base
            puntuacion_base = calcular_puntuacion_top5(hallazgo, authority_map)
            
            # Repetición cross-medio
            repeticion = calcular_repeticion_cross_medio(hallazgo, hallazgos_verdes)
            
            # Puntuación final
            puntuacion_final = puntuacion_base * repeticion
            
            hallazgos_con_puntuacion.append({
                "hallazgo": hallazgo,
                "puntuacion_base": puntuacion_base,
                "repeticion": repeticion,
                "puntuacion_final": puntuacion_final
            })
        
        # Ordenar por puntuación final descendente
        hallazgos_con_puntuacion.sort(key=lambda x: x["puntuacion_final"], reverse=True)
        
        # Tomar Top 5
        top5 = hallazgos_con_puntuacion[:5]
        
        # Formatear resultado
        resultado = []
        for idx, item in enumerate(top5, 1):
            resultado.append({
                "rank": idx,
                "hallazgo": item["hallazgo"],
                "puntuacion": item["puntuacion_final"],
                "puntuacion_base": item["puntuacion_base"],
                "repeticion_cross_medio": item["repeticion"]
            })
        
        return resultado
        
    except Exception as e:
        raise RuntimeError(f"Error generando Top 5 con repetición: {e}")


def obtener_resumen_top5(top5: List[Dict[str, Any]]) -> str:
    """
    Generar resumen textual del Top 5.
    
    Args:
        top5: Lista del Top 5
        
    Returns:
        String con resumen
    """
    if not top5:
        return "No hay hallazgos para el Top 5 Venezuela"
    
    lineas = ["🔝 TOP 5 VENEZUELA"]
    for item in top5:
        hallazgo = item["hallazgo"]
        rank = item["rank"]
        
        titulo = hallazgo.get("titulo", "Sin título")
        medio = hallazgo.get("medio_id", "?")
        tipo = hallazgo.get("tipo_pieza", "")
        prominencia = hallazgo.get("prominencia", "")
        
        # Formatear línea
        tipos_emoji = {
            "portada": "📰",
            "editorial": "✍️",
            "opinion": "💭",
            "nota": "📄",
            "analisis": "📊"
        }
        emoji = tipos_emoji.get(tipo, "📌")
        
        lineas.append(f"  {rank}. {emoji} {titulo[:60]}... ({medio}, {prominencia})")
    
    return "\n".join(lineas)
