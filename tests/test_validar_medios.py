"""
Tests para radar/validar_medios.py
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from radar.validar_medios import (
    es_url_valida,
    extraer_rss_de_html,
    descubrir_feed,
    validar_medio,
    validar_todos_medios,
    generar_reporte,
    guardar_reporte_json,
    actualizar_config_medios,
)


class TestEsUrlValida:
    """Tests para es_url_valida()"""

    def test_url_http_valida(self):
        assert es_url_valida("http://ejemplo.com/rss") is True

    def test_url_https_valida(self):
        assert es_url_valida("https://ejemplo.com/feed") is True

    def test_url_sin_protocolo_invalida(self):
        assert es_url_valida("ejemplo.com/rss") is False

    def test_url_sin_dominio_invalida(self):
        assert es_url_valida("http:///rss") is False

    def test_url_vacia_invalida(self):
        assert es_url_valida("") is False

    def test_url_none_invalida(self):
        assert es_url_valida(None) is False


class TestExtraerRssDeHtml:
    """Tests para extraer_rss_de_html()"""

    def test_html_con_link_rss(self):
        html = '<html><head><link rel="alternate" type="application/rss+xml" href="https://ejemplo.com/rss" /></head></html>'
        rss_url = extraer_rss_de_html(html, "https://ejemplo.com")
        assert rss_url == "https://ejemplo.com/rss"

    def test_html_con_link_rss_relativo(self):
        html = '<html><head><link rel="alternate" type="application/rss+xml" href="/rss" /></head></html>'
        rss_url = extraer_rss_de_html(html, "https://ejemplo.com")
        assert rss_url == "https://ejemplo.com/rss"

    def test_html_con_link_atom(self):
        html = '<html><head><link rel="alternate" type="application/atom+xml" href="https://ejemplo.com/atom.xml" /></head></html>'
        rss_url = extraer_rss_de_html(html, "https://ejemplo.com")
        assert rss_url == "https://ejemplo.com/atom.xml"

    def test_html_sin_rss(self):
        html = "<html><body>Sin RSS</body></html>"
        rss_url = extraer_rss_de_html(html, "https://ejemplo.com")
        assert rss_url is None


class TestDescubrirFeed:
    """Tests para descubrir_feed() - mocking fetch_url y probar_feed_rss"""

    @patch("radar.validar_medios.probar_feed_rss")
    @patch("radar.validar_medios.fetch_url")
    def test_descubrir_feed_en_rss(self, mock_fetch, mock_probar):
        # Configurar mocks
        mock_probar.return_value = (True, "https://ejemplo.com/rss", None)
        
        rss_url, status = descubrir_feed("https://ejemplo.com")
        
        assert rss_url == "https://ejemplo.com/rss"
        assert status == "OK"
        # Debería haber probado /rss primero
        assert mock_probar.call_count == 1

    @patch("radar.validar_medios.probar_feed_rss")
    @patch("radar.validar_medios.fetch_url")
    def test_descubrir_feed_en_feed(self, mock_fetch, mock_probar):
        # Configurar mocks: /rss falla, /feed funciona
        mock_probar.side_effect = [
            (False, "https://ejemplo.com/rss", "No válido"),
            (True, "https://ejemplo.com/feed", None),
        ]
        
        rss_url, status = descubrir_feed("https://ejemplo.com")
        
        assert rss_url == "https://ejemplo.com/feed"
        assert status == "OK"

    @patch("radar.validar_medios.probar_feed_rss")
    @patch("radar.validar_medios.fetch_url")
    @patch("radar.validar_medios.extraer_rss_de_html")
    def test_descubrir_feed_desde_portada(self, mock_extraer, mock_fetch, mock_probar):
        # Configurar mocks: todos los sufijos fallan, pero el HTML tiene link
        mock_probar.return_value = (False, "", "No válido")
        mock_fetch.return_value = (True, "<html>...</html>", None)
        mock_extraer.return_value = "https://ejemplo.com/feed.xml"
        
        # Mock para verificar el feed encontrado
        with patch("radar.validar_medios.probar_feed_rss") as mock_probar2:
            mock_probar2.return_value = (True, "https://ejemplo.com/feed.xml", None)
            rss_url, status = descubrir_feed("https://ejemplo.com")
            
            assert rss_url == "https://ejemplo.com/feed.xml"
            assert status == "OK"

    @patch("radar.validar_medios.probar_feed_rss")
    @patch("radar.validar_medios.fetch_url")
    @patch("radar.validar_medios.extraer_rss_de_html")
    def test_descubrir_feed_sin_feed(self, mock_extraer, mock_fetch, mock_probar):
        # Configurar mocks: todo falla
        mock_probar.return_value = (False, "", "No válido")
        mock_fetch.return_value = (True, "<html>...</html>", None)
        mock_extraer.return_value = None
        
        rss_url, status = descubrir_feed("https://ejemplo.com")
        
        assert rss_url is None
        assert status == "SIN_FEED"

    def test_descubrir_feed_url_invalida(self):
        rss_url, status = descubrir_feed("url-invalida")
        assert rss_url is None
        assert status == "ERROR"


class TestValidarMedio:
    """Tests para validar_medio()"""

    @patch("radar.validar_medios.probar_feed_rss")
    def test_medio_con_rss_valido(self, mock_probar):
        mock_probar.return_value = (True, "https://ejemplo.com/rss", None)
        
        medio = {
            "id": "test1",
            "nombre": "Test",
            "rss_url": "https://ejemplo.com/rss",
            "url": "https://ejemplo.com"
        }
        
        resultado = validar_medio(medio)
        
        assert resultado["id"] == "test1"
        assert resultado["status"] == "OK"
        assert resultado["rss_url_validado"] == "https://ejemplo.com/rss"

    @patch("radar.validar_medios.probar_feed_rss")
    @patch("radar.validar_medios.descubrir_feed")
    def test_medio_con_rss_invalido_pero_descubrible(self, mock_descubrir, mock_probar):
        mock_probar.return_value = (False, "https://ejemplo.com/rss", "Error")
        mock_descubrir.return_value = ("https://ejemplo.com/feed", "OK")
        
        medio = {
            "id": "test2",
            "nombre": "Test",
            "rss_url": "https://ejemplo.com/rss",
            "url": "https://ejemplo.com"
        }
        
        resultado = validar_medio(medio)
        
        assert resultado["id"] == "test2"
        assert resultado["status"] == "CORREGIDO"
        assert resultado["rss_url_validado"] == "https://ejemplo.com/feed"

    @patch("radar.validar_medios.descubrir_feed")
    def test_medio_sin_rss_descubierto(self, mock_descubrir):
        mock_descubrir.return_value = ("https://ejemplo.com/feed", "OK")
        
        medio = {
            "id": "test3",
            "nombre": "Test",
            "rss_url": None,
            "url": "https://ejemplo.com"
        }
        
        resultado = validar_medio(medio)
        
        assert resultado["id"] == "test3"
        assert resultado["status"] == "CORREGIDO"

    @patch("radar.validar_medios.descubrir_feed")
    def test_medio_sin_rss_no_descubierto(self, mock_descubrir):
        mock_descubrir.return_value = (None, "SIN_FEED")
        
        medio = {
            "id": "test4",
            "nombre": "Test",
            "rss_url": None,
            "url": "https://ejemplo.com"
        }
        
        resultado = validar_medio(medio)
        
        assert resultado["id"] == "test4"
        assert resultado["status"] == "SIN_FEED"


class TestValidarTodosMedios:
    """Tests para validar_todos_medios()"""

    @patch("radar.validar_medios.validar_medio")
    def test_validar_todos_medios(self, mock_validar):
        # Configurar mocks para diferentes resultados
        # Nota: el status debe ser uno de los válidos: OK, CORREGIDO, SIN_FEED
        # "ERROR" no es un status válido en el código actual
        mock_validar.side_effect = [
            {"id": "m1", "status": "OK", "rss_url_validado": "url1", "error": None},
            {"id": "m2", "status": "CORREGIDO", "rss_url_validado": "url2", "error": None},
            {"id": "m3", "status": "SIN_FEED", "rss_url_validado": None, "error": None},
            {"id": "m4", "status": "SIN_FEED", "rss_url_validado": None, "error": "Timeout"},
        ]
        
        medios = [
            {"id": "m1", "rss_url": "url1"},
            {"id": "m2", "rss_url": None},
            {"id": "m3", "rss_url": None},
            {"id": "m4", "rss_url": "bad_url"},
        ]
        
        resultados = validar_todos_medios(medios, verbose=False)
        
        assert resultados["total"] == 4
        assert len(resultados["ok"]) == 1
        assert len(resultados["corregido"]) == 1
        assert len(resultados["sin_feed"]) == 2
        assert len(resultados["errores"]) == 0
        assert resultados["resumen"]["ok"] == 1
        assert resultados["resumen"]["corregido"] == 1
        assert resultados["resumen"]["sin_feed"] == 2


class TestGenerarReporte:
    """Tests para generar_reporte()"""

    def test_generar_reporte_con_todo(self):
        resultados = {
            "total": 4,
            "ok": [{"id": "m1", "rss_url_validado": "url1", "status": "OK", "error": None}],
            "corregido": [{"id": "m2", "rss_url_validado": "url2", "status": "CORREGIDO", "error": None}],
            "sin_feed": [{"id": "m3", "rss_url_validado": None, "status": "SIN_FEED", "error": None}],
            "errores": [{"id": "m4", "rss_url_validado": None, "status": "ERROR", "error": "Timeout"}],
            "resumen": {"ok": 1, "corregido": 1, "sin_feed": 1, "errores": 1}
        }
        
        reporte = generar_reporte(resultados)
        
        assert "REPORTE DE VALIDACIÓN DE MEDIOS" in reporte
        assert "🟢 FEEDS OK:" in reporte
        assert "🟡 FEEDS CORREGIDOS:" in reporte
        assert "⚪ SIN FEED" in reporte
        assert "❌ ERRORES:" in reporte

    def test_generar_reporte_vacio(self):
        resultados = {
            "total": 0,
            "ok": [],
            "corregido": [],
            "sin_feed": [],
            "errores": [],
            "resumen": {"ok": 0, "corregido": 0, "sin_feed": 0, "errores": 0}
        }
        
        reporte = generar_reporte(resultados)
        
        assert "Total de medios: 0" in reporte


class TestGuardarReporteJson:
    """Tests para guardar_reporte_json()"""

    def test_guardar_reporte_json(self):
        resultados = {"total": 1, "ok": [], "corregido": [], "sin_feed": [], "errores": []}
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name
        
        try:
            assert guardar_reporte_json(resultados, temp_path) is True
            
            # Verificar contenido
            with open(temp_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            assert data["total"] == 1
        finally:
            os.unlink(temp_path)


class TestActualizarConfigMedios:
    """Tests para actualizar_config_medios()"""

    def test_actualizar_config_con_feeds_ok(self):
        # Crear config temporal
        config = {
            "_comentario": "Test",
            "version": "1.0",
            "medios": [
                {"id": "m1", "nombre": "Test1", "rss_url": None, "url": "https://test1.com"},
                {"id": "m2", "nombre": "Test2", "rss_url": None, "url": "https://test2.com"}
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            temp_path = f.name
        
        try:
            resultados = {
                "total": 2,
                "ok": [{"id": "m1", "rss_url_validado": "https://test1.com/rss"}],
                "corregido": [{"id": "m2", "rss_url_validado": "https://test2.com/feed"}],
                "sin_feed": [],
                "errores": [],
                "resumen": {"ok": 1, "corregido": 1, "sin_feed": 0, "errores": 0}
            }
            
            assert actualizar_config_medios(temp_path, resultados) is True
            
            # Verificar actualización
            with open(temp_path, "r", encoding="utf-8") as f:
                config_actualizado = json.load(f)
            
            m1 = next(m for m in config_actualizado["medios"] if m["id"] == "m1")
            assert m1["rss_url"] == "https://test1.com/rss"
            
            m2 = next(m for m in config_actualizado["medios"] if m["id"] == "m2")
            assert m2["rss_url"] == "https://test2.com/feed"
        finally:
            os.unlink(temp_path)

    def test_actualizar_config_sin_cambios(self):
        # Medios sin cambios (sin_feed y errores)
        config = {
            "medios": [
                {"id": "m1", "nombre": "Test1", "rss_url": None, "url": "https://test1.com"}
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            temp_path = f.name
        
        try:
            resultados = {
                "total": 1,
                "ok": [],
                "corregido": [],
                "sin_feed": [{"id": "m1", "rss_url_validado": None}],
                "errores": [],
                "resumen": {"ok": 0, "corregido": 0, "sin_feed": 1, "errores": 0}
            }
            
            assert actualizar_config_medios(temp_path, resultados) is True
            
            # Verificar que no se cambió (sigue None)
            with open(temp_path, "r", encoding="utf-8") as f:
                config_actualizado = json.load(f)
            
            m1 = config_actualizado["medios"][0]
            assert m1["rss_url"] is None
        finally:
            os.unlink(temp_path)
