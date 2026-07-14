#!/usr/bin/env python3
"""
RADAR - Export CSV de la matriz
===============================

Exportar la matriz de hallazgos a formato CSV para análisis histórico.

Funciones principales:
- generar_csv_matriz(): Generar CSV con las columnas del reporte.json

Reglas:
- Usar las columnas definidas en config/reporte.json
- Un archivo por corrida: matriz_{fecha}-{corte}.csv
- Formato UTF-8 con BOM para Excel
"""

import csv
import datetime
from typing import Any, Dict, List, Tuple

# Columnas del CSV según config/reporte.json
COLUMNAS_CSV = [
    "medio_id",
    "medio_nombre",
    "region",
    "semaforo",
    "titulo",
    "url",
    "url_archivo",
    "fecha",
    "tipo_pieza",
    "enfoque_matriz",
    "valencia",
    "valencia_respecto_a",
    "prominencia",
    "conectores_activados",
    "resumen_1_frase"
]


def formatear_conectores_activados(conectores: List[str]) -> str:
    """
    Formatear lista de conectores activados para CSV.
    
    Args:
        conectores: Lista de strings de conectores
        
    Returns:
        String separado por comas
    """
    if not conectores:
        return ""
    return ";".join(conectores)


def formatear_lista_para_csv(lista: List[str]) -> str:
    """
    Formatear una lista para CSV (separado por punto y coma).
    
    Args:
        lista: Lista de strings
        
    Returns:
        String formateado
    """
    if not lista:
        return ""
    return ";".join(str(item) for item in lista)


def crear_fila_csv(
    hallazgo: Dict[str, Any],
    medio_config: Dict[str, Any]
) -> Dict[str, str]:
    """
    Crear una fila del CSV a partir de un hallazgo.
    
    Args:
        hallazgo: Dict con datos del hallazgo
        medio_config: Configuración del medio
        
    Returns:
        Dict con valores para cada columna
    """
    fila = {col: "" for col in COLUMNAS_CSV}
    
    try:
        # Datos del medio
        fila["medio_id"] = hallazgo.get("medio_id", "")
        fila["medio_nombre"] = medio_config.get("nombre", "")
        fila["region"] = medio_config.get("region", "desconocido")
        
        # Datos del hallazgo
        fila["semaforo"] = "VERDE_con_cobertura"  # Por defecto para hallazgos
        fila["titulo"] = hallazgo.get("titulo", "")
        fila["url"] = hallazgo.get("url", "")
        fila["url_archivo"] = hallazgo.get("url_archivo", "")
        
        # Fecha
        fecha = hallazgo.get("fecha")
        if fecha:
            fila["fecha"] = str(fecha)
        else:
            fila["fecha"] = ""
        
        # Tipo de pieza
        fila["tipo_pieza"] = hallazgo.get("tipo_pieza", "")
        
        # Clasificación de matriz
        fila["enfoque_matriz"] = hallazgo.get("enfoque_matriz", "")
        fila["valencia"] = hallazgo.get("valencia", "")
        fila["valencia_respecto_a"] = hallazgo.get("valencia_respecto_a", "")
        
        # Prominencia
        fila["prominencia"] = hallazgo.get("prominencia", "")
        
        # Conectores activados
        conectores = hallazgo.get("conectores_activados", [])
        fila["conectores_activados"] = formatear_conectores_activados(conectores)
        
        # Resumen
        fila["resumen_1_frase"] = hallazgo.get("resumen_1_frase", "")
        
        return fila
        
    except Exception as e:
        raise RuntimeError(f"Error creando fila CSV para hallazgo {hallazgo.get('id', '?')}: {e}")


def generar_csv_matriz(
    hallazgos: List[Dict[str, Any]],
    medios_config: List[Dict[str, Any]],
    fecha: str,
    corte: str
) -> str:
    """
    Generar contenido CSV de la matriz.
    
    Args:
        hallazgos: Lista de hallazgos (solo los VERDES)
        medios_config: Configuración de medios
        fecha: Fecha en formato YYYYMMDD
        corte: Nombre del corte (MATUTINO/VESPERTINO)
        
    Returns:
        String con el contenido CSV
    """
    try:
        # Crear mapeo de medio_id -> config
        medios_map = {m.get("id"): m for m in medios_config}
        
        # Crear filas
        filas = []
        for hallazgo in hallazgos:
            medio_id = hallazgo.get("medio_id", "desconocido")
            medio_config = medios_map.get(medio_id, {})
            fila = crear_fila_csv(hallazgo, medio_config)
            filas.append(fila)
        
        # Ordenar por medio_id para consistencia
        filas.sort(key=lambda f: f.get("medio_id", ""))
        
        # Crear CSV
        output = []
        
        # Header
        output.append(",".join(COLUMNAS_CSV))
        
        # Filas
        for fila in filas:
            fila_vals = []
            for col in COLUMNAS_CSV:
                val = fila.get(col, "")
                # Escapar comillas dobles
                val = str(val).replace('"', '""')
                fila_vals.append(f'"{val}"')
            fila_csv = ",".join(fila_vals)
            output.append(fila_csv)
        
        # Unir con saltos de línea
        return "\n".join(output)
        
    except Exception as e:
        raise RuntimeError(f"Error generando CSV: {e}")


def guardar_csv_matriz(
    hallazgos: List[Dict[str, Any]],
    medios_config: List[Dict[str, Any]],
    fecha: str,
    corte: str,
    directorio_salida: str = "."
) -> str:
    """
    Guardar el CSV de la matriz en un archivo.
    
    Args:
        hallazgos: Lista de hallazgos
        medios_config: Configuración de medios
        fecha: Fecha en formato YYYYMMDD
        corte: Nombre del corte
        directorio_salida: Directorio donde guardar
        
    Returns:
        Ruta al archivo generado
    """
    import os
    
    try:
        # Generar contenido CSV
        csv_content = generar_csv_matriz(hallazgos, medios_config, fecha, corte)
        
        # Crear nombre de archivo
        filename = f"matriz_{fecha}-{corte.lower()}.csv"
        filepath = os.path.join(directorio_salida, filename)
        
        # Asegurar que el directorio existe
        os.makedirs(directorio_salida, exist_ok=True)
        
        # Guardar archivo
        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            f.write(csv_content)
        
        return filepath
        
    except Exception as e:
        raise RuntimeError(f"Error guardando CSV: {e}")


def leer_csv_matriz(filepath: str) -> List[Dict[str, str]]:
    """
    Leer un CSV de matriz generado previamente.
    
    Args:
        filepath: Ruta al archivo CSV
        
    Returns:
        Lista de dicts con los datos
    """
    import os
    
    if not os.path.exists(filepath):
        return []
    
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception as e:
        raise RuntimeError(f"Error leyendo CSV {filepath}: {e}")


# Funciones utilitarias para el pipeline completo

def generar_nombre_archivo_csv() -> Tuple[str, str]:
    """
    Generar fecha y corte actual para el nombre del archivo.
    
    Returns:
        Tuple[fecha: str, corte: str]
    """
    ahora = datetime.datetime.utcnow()
    fecha = ahora.strftime("%Y%m%d")
    
    # Determinar corte basado en la hora UTC
    hora = ahora.hour
    if 10 <= hora < 13:  # Cerca de 11:00 UTC
        corte = "MATUTINO"
    elif 20 <= hora < 23:  # Cerca de 21:00 UTC
        corte = "VESPERTINO"
    else:
        # Si no es hora de corte, usar el último corte
        corte = "MATUTINO" if hora < 12 else "VESPERTINO"
    
    return fecha, corte
