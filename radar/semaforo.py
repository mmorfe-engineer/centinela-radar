#!/usr/bin/env python3
"""
RADAR - Semáforo de certificación
==================================

Asignación de estados 🟢🟡🔴 a cada medio según las reglas del reporte.json.

Regla central del producto:
"NINGÚN MEDIO PUEDE TERMINAR SIN ESTADO ASIGNADO"
Violación = fallo de auditoría nivel 1

Estados:
- 🟢 CON COBERTURA: Hallazgos sobre Venezuela encontrados, con enlace verificado
- 🟡 SIN COBERTURA (certificado): El medio fue revisado y NO publicó sobre Venezuela
- 🔴 NO VERIFICABLE: No se pudo revisar (error, timeout, paywall)

Compuerta propia del RADAR:
"ningún medio puede terminar la corrida sin estado asignado"
"""

from typing import Any, Dict, List, Optional, Tuple

from core.normalizacion import normalizar_titulo

# Constantes de estados
ESTADO_VERDE = "VERDE_con_cobertura"
ESTADO_AMARILLO = "AMARILLO_sin_cobertura_certificado"
ESTADO_ROJO = "ROJO_no_verificable"


def esta_en_cobertura(medio_resultado: Dict[str, Any], 
                      hallazgos_medio: List[Dict[str, Any]]) -> bool:
    """
    Determinar si un medio tiene cobertura sobre Venezuela.
    
    Args:
        medio_resultado: Resultado de fetch_medio()
        hallazgos_medio: Hallazgos del matching para este medio
        
    Returns:
        True si tiene cobertura, False de lo contrario
    """
    # Si el medio tuvo éxito en fetch y tiene hallazgos
    if medio_resultado.get("exito", False) and hallazgos_medio:
        return True
    return False


def asignar_estado_medio(
    medio_config: Dict[str, Any],
    medio_resultado: Dict[str, Any],
    hallazgos_medio: List[Dict[str, Any]],
    config_semaforo: Optional[Dict[str, Any]] = None
) -> Tuple[str, str]:
    """
    Asignar estado a un medio según las reglas.
    
    Args:
        medio_config: Configuración del medio
        medio_resultado: Resultado de fetch_medio()
        hallazgos_medio: Hallazgos del matching para este medio
        config_semaforo: Configuración del semáforo (opcional)
        
    Returns:
        Tuple[estado: str, explicacion: str]
        
    Reglas:
    - 🟢: fetch exitoso + hallazgos sobre Venezuela
    - 🟡: fetch exitoso + SIN hallazgos sobre Venezuela
    - 🔴: fetch fallido (no verificable)
    """
    exito = medio_resultado.get("exito", False)
    tiene_cobertura = esta_en_cobertura(medio_resultado, hallazgos_medio)
    
    if exito:
        if tiene_cobertura:
            return ESTADO_VERDE, "Fetch exitoso + hallazgos sobre Venezuela"
        else:
            return ESTADO_AMARILLO, "Fetch exitoso + sin hallazgos sobre Venezuela (certificado)"
    else:
        # Fetch fallido -> NO VERIFICABLE
        error = medio_resultado.get("error", "Error desconocido")
        return ESTADO_ROJO, f"Fetch fallido: {error}"


def asignar_estados(
    medios_config: List[Dict[str, Any]],
    resultados_fetch: Dict[str, Any],
    hallazgos_por_medio: Dict[str, List[Dict[str, Any]]],
    config_semaforo: Optional[Dict[str, Any]] = None
) -> Tuple[Dict[str, str], Dict[str, Any], Dict[str, str]]:
    """
    Asignar estados a todos los medios.
    
    Args:
        medios_config: Lista de medios del config
        resultados_fetch: Resultado de fetch_todos_medios()
        hallazgos_por_medio: Dict mapeando medio_id -> lista de hallazgos
        config_semaforo: Configuración del semáforo (opcional)
        
    Returns:
        Tuple[estados: Dict[str, str], tablero: Dict[str, Any], errores_medios: Dict[str, str]]
        
        estados: {"medio_id": "VERDE_con_cobertura" | "AMARILLO_..." | "ROJO_..."}
        tablero: {"total": int, "verdes": int, "amarillos": int, "rojos": int, ...}
        errores_medios: {"medio_id": "descripción del error"} para medios ROJO
    """
    estados = {}
    tablero = {
        "total": len(medios_config),
        ESTADO_VERDE: 0,
        ESTADO_AMARILLO: 0,
        ESTADO_ROJO: 0
    }
    errores_medios = {}
    
    # Crear mapeo de id -> resultado de fetch
    resultados_por_id = {}
    for resultado in resultados_fetch.get("medios", []):
        resultados_por_id[resultado["id"]] = resultado
    
    # Asignar estado a cada medio
    for medio in medios_config:
        medio_id = medio.get("id", "desconocido")
        resultado_fetch = resultados_por_id.get(medio_id, {})
        hallazgos = hallazgos_por_medio.get(medio_id, [])
        
        estado, explicacion = asignar_estado_medio(medio, resultado_fetch, hallazgos)
        estados[medio_id] = estado
        tablero[estado] += 1
        
        # Guardar error para medios ROJO
        if estado == ESTADO_ROJO:
            errores_medios[medio_id] = explicacion
    
    # Verificar regla central: ningún medio sin estado
    medios_sin_estado = [m for m in medios_config if m.get("id") not in estados]
    if medios_sin_estado:
        raise RuntimeError(
            f"VIOLACIÓN DE REGLA CENTRAL: {len(medios_sin_estado)} medios sin estado: "
            f"{', '.join(m.get('id', '?') for m in medios_sin_estado)}"
        )
    
    # Verificar que total = suma de estados
    total_estados = tablero[ESTADO_VERDE] + tablero[ESTADO_AMARILLO] + tablero[ESTADO_ROJO]
    if total_estados != tablero["total"]:
        raise RuntimeError(
            f"Tablero incoherente: total={tablero['total']} "
            f"vs suma={total_estados}"
        )
    
    return estados, tablero, errores_medios


def generar_tablero(
    estados: Dict[str, str],
    medios_config: List[Dict[str, Any]],
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generar tablero de certificación formateado.
    
    Args:
        estados: Dict de medio_id -> estado
        medios_config: Lista de medios
        config: Configuración del reporte (opcional)
        
    Returns:
        Dict con estructura:
        {
            "total": int,
            "estados": {"VERDE": int, "AMARILLO": int, "ROJO": int},
            "por_region": {"eeuu": {"VERDE": int, ...}, ...},
            "medios": [
                {"id": str, "nombre": str, "region": str, "estado": str},
                ...
            ]
        }
    """
    tablero = {
        "total": len(estados),
        "estados": {
            ESTADO_VERDE: 0,
            ESTADO_AMARILLO: 0,
            ESTADO_ROJO: 0
        },
        "por_region": {},
        "medios": []
    }
    
    # Contar por estado
    for estado in estados.values():
        tablero["estados"][estado] += 1
    
    # Contar por región
    regiones = set()
    for medio in medios_config:
        region = medio.get("region", "desconocido")
        regiones.add(region)
        if region not in tablero["por_region"]:
            tablero["por_region"][region] = {
                ESTADO_VERDE: 0,
                ESTADO_AMARILLO: 0,
                ESTADO_ROJO: 0
            }
    
    for medio in medios_config:
        medio_id = medio.get("id")
        region = medio.get("region", "desconocido")
        estado = estados.get(medio_id)
        
        if estado:
            tablero["por_region"][region][estado] += 1
        
        tablero["medios"].append({
            "id": medio_id,
            "nombre": medio.get("nombre", ""),
            "region": region,
            "estado": estado
        })
    
    return tablero


def validar_tablero(tablero: Dict[str, Any], total_medios: int) -> bool:
    """
    Validar que el tablero es coherente.
    
    Args:
        tablero: Dict con estructura del tablero
        total_medios: Total de medios esperado
        
    Returns:
        True si es coherente, False de lo contrario
        
    Raises:
        RuntimeError si no es coherente
    """
    total = tablero.get("total", 0)
    suma_estados = sum(tablero.get("estados", {}).values())
    
    if total != total_medios:
        raise RuntimeError(
            f"Tablero incoherente: total={total} vs esperado={total_medios}"
        )
    
    if total != suma_estados:
        raise RuntimeError(
            f"Tablero incoherente: total={total} vs suma_estados={suma_estados}"
        )
    
    return True
