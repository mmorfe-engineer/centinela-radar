"""
Tests para radar/fetch_rss.py
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch, Mock

import pytest

from radar.fetch_rss import (
    obtener_headers,
    es_url_valida,
    fetch_url,
    parse_feed,
    parse_portada,
    fetch_medio,
    fetch_todos_medios,
)


class TestObtenerHeaders:
    """Tests para obtener_headers()"""

    def test_headers_tiene_user_agent(self):
        headers = obtener_headers()
        assert "User-Agent" in headers
        assert "CENTINELA-RADAR" in headers["User-Agent"]

    def test_headers_tiene_accept(self):
        headers = obtener_headers()
        assert "Accept" in headers


class TestEsUrlValida:
    """Tests para es_url_valida()"""

    def test_url_http_valida(self):
        assert es_url_valida("http://ejemplo.com") is True

    def test_url_https_valida(self):
        assert es_url_valida("https://ejemplo.com/rss") is True

    def test_url_sin_protocolo_invalida(self):
        assert es_url_valida("ejemplo.com") is False

    def test_url_sin_dominio_invalida(self):
        assert es_url_valida("http://") is False

    def test_url_vacia_invalida(self):
        assert es_url_valida("") is False

    def test_url_none_invalida(self):
        assert es_url_valida(None) is False


class TestFetchUrl:
    """Tests para fetch_url() - con mocks de requests"""

    @patch("radar.fetch_rss.requests.get")
    @patch("radar.fetch_rss.time.sleep")
    def test_fetch_url_exitoso(self, mock_sleep, mock_get):
        # Configurar mock
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<rss>...</rss>"
        mock_get.return_value = mock_response
        
        exito, contenido, error = fetch_url("https://ejemplo.com")
        
        assert exito is True
        assert contenido == "<rss>...</rss>"
        assert error is None

    @patch("radar.fetch_rss.requests.get")
    def test_fetch_url_404(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        exito, contenido, error = fetch_url("https://ejemplo.com/404")
        
        assert exito is False
        assert contenido is None
        assert "HTTP 404" in error

    @patch("radar.fetch_rss.requests.get")
    def test_fetch_url_403_paywall(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response
        
        exito, contenido, error = fetch_url("https://ejemplo.com/paywall")
        
        assert exito is False
        assert contenido is None
        assert "Bloqueado" in error

    @patch("radar.fetch_rss.requests.get")
    def test_fetch_url_timeout(self, mock_get):
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()
        
        exito, contenido, error = fetch_url("https://ejemplo.com")
        
        assert exito is False
        assert contenido is None
        assert "Timeout" in error


class TestParseFeed:
    """Tests para parse_feed()"""

    def test_parse_feed_rss_valido(self):
        xml = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Test Title 1</title>
                    <link>https://ejemplo.com/1</link>
                </item>
                <item>
                    <title>Test Title 2</title>
                    <link>https://ejemplo.com/2</link>
                </item>
            </channel>
        </rss>"""
        
        titulares = parse_feed(xml, "https://ejemplo.com")
        
        assert len(titulares) == 2
        assert titulares[0]["titulo"] == "Test Title 1"
        assert titulares[0]["url"] == "https://ejemplo.com/1"

    def test_parse_feed_atom_valido(self):
        xml = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <title>Atom Title</title>
                <link href="https://ejemplo.com/atom"/>
            </entry>
        </feed>"""
        
        titulares = parse_feed(xml, "https://ejemplo.com")
        
        assert len(titulares) == 1
        assert titulares[0]["titulo"] == "Atom Title"

    def test_parse_feed_vacio(self):
        xml = "<rss><channel></channel></rss>"
        titulares = parse_feed(xml, "https://ejemplo.com")
        assert len(titulares) == 0

    def test_parse_feed_invalido(self):
        xml = "Este no es XML válido"
        titulares = parse_feed(xml, "https://ejemplo.com")
        assert len(titulares) == 0

    def test_parse_feed_url_relativa(self):
        xml = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Test</title>
                    <link>/article/123</link>
                </item>
            </channel>
        </rss>"""
        
        titulares = parse_feed(xml, "https://ejemplo.com")
        
        assert len(titulares) == 1
        assert titulares[0]["url"] == "https://ejemplo.com/article/123"


class TestParsePortada:
    """Tests para parse_portada()"""

    def test_parse_portada_con_h1(self):
        html = "<html><body><h1>Titular Principal</h1></body></html>"
        titulares = parse_portada(html, "https://ejemplo.com")
        
        # Debería encontrar al menos el h1
        assert len(titulares) >= 1
        # Verificar que hay un titular con texto
        texts = [t.get("titulo", "") for t in titulares]
        assert any("Titular" in t for t in texts)

    def test_parse_portada_con_etiquetas(self):
        html = """
        <html>
        <body>
            <h1>Titulo 1</h1>
            <h2>Titulo 2</h2>
            <h3>Titulo 3</h3>
        </body>
        </html>
        """
        titulares = parse_portada(html, "https://ejemplo.com")
        assert len(titulares) >= 3

    def test_parse_portada_sin_titulares(self):
        html = "<html><body><p>Solo párrafo</p></body></html>"
        titulares = parse_portada(html, "https://ejemplo.com")
        # Podría devolver vacío o encontrar algo
        # Lo importante es que no falle
        assert isinstance(titulares, list)


class TestFetchMedio:
    """Tests para fetch_medio()"""

    @patch("radar.fetch_rss.fetch_url")
    @patch("radar.fetch_rss.parse_feed")
    def test_fetch_medio_con_rss(self, mock_parse, mock_fetch):
        # Configurar mocks
        mock_fetch.return_value = (True, "<rss>...</rss>", None)
        mock_parse.return_value = [{"titulo": "Test", "url": "http://test.com"}]
        
        medio = {
            "id": "test1",
            "nombre": "Test",
            "rss_url": "https://test.com/rss",
            "url": "https://test.com"
        }
        
        resultado = fetch_medio(medio)
        
        assert resultado["id"] == "test1"
        assert resultado["exito"] is True
        assert resultado["es_rss"] is True
        assert resultado["es_portada"] is False
        assert len(resultado["titulares"]) == 1

    @patch("radar.fetch_rss.fetch_url")
    @patch("radar.fetch_rss.parse_feed")
    @patch("radar.fetch_rss.parse_portada")
    def test_fetch_medio_rss_falla_portada_ok(self, mock_parse_portada, mock_parse_feed, mock_fetch):
        # RSS falla, portada funciona
        mock_fetch.side_effect = [
            (False, None, "HTTP 404"),  # RSS falla
            (True, "<html>...</html>", None)  # Portada funciona
        ]
        mock_parse_feed.return_value = []  # RSS no parsea
        mock_parse_portada.return_value = [{"titulo": "From Portada", "url": None}]
        
        medio = {
            "id": "test2",
            "nombre": "Test",
            "rss_url": "https://test.com/rss",
            "url": "https://test.com"
        }
        
        resultado = fetch_medio(medio)
        
        assert resultado["id"] == "test2"
        assert resultado["exito"] is True
        assert resultado["es_rss"] is False
        assert resultado["es_portada"] is True

    @patch("radar.fetch_rss.fetch_url")
    def test_fetch_medio_todo_falla(self, mock_fetch):
        mock_fetch.return_value = (False, None, "Timeout")
        
        medio = {
            "id": "test3",
            "nombre": "Test",
            "rss_url": "https://test.com/rss",
            "url": "https://test.com"
        }
        
        resultado = fetch_medio(medio)
        
        assert resultado["id"] == "test3"
        assert resultado["exito"] is False
        assert "Timeout" in resultado["error"]

    def test_fetch_medio_sin_urls(self):
        medio = {
            "id": "test4",
            "nombre": "Test"
        }
        
        resultado = fetch_medio(medio)
        
        assert resultado["id"] == "test4"
        assert resultado["exito"] is False
        assert "No hay URLs válidas" in resultado["error"]


class TestFetchTodosMedios:
    """Tests para fetch_todos_medios()"""

    @patch("radar.fetch_rss.fetch_medio")
    def test_fetch_todos_medios(self, mock_fetch):
        # Configurar mock para múltiples medios
        mock_fetch.side_effect = [
            {"id": "m1", "exito": True, "titulares": [{"titulo": "T1"}], "error": None},
            {"id": "m2", "exito": False, "titulares": [], "error": "Timeout"},
            {"id": "m3", "exito": True, "titulares": [{"titulo": "T3"}], "error": None},
        ]
        
        medios = [
            {"id": "m1", "rss_url": "url1"},
            {"id": "m2", "rss_url": "url2"},
            {"id": "m3", "rss_url": "url3"},
        ]
        
        resultado = fetch_todos_medios(medios)
        
        assert len(resultado["medios"]) == 3
        assert len(resultado["titulares_todos"]) == 2  # m1 y m3
        assert len(resultado["errores"]) == 1  # m2
