#!/usr/bin/env python3
"""
Tests para radar/csv_matriz.py
"""

import csv
import io
import os
import tempfile
from typing import Any, Dict, List

from radar.csv_matriz import (
    COLUMNAS_CSV,
    formatear_conectores_activados,
    formatear_lista_para_csv,
    crear_fila_csv,
    generar_csv_matriz,
    guardar_csv_matriz,
    leer_csv_matriz,
    generar_nombre_archivo_csv
)


class TestFormatearConectoresActivados:
    """Tests para formatear_conectores_activados()"""

    def test_lista_vacia(self):
        """Lista vacía debe devolver string vacío"""
        resultado = formatear_conectores_activados([])
        assert resultado == ""

    def test_un_conector(self):
        """Un conector debe formatearse correctamente"""
        resultado = formatear_conectores_activados(["sanciones"])
        assert resultado == "sanciones"

    def test_varios_conectores(self):
        """Varios conectores deben separarse por punto y coma"""
        resultado = formatear_conectores_activados(["sanciones", "PDVSA", "economia"])
        assert resultado == "sanciones;PDVSA;economia"

    def test_none(self):
        """None debe tratarse como lista vacía"""
        resultado = formatear_conectores_activados(None)
        assert resultado == ""


class TestFormatearListaParaCSV:
    """Tests para formatear_lista_para_csv()"""

    def test_lista_vacia(self):
        """Lista vacía debe devolver string vacío"""
        resultado = formatear_lista_para_csv([])
        assert resultado == ""

    def test_lista_con_elementos(self):
        """Lista con elementos debe separarse por punto y coma"""
        resultado = formatear_lista_para_csv(["a", "b", "c"])
        assert resultado == "a;b;c"


class TestCrearFilaCSV:
    """Tests para crear_fila_csv()"""

    def test_fila_basica(self):
        """Fila básica con todos los campos"""
        hallazgo = {
            "medio_id": "wapo",
            "titulo": "Test Title",
            "url": "https://example.com",
            "fecha": "2024-01-01",
            "tipo_pieza": "nota",
            "enfoque_matriz": "gobierno",
            "valencia": "neutral",
            "valencia_respecto_a": "gobierno",
            "prominencia": "portada",
            "conectores_activados": ["sanciones"],
            "resumen_1_frase": "Test summary"
        }
        medio_config = {
            "id": "wapo",
            "nombre": "Washington Post",
            "region": "eeuu"
        }
        
        fila = crear_fila_csv(hallazgo, medio_config)
        
        assert fila["medio_id"] == "wapo"
        assert fila["medio_nombre"] == "Washington Post"
        assert fila["region"] == "eeuu"
        assert fila["semaforo"] == "VERDE_con_cobertura"
        assert fila["titulo"] == "Test Title"
        assert fila["url"] == "https://example.com"
        assert fila["fecha"] == "2024-01-01"
        assert fila["tipo_pieza"] == "nota"
        assert fila["enfoque_matriz"] == "gobierno"
        assert fila["valencia"] == "neutral"
        assert fila["prominencia"] == "portada"
        assert fila["conectores_activados"] == "sanciones"
        assert fila["resumen_1_frase"] == "Test summary"

    def test_fila_con_campos_faltantes(self):
        """Campos faltantes deben ser strings vacíos"""
        hallazgo = {"medio_id": "test"}
        medio_config = {}
        
        fila = crear_fila_csv(hallazgo, medio_config)
        
        assert fila["medio_id"] == "test"
        assert fila["medio_nombre"] == ""
        assert fila["region"] == "desconocido"
        assert fila["titulo"] == ""
        assert fila["conectores_activados"] == ""

    def test_fila_sin_fecha(self):
        """Fecha None debe ser string vacío"""
        hallazgo = {"medio_id": "test", "fecha": None}
        medio_config = {}
        
        fila = crear_fila_csv(hallazgo, medio_config)
        assert fila["fecha"] == ""


class TestGenerarCSVMatriz:
    """Tests para generar_csv_matriz()"""

    def test_hallazgos_vacios(self):
        """Sin hallazgos debe devolver solo header"""
        csv_content = generar_csv_matriz([], [], "20240101", "MATUTINO")
        lineas = csv_content.strip().split("\n")
        assert len(lineas) == 1  # Solo header
        assert lineas[0] == ",".join(COLUMNAS_CSV)

    def test_un_hallazgo(self):
        """Un hallazgo debe generar header + 1 fila"""
        hallazgos = [{
            "medio_id": "wapo",
            "titulo": "Test",
            "url": "url1",
            "fecha": "2024-01-01",
            "tipo_pieza": "nota",
            "enfoque_matriz": "gobierno",
            "valencia": "neutral",
            "valencia_respecto_a": "gobierno",
            "prominencia": "portada",
            "conectores_activados": ["sanciones"],
            "resumen_1_frase": "Test"
        }]
        medios_config = [{"id": "wapo", "nombre": "Washington Post", "region": "eeuu"}]
        
        csv_content = generar_csv_matriz(hallazgos, medios_config, "20240101", "MATUTINO")
        lineas = csv_content.strip().split("\n")
        assert len(lineas) == 2  # Header + 1 fila

    def test_varios_hallazgos_ordenados(self):
        """Varios hallazgos deben estar ordenados por medio_id"""
        hallazgos = [
            {"medio_id": "bbc", "titulo": "B"},
            {"medio_id": "cnn", "titulo": "C"},
            {"medio_id": "aaa", "titulo": "A"}
        ]
        medios_config = [
            {"id": "aaa", "nombre": "AAA", "region": "x"},
            {"id": "bbc", "nombre": "BBC", "region": "y"},
            {"id": "cnn", "nombre": "CNN", "region": "z"}
        ]
        
        csv_content = generar_csv_matriz(hallazgos, medios_config, "20240101", "MATUTINO")
        lineas = csv_content.strip().split("\n")
        
        # Verificar que las filas están ordenadas por medio_id
        medio_ids = []
        for linea in lineas[1:]:  # Saltar header
            partes = linea.split(",")
            if len(partes) >= 1:
                medio_id = partes[0].strip('"')
                medio_ids.append(medio_id)
        
        assert medio_ids == sorted(medio_ids)

    def test_csv_valido(self):
        """CSV generado debe ser válido"""
        hallazgos = [
            {"medio_id": "m1", "titulo": "Test, with comma", "conectores_activados": ["a", "b"]}
        ]
        medios_config = [{"id": "m1", "nombre": "Medium 1", "region": "x"}]
        
        csv_content = generar_csv_matriz(hallazgos, medios_config, "20240101", "MATUTINO")
        
        # Debería poder parsearse como CSV válido
        reader = csv.DictReader(io.StringIO(csv_content))
        filas = list(reader)
        assert len(filas) == 1
        assert filas[0]["medio_id"] == "m1"
        assert "Test, with comma" in filas[0]["titulo"]


class TestGuardarCSVMatriz:
    """Tests para guardar_csv_matriz()"""

    def test_guardar_csv(self):
        """CSV debe guardarse correctamente en archivo"""
        hallazgos = [{"medio_id": "test", "titulo": "Test"}]
        medios_config = [{"id": "test", "nombre": "Test Medium", "region": "x"}]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = guardar_csv_matriz(
                hallazgos, medios_config, "20240101", "MATUTINO", tmpdir
            )
            
            assert os.path.exists(filepath)
            assert filepath.endswith("matriz_20240101-matutino.csv")
            
            # Verificar contenido
            with open(filepath, "r", encoding="utf-8-sig") as f:
                content = f.read()
            
            assert "medio_id" in content
            assert "test" in content

    def test_directorio_no_existe(self):
        """Directorio debe crearse automáticamente"""
        hallazgos = [{"medio_id": "test", "titulo": "Test"}]
        medios_config = [{"id": "test", "nombre": "Test", "region": "x"}]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, "subdir")
            filepath = guardar_csv_matriz(
                hallazgos, medios_config, "20240101", "MATUTINO", subdir
            )
            
            assert os.path.exists(filepath)
            assert os.path.exists(subdir)


class TestLeerCSVMatriz:
    """Tests para leer_csv_matriz()"""

    def test_leer_archivo_no_existente(self):
        """Archivo no existente debe devolver lista vacía"""
        resultado = leer_csv_matriz("/no/existe/archivo.csv")
        assert resultado == []

    def test_leer_archivo_valido(self):
        """Archivo válido debe parsearse correctamente"""
        csv_content = ",".join(COLUMNAS_CSV) + "\n"
        csv_content += '"m1","Medium 1","eeuu","VERDE_con_cobertura","Title","url",,,,,,,,"\n'
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(csv_content)
            filepath = f.name
        
        try:
            resultado = leer_csv_matriz(filepath)
            assert len(resultado) == 1
            assert resultado[0]["medio_id"] == "m1"
            assert resultado[0]["medio_nombre"] == "Medium 1"
        finally:
            os.unlink(filepath)


class TestGenerarNombreArchivoCSV:
    """Tests para generar_nombre_archivo_csv()"""

    def test_formato_fecha(self):
        """Fecha debe estar en formato YYYYMMDD"""
        fecha, corte = generar_nombre_archivo_csv()
        assert len(fecha) == 8
        assert fecha.isdigit()

    def test_corte_valido(self):
        """Corte debe ser MATUTINO o VESPERTINO"""
        _, corte = generar_nombre_archivo_csv()
        assert corte in ["MATUTINO", "VESPERTINO"]
