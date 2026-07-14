#!/usr/bin/env python3
"""
RADAR - Clasificación de matriz
============================

Clasificación de hallazgos usando LLM (DeepSeek-R1) para determinar:
- enfoque_matriz: gobierno, oposición, país_general
- valencia: favorable, crítica, neutral, mixta
- valencia_respecto_a: gobierno, oposición
- prominencia: portada, apertura_seccion, interior
- es_editorial_u_opinion: bool

Funciones principales:
- clasificar_hallazgo(): Clasificar un solo hallazgo
- clasificar_todos(): Clasificar todos los hallazgos

Reglas:
- Usar acción="clasificar" (rutea a DeepSeek)
- Temperatura 0 para determinismo
- Terminología neutral siempre
"""

import json
import logging
from typing import Any, Dict, List, Optional

from core.llm import LLMClient


# Opciones válidas según config/reporte.json
OPCIONES_ENFOQUE = ["gobierno", "oposicion", "pais_general"]
OPCIONES_VALENCIA = ["favorable", "critica", "neutral", "mixta"]
OPCIONES_VALENCIA_RESP = ["gobierno", "oposicion"]
OPCIONES_PROMINENCIA = ["portada", "apertura_seccion", "interior"]


def crear_prompt_clasificacion(hallazgo: Dict[str, Any]) -> str:
    """
    Crear prompt para clasificar un hallazgo.
    
    Args:
        hallazgo: Dict con datos del hallazgo
        
    Returns:
        Prompt formateado
    """
    titulo = hallazgo.get("titulo", "Sin título")
    resumen = hallazgo.get("resumen_1_frase", "")
    medio_id = hallazgo.get("medio_id", "desconocido")
    conectores = hallazgo.get("conectores_activados", [])
    
    conectores_str = "; ".join(conectores) if conectores else "ninguno"
    
    prompt = f"""
CLASIFICACIÓN DE MATRIZ - Análisis neutral de cobertura mediática

HALLGO A CLASIFICAR:
- Título: "{titulo}"
- Resumen: "{resumen}"
- Medio: {medio_id}
- Conectores activados: {conectores_str}

INSTRUCCIÓN:
Clasifica este hallazgo según los siguientes criterios. Devuelve SOLO un objeto JSON con el schema:

{{
    "enfoque_matriz": "gobierno"|"oposicion"|"pais_general",
    "valencia": "favorable"|"critica"|"neutral"|"mixta",
    "valencia_respecto_a": "gobierno"|"oposicion",
    "prominencia": "portada"|"apertura_seccion"|"interior",
    "es_editorial_u_opinion": true|false
}}

DEFINICIONES:
- enfoque_matriz:
  * "gobierno": el hallazgo está centrado en acciones, declaraciones o políticas del gobierno/Estado
  * "oposicion": el hallazgo está centrado en acciones o declaraciones de actores de oposición
  * "pais_general": el hallazgo aborda temas que afectan al país en general sin enfoque específico

- valencia:
  * "favorable": el tono general es positivo para el sujeto
  * "critica": el tono general es negativo para el sujeto
  * "neutral": no hay tono positivo ni negativo
  * "mixta": hay elementos positivos y negativos

- valencia_respecto_a: ¿respecto a quién es la valencia? ("gobierno" o "oposicion")

- prominencia:
  * "portada": el artículo aparece en portada o lugar destacado
  * "apertura_seccion": aparece en la apertura de una sección
  * "interior": aparece en el interior de la sección

- es_editorial_u_opinion: true si es un artículo de opinión, editorial, columna o análisis

REGLAS:
1. Usa terminología neutral: "gobierno" / "oposición" / "país en general".
2. valencia_respecto_a solo aplica si enfoque_matriz no es "pais_general".
3. Si enfoque_matriz es "pais_general", valencia_respecto_a puede ser null o vacío.
4. Analiza el TEXTOS COMPLETO (título + resumen), no solo el título.
5. No asumas intencionalidad: clasifica lo que dice el texto, no lo que "debe" decir.

Clasifica el hallazgo.
"""
    
    return prompt.strip()


def parsear_respuesta_clasificacion(respuesta: str) -> Dict[str, Any]:
    """
    Parsear la respuesta del LLM al schema de clasificación.
    
    Args:
        respuesta: Texto de la respuesta
        
    Returns:
        Dict con los campos de clasificación
    """
    resultado = {}

    try:
        # Extraer JSON de markdown code fences si Mistral los incluye
        texto = respuesta.strip()
        if texto.startswith("```"):
            lineas = texto.split("\n")
            lineas = lineas[1:]  # quitar ```json o ```
            if lineas and lineas[-1].strip() == "```":
                lineas = lineas[:-1]
            texto = "\n".join(lineas).strip()
        else:
            texto = respuesta.strip()

        # Intentar parsear como JSON
        if texto.startswith("{"):
            data = json.loads(texto)
            
            # Validar campos
            for campo, opciones in [
                ("enfoque_matriz", OPCIONES_ENFOQUE),
                ("valencia", OPCIONES_VALENCIA),
                ("valencia_respecto_a", OPCIONES_VALENCIA_RESP),
                ("prominencia", OPCIONES_PROMINENCIA)
            ]:
                valor = data.get(campo)
                if valor and valor not in opciones:
                    logging.warning(f"Valor inválido para {campo}: {valor}. Usando default.")
                    data[campo] = opciones[0] if opciones else None
            
            # Validar es_editorial_u_opinion
            es_editorial = data.get("es_editorial_u_opinion")
            if isinstance(es_editorial, bool):
                data["es_editorial_u_opinion"] = es_editorial
            else:
                data["es_editorial_u_opinion"] = False
            
            return data
        else:
            logging.warning(f"Respuesta no es JSON: {texto[:200]}")
            return {}
    
    except json.JSONDecodeError as e:
        logging.error(f"Error parseando JSON: {e}")
        return {}
    
    except Exception as e:
        logging.error(f"Error en parsear_respuesta_clasificacion: {e}")
        return {}


def clasificar_hallazgo(
    hallazgo: Dict[str, Any],
    cliente_llm: Optional[LLMClient] = None
) -> Dict[str, Any]:
    """
    Clasificar un solo hallazgo usando LLM.
    
    Args:
        hallazgo: Dict con datos del hallazgo
        cliente_llm: Cliente LLM opcional
        
    Returns:
        Dict con los campos de clasificación añadidos
    """
    # Crear cliente si no se proporciona
    if cliente_llm is None:
        cliente_llm = LLMClient()
    
    try:
        # Crear prompt
        prompt = crear_prompt_clasificacion(hallazgo)
        
        # Ejecutar clasificación con DeepSeek (acción="clasificar")
        resultado_llm = cliente_llm.completar(
            accion="clasificar",
            prompt=prompt,
            # modelo=None → usa routing table: nvidia/deepseek-ai/deepseek-r1
            # con fallback automático a mistral/mistral-large-latest
            temperatura=0.0,
            max_tokens=500
        )

        # completar() devuelve un dict; extraer el texto de la respuesta
        if not resultado_llm.get("exito"):
            raise RuntimeError(f"LLM falló: {resultado_llm.get('error', 'sin detalle')}")
        respuesta_texto = resultado_llm.get("respuesta", "") or ""

        # Parsear respuesta
        clasificacion = parsear_respuesta_clasificacion(respuesta_texto)
        
        # Añadir clasificación al hallazgo
        resultado = hallazgo.copy()
        resultado.update(clasificacion)
        
        return resultado
        
    except Exception as e:
        logging.error(f"Error en clasificar_hallazgo: {e}")
        # Devolver hallazgo original con valores default
        return {
            **hallazgo,
            "enfoque_matriz": "pais_general",
            "valencia": "neutral",
            "valencia_respecto_a": None,
            "prominencia": "interior",
            "es_editorial_u_opinion": False
        }


def clasificar_todos(
    hallazgos: List[Dict[str, Any]],
    cliente_llm: Optional[LLMClient] = None
) -> List[Dict[str, Any]]:
    """
    Clasificar todos los hallazgos.
    
    Args:
        hallazgos: Lista de hallazgos a clasificar
        cliente_llm: Cliente LLM opcional
        
    Returns:
        Lista de hallazgos con clasificación añadida
    """
    if not hallazgos:
        return []
    
    if cliente_llm is None:
        cliente_llm = LLMClient()
    
    resultado = []
    
    try:
        for idx, hallazgo in enumerate(hallazgos):
            logging.info(f"Clasificando hallazgo {idx + 1}/{len(hallazgos)}")
            
            hallazgo_clasificado = clasificar_hallazgo(hallazgo, cliente_llm)
            resultado.append(hallazgo_clasificado)
        
        return resultado
        
    except Exception as e:
        logging.error(f"Error en clasificar_todos: {e}")
        raise RuntimeError(f"Error clasificando hallazgos: {e}")


def clasificar_batch(
    hallazgos: List[Dict[str, Any]],
    batch_size: int = 5,
    cliente_llm: Optional[LLMClient] = None
) -> List[Dict[str, Any]]:
    """
    Clasificar hallazgos en batches para optimizar uso de API.
    
    Args:
        hallazgos: Lista de hallazgos
        batch_size: Tamaño del batch
        cliente_llm: Cliente LLM opcional
        
    Returns:
        Lista de hallazgos clasificados
    """
    if not hallazgos:
        return []
    
    if cliente_llm is None:
        cliente_llm = LLMClient()
    
    resultado = []
    
    try:
        for i in range(0, len(hallazgos), batch_size):
            batch = hallazgos[i:i + batch_size]
            batch_result = clasificar_todos(batch, cliente_llm)
            resultado.extend(batch_result)
        
        return resultado
        
    except Exception as e:
        logging.error(f"Error en clasificar_batch: {e}")
        raise RuntimeError(f"Error en clasificación por batch: {e}")
