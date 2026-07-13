"""
Tests de validación de config/reporte.json contra el schema de centinela-core
"""

import json
import pytest
from pathlib import Path


class TestConfigEstructura:
    """Tests para validar estructura básica de los archivos config"""

    def test_reporte_json_existe(self):
        """Verificar que config/reporte.json existe"""
        path = Path("config/reporte.json")
        assert path.exists(), f"Archivo {path} no encontrado"

    def test_reporte_json_es_valido_json(self):
        """Verificar que config/reporte.json es JSON válido"""
        with open("config/reporte.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict), "reporte.json debe ser un objeto JSON"

    def test_reporte_json_tiene_campos_obligatorios(self):
        """Verificar campos obligatorios en reporte.json"""
        with open("config/reporte.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        campos_obligatorios = [
            "canal",
            "nombre_visible",
            "banda_color",
            "crons_utc",
            "ventana",
            "pages_ruta",
            "consultas_perplexity",
            "semaforo",
            "presupuesto",
            "secciones_activas"
        ]
        
        for campo in campos_obligatorios:
            assert campo in data, f"Campo obligatorio '{campo}' no encontrado en reporte.json"

    def test_reporte_json_canal_es_radar(self):
        """Verificar que el canal es 'radar'"""
        with open("config/reporte.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["canal"] == "radar", "El canal debe ser 'radar'"

    def test_reporte_json_nombre_visible_tiene_emoji(self):
        """Verificar que nombre_visible tiene el emoji de RADAR"""
        with open("config/reporte.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        nombre = data["nombre_visible"]
        assert "📡" in nombre, f"nombre_visible debe contener emoji 📡, encontrado: {nombre}"

    def test_reporte_json_banda_color_es_hex(self):
        """Verificar que banda_color es un código hex válido"""
        with open("config/reporte.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        color = data["banda_color"]
        assert color.startswith("#"), f"banda_color debe empezar con #, encontrado: {color}"
        assert len(color) == 7, f"banda_color debe tener 7 caracteres, encontrado: {color}"

    def test_reporte_json_crons_utc_es_lista(self):
        """Verificar que crons_utc es una lista"""
        with open("config/reporte.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data["crons_utc"], list), "crons_utc debe ser una lista"
        assert len(data["crons_utc"]) == 2, "Debe haber 2 crons (matutino y vespertino)"

    def test_reporte_json_consultas_perplexity_es_lista(self):
        """Verificar que consultas_perplexity es una lista"""
        with open("config/reporte.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        consultas = data["consultas_perplexity"]
        assert isinstance(consultas, list), "consultas_perplexity debe ser una lista"
        assert len(consultas) == 8, f"Debe haber 8 consultas por región, encontradas: {len(consultas)}"

    def test_reporte_json_consultas_tienen_campos(self):
        """Verificar que cada consulta tiene los campos necesarios"""
        with open("config/reporte.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        for consulta in data["consultas_perplexity"]:
            assert "id" in consulta, "Cada consulta debe tener 'id'"
            assert "region" in consulta, "Cada consulta debe tener 'region'"
            assert "modelo" in consulta, "Cada consulta debe tener 'modelo'"
            assert "query" in consulta, "Cada consulta debe tener 'query'"

    def test_reporte_json_semaforo_tiene_estados(self):
        """Verificar que semáforo tiene estados definidos"""
        with open("config/reporte.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        semaforo = data["semaforo"]
        assert "estados" in semaforo, "semaforo debe tener 'estados'"
        assert isinstance(semaforo["estados"], list), "estados debe ser una lista"
        assert len(semaforo["estados"]) == 3, "Debe tener 3 estados: VERDE, AMARILLO, ROJO"

    def test_reporte_json_presupuesto_existe(self):
        """Verificar que presupuesto existe y tiene campos"""
        with open("config/reporte.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        presupuesto = data["presupuesto"]
        assert isinstance(presupuesto, dict), "presupuesto debe ser un dict"
        assert "max_llamadas_busqueda" in presupuesto, "presupuesto debe tener max_llamadas_busqueda"
        assert "max_reintentos_totales" in presupuesto, "presupuesto debe tener max_reintentos_totales"

    def test_reporte_json_secciones_activas_existe(self):
        """Verificar que secciones_activas existe y es una lista"""
        with open("config/reporte.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        secciones = data["secciones_activas"]
        assert isinstance(secciones, list), "secciones_activas debe ser una lista"
        # Verificar secciones clave del RADAR
        assert "tablero_certificacion" in secciones, "Debe incluir tablero_certificacion"
        assert "top5_venezuela" in secciones, "Debe incluir top5_venezuela"
        assert "top10_global" in secciones, "Debe incluir top10_global"


class TestConfigRadarMedios:
    """Tests para validar config/radar_medios.json"""

    def test_radar_medios_existe(self):
        """Verificar que config/radar_medios.json existe"""
        path = Path("config/radar_medios.json")
        assert path.exists(), f"Archivo {path} no encontrado"

    def test_radar_medios_es_valido_json(self):
        """Verificar que config/radar_medios.json es JSON válido"""
        with open("config/radar_medios.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict), "radar_medios.json debe ser un dict"
        assert "medios" in data, "radar_medios.json debe tener clave 'medios'"

    def test_radar_medios_tiene_35_medios(self):
        """Verificar que hay aproximadamente 35 medios"""
        with open("config/radar_medios.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        medios = data.get("medios", [])
        # El doc dice ~35 medios
        assert len(medios) >= 30, f"Se esperan ~35 medios, encontrados: {len(medios)}"

    def test_radar_medios_cada_medio_tiene_id(self):
        """Verificar que cada medio tiene un id"""
        with open("config/radar_medios.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        for medio in data.get("medios", []):
            assert "id" in medio, f"Cada medio debe tener 'id'"

    def test_radar_medios_campos_obligatorios(self):
        """Verificar campos obligatorios en cada medio"""
        with open("config/radar_medios.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Campos obligatorios: id, nombre, region, rss_url, y url (portada_url o url)
        for medio in data.get("medios", []):
            assert "id" in medio, f"Campo 'id' no encontrado en medio {medio.get('id', 'desconocido')}"
            assert "nombre" in medio, f"Campo 'nombre' no encontrado en medio {medio.get('id', 'desconocido')}"
            assert "region" in medio, f"Campo 'region' no encontrado en medio {medio.get('id', 'desconocido')}"
            # rss_url puede ser null (a descubrir) pero debe existir el campo
            assert "rss_url" in medio, f"Campo 'rss_url' no encontrado en medio {medio.get('id', 'desconocido')}"
            # URL de referencia (portada_url o url)
            assert "portada_url" in medio or "url" in medio, f"Campo 'portada_url' o 'url' no encontrado en medio {medio.get('id', 'desconocido')}"


class TestConfigConectores:
    """Tests para validar config/conectores.json"""

    def test_conectores_existe(self):
        """Verificar que config/conectores.json existe"""
        path = Path("config/conectores.json")
        assert path.exists(), f"Archivo {path} no encontrado"

    def test_conectores_es_valido_json(self):
        """Verificar que config/conectores.json es JSON válido"""
        with open("config/conectores.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict), "conectores.json debe ser un dict"

    def test_conectores_tiene_categorias(self):
        """Verificar que conectores tiene categorías"""
        with open("config/conectores.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Debería tener grupos con categorías como actores, estructurales, coyuntura
        assert "grupos" in data, "conectores.json debe tener clave 'grupos'"
        grupos = data.get("grupos", {})
        assert "actores" in grupos, "grupos debe tener 'actores'"
        assert "estructurales" in grupos, "grupos debe tener 'estructurales'"
        assert "coyuntura" in grupos, "grupos debe tener 'coyuntura'"
