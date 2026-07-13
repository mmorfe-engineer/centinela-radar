#!/usr/bin/env python3
"""
RADAR - Capa determinista: Matching de titulares
===============================================

Cruce de titulares contra conectores temáticos para identificar
cobertura sobre Venezuela.

Funciones principales:
- normalizar_texto_para_matching(): Normalización específica para matching
- cruzar_con_conectores(): Cruce de titulares × conectores
- conectores_activados(): Identificar qué conectores activó un titular

Reglas:
- Un titular matcha si contiene cualquier término o alias de cualquier conector
- Usar normalización del core (minúsculas, sin tildes, alias)
- Prohibido modificar conectores.json
"""

import re
from typing import Any, Dict, List, Optional, Set

from core.normalizacion import normalizar_titulo, normalizar_texto


def normalizar_para_matching(texto: str) -> str:
    """
    Normalizar texto para matching contra conectores.
    
    Aplica:
    1. normalizar_titulo del core (minúsculas, sin tildes, alias)
    2. Eliminar caracteres especiales adicionales
    3. Reemplazar guiones y barras por espacios
    
    Args:
        texto: Texto a normalizar
        
    Returns:
        Texto normalizado para matching
    """
    if not texto:
        return ""
    
    # Usar normalización del core
    texto = normalizar_titulo(texto)
    
    # Eliminar caracteres no alfanuméricos (excepto espacios)
    texto = re.sub(r'[^\w\s]', ' ', texto)
    
    # Reemplazar múltiples espacios por uno
    texto = re.sub(r'\s+', ' ', texto)
    
    # Eliminar espacios al inicio y final
    texto = texto.strip()
    
    return texto


def extraer_terminos_de_conectores(conectores_config: Dict[str, Any]) -> Set[str]:
    """
    Extraer todos los términos (canónicos + alias) de los conectores.
    
    Args:
        conectores_config: Dict con estructura de config/conectores.json
        
    Returns:
        Set de términos normalizados para matching rápido
    """
    todos_terminos = set()
    
    try:
        grupos = conectores_config.get("grupos", {})
        for grupo_nombre, grupo_config in grupos.items():
            if isinstance(grupo_config, dict):
                terminos = grupo_config.get("terminos", [])
                for termino in terminos:
                    if isinstance(termino, dict):
                        canonico = termino.get("canonico", "")
                        alias = termino.get("alias", [])
                        
                        # Añadir canónico normalizado
                        if canonico:
                            todos_terminos.add(normalizar_para_matching(canonico))
                        
                        # Añadir aliases normalizados
                        for a in alias:
                            todos_terminos.add(normalizar_para_matching(a))
    except Exception as e:
        # Fail loud
        raise ValueError(f"Error extrayendo términos de conectores: {e}")
    
    return todos_terminos


def conectores_activados(texto: str, conectores_config: Dict[str, Any]) -> List[str]:
    """
    Identificar qué conectores específica activó un texto.
    
    Args:
        texto: Texto a analizar (titular o resumen)
        conectores_config: Configuración de conectores
        
    Returns:
        Lista de ids de conectores activados
    """
    texto_norm = normalizar_para_matching(texto)
    conectores_activados = []
    
    try:
        grupos = conectores_config.get("grupos", {})
        for grupo_nombre, grupo_config in grupos.items():
            if isinstance(grupo_config, dict):
                terminos = grupo_config.get("terminos", [])
                for termino in terminos:
                    if isinstance(termino, dict):
                        canonico = termino.get("canonico", "")
                        alias = termino.get("alias", [])
                        
                        # Verificar si el texto contiene el término
                        todos_nombres = [normalizar_para_matching(canonico)] + \
                                       [normalizar_para_matching(a) for a in alias]
                        
                        for nombre in todos_nombres:
                            if nombre and nombre in texto_norm:
                                conectores_activados.append(grupo_nombre)
                                break  # Solo contar una vez por grupo
    except Exception as e:
        raise ValueError(f"Error identificando conectores activados: {e}")
    
    return conectores_activados


def titular_matcha_conectores(titular: str, conectores_config: Dict[str, Any]) -> bool:
    """
    Verificar si un titular matcha con algún conector.
    
    Args:
        titular: Texto del titular
        conectores_config: Configuración de conectores
        
    Returns:
        True si matcha con al menos un conector, False de lo contrario
    """
    if not titular:
        return False
    
    # Usar el set de términos para matching rápido
    terminos = extraer_terminos_de_conectores(conectores_config)
    
    titular_norm = normalizar_para_matching(titular)
    
    # Verificar si algún término está en el titular
    for termino in terminos:
        if termino and termino in titular_norm:
            return True
    
    return False


def cruzar_con_conectores(
    titulares: List[Dict[str, Any]], 
    conectores_config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Cruzar lista de titulares contra conectores temáticos.
    
    Args:
        titulares: Lista de dicts con {"titulo": str, "url": str, "fecha": str | None, ...}
        conectores_config: Configuración de conectores
        
    Returns:
        Lista de hallazgos (solo aquellos que matcheen):
        [
            {
                "titulo": str,
                "url": str,
                "fecha": str | None,
                "medio_id": str (si disponible),
                "conectores_activados": [str],
                "texto_normalizado": str
            },
            ...
        ]
        
    Note:
        Todos los titulares se conservan para el Top 10 Global,
        pero solo los que matcheen se devuelven como hallazgos.
    """
    hallazgos = []
    
    try:
        for titular_dict in titulares:
            titulo = titular_dict.get("titulo", "")
            if not titulo:
                continue
            
            # Verificar si matcha
            if titular_matcha_conectores(titulo, conectores_config):
                # Identificar conectores activados
                conectores_act = conectores_activados(titulo, conectores_config)
                
                hallazgo = {
                    "titulo": titulo,
                    "url": titular_dict.get("url", ""),
                    "fecha": titular_dict.get("fecha"),
                    "medio_id": titular_dict.get("medio_id"),
                    "conectores_activados": conectores_act,
                    "texto_normalizado": normalizar_para_matching(titulo)
                }
                hallazgos.append(hallazgo)
        
        return hallazgos
        
    except Exception as e:
        # Fail loud
        raise RuntimeError(f"Error en cruce de conectores: {e}")


def filtrar_titulares_no_vacios(titulares: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filtrar titulares vacíos o con texto muy corto.
    
    Args:
        titulares: Lista de dicts con titulares
        
    Returns:
        Lista filtrada
    """
    resultado = []
    for t in titulares:
        titulo = t.get("titulo", "")
        if titulo and len(titulo.strip()) > 3:
            resultado.append(t)
    return resultado
