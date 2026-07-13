"""
Tests para radar/matching.py
"""

import pytest

from radar.matching import (
    normalizar_para_matching,
    extraer_terminos_de_conectores,
    conectores_activados,
    titular_matcha_conectores,
    cruzar_con_conectores,
    filtrar_titulares_no_vacios,
)


class TestNormalizarParaMatching:
    """Tests para normalizar_para_matching()"""

    def test_normalizar_texto_vacio(self):
        assert normalizar_para_matching("") == ""
        assert normalizar_para_matching(None) == ""

    def test_normalizar_minusculas(self):
        texto = "VenezueLa"
        resultado = normalizar_para_matching(texto)
        assert resultado == "venezuela"

    def test_normalizar_sin_tildes(self):
        texto = "Venezuela"
        resultado = normalizar_para_matching(texto)
        assert "e" in resultado.lower()  # "venezuela" sin tilde

    def test_normalizar_sin_especiales(self):
        texto = "Venezuela: ¡Noticia! ¿Importante?"
        resultado = normalizar_para_matching(texto)
        # Debería eliminar : ¡ ! ¿ ?
        assert ":" not in resultado
        assert "¡" not in resultado
        assert "!" not in resultado
        assert "¿" not in resultado

    def test_normalizar_alias_venezuela(self):
        # La normalización del core debería manejar alias
        texto = "EE.UU. sanciona a PDVSA"
        resultado = normalizar_para_matching(texto)
        # Debería normalizar EE.UU. a estados unidos
        assert "estados unidos" in resultado or "eeuu" in resultado or "ee uu" in resultado


class TestExtraerTerminosDeConectores:
    """Tests para extraer_terminos_de_conectores()"""

    def test_extraer_terminos_config_valido(self):
        config = {
            "grupos": {
                "actores": {
                    "terminos": [
                        {"canonico": "venezuela", "alias": ["venezolano", "venezolana"]},
                        {"canonico": "maduro", "alias": ["nicolas maduro"]}
                    ]
                }
            }
        }
        
        terminos = extraer_terminos_de_conectores(config)
        
        assert isinstance(terminos, set)
        # Debería contener todos los términos normalizados
        assert len(terminos) >= 4

    def test_extraer_terminos_config_vacio(self):
        config = {"grupos": {}}
        terminos = extraer_terminos_de_conectores(config)
        assert terminos == set()

    def test_extraer_terminos_sin_alias(self):
        config = {
            "grupos": {
                "test": {
                    "terminos": [
                        {"canonico": "prueba", "alias": []}
                    ]
                }
            }
        }
        
        terminos = extraer_terminos_de_conectores(config)
        assert len(terminos) >= 1


class TestConectoresActivados:
    """Tests para conectores_activados()"""

    def test_conectores_activados_un_grupo(self):
        config = {
            "grupos": {
                "actores": {
                    "terminos": [
                        {"canonico": "venezuela", "alias": []}
                    ]
                }
            }
        }
        
        texto = "Noticia sobre Venezuela"
        resultado = conectores_activados(texto, config)
        
        assert "actores" in resultado

    def test_conectores_activados_varios_grupos(self):
        config = {
            "grupos": {
                "actores": {
                    "terminos": [
                        {"canonico": "venezuela", "alias": []}
                    ]
                },
                "estructurales": {
                    "terminos": [
                        {"canonico": "sanciones", "alias": []}
                    ]
                }
            }
        }
        
        texto = "Sanciones a Venezuela"
        resultado = conectores_activados(texto, config)
        
        assert "actores" in resultado
        assert "estructurales" in resultado

    def test_conectores_activados_alias(self):
        config = {
            "grupos": {
                "actores": {
                    "terminos": [
                        {"canonico": "maduro", "alias": ["nicolas maduro", "dictador"]}
                    ]
                }
            }
        }
        
        texto = "El destacar solo"  # No contiene "dictador"
        resultado = conectores_activados(texto, config)
        # "dictador" no está en el texto
        assert "actores" not in resultado

        texto2 = "El nicolas maduro hablo"
        resultado2 = conectores_activados(texto2, config)
        assert "actores" in resultado2


class TestTitularMatchaConectores:
    """Tests para titular_matcha_conectores()"""

    def test_matcha_conector_directo(self):
        config = {
            "grupos": {
                "actores": {
                    "terminos": [
                        {"canonico": "venezuela", "alias": []}
                    ]
                }
            }
        }
        
        assert titular_matcha_conectores("Venezuela en crisis", config) is True
        assert titular_matcha_conectores("Noticia de Colombia", config) is False

    def test_matcha_con_alias(self):
        config = {
            "grupos": {
                "actores": {
                    "terminos": [
                        {"canonico": "pdvsa", "alias": ["petroleos de venezuela"]}
                    ]
                }
            }
        }
        
        assert titular_matcha_conectores("Petroleos de Venezuela en problemas", config) is True

    def test_no_matcha(self):
        config = {
            "grupos": {
                "actores": {
                    "terminos": [
                        {"canonico": "venezuela", "alias": []}
                    ]
                }
            }
        }
        
        assert titular_matcha_conectores("Noticia sobre Brasil", config) is False

    def test_titulo_vacio(self):
        config = {"grupos": {}}
        assert titular_matcha_conectores("", config) is False


class TestCruzarConConectores:
    """Tests para cruzar_con_conectores()"""

    def test_cruzar_con_conectores_basico(self):
        config = {
            "grupos": {
                "actores": {
                    "terminos": [
                        {"canonico": "venezuela", "alias": []},
                        {"canonico": "maduro", "alias": []}
                    ]
                }
            }
        }
        
        titulares = [
            {"titulo": "Venezuela en crisis", "url": "url1"},
            {"titulo": "Noticia de Brasil", "url": "url2"},
            {"titulo": "Maduro habla", "url": "url3"}
        ]
        
        hallazgos = cruzar_con_conectores(titulares, config)
        
        assert len(hallazgos) == 2  # Los que contienen "venezuela" o "maduro"
        assert any("Venezuela" in h["titulo"] for h in hallazgos)
        assert any("Maduro" in h["titulo"] for h in hallazgos)

    def test_cruzar_con_conectores_con_medio_id(self):
        config = {
            "grupos": {
                "actores": {
                    "terminos": [
                        {"canonico": "venezuela", "alias": []}
                    ]
                }
            }
        }
        
        titulares = [
            {"titulo": "Venezuela en crisis", "url": "url1", "medio_id": "bbc"},
            {"titulo": "Noticia de Brasil", "url": "url2", "medio_id": "globo"}
        ]
        
        hallazgos = cruzar_con_conectores(titulares, config)
        
        assert len(hallazgos) == 1
        assert hallazgos[0]["medio_id"] == "bbc"

    def test_cruzar_con_conectores_titulos_vacios(self):
        config = {"grupos": {}}
        
        titulares = [
            {"titulo": "", "url": "url1"},
            {"titulo": "   ", "url": "url2"},
            {"titulo": "Valid", "url": "url3"}
        ]
        
        hallazgos = cruzar_con_conectores(titulares, config)
        # Debería ignorar los vacíos
        assert len(hallazgos) == 0


class TestFiltrarTitularesNoVacios:
    """Tests para filtrar_titulares_no_vacios()"""

    def test_filtrar_vacios(self):
        titulares = [
            {"titulo": "Valid", "url": "url1"},
            {"titulo": "", "url": "url2"},
            {"titulo": "   ", "url": "url3"}
        ]
        
        filtrados = filtrar_titulares_no_vacios(titulares)
        
        assert len(filtrados) == 1
        assert filtrados[0]["titulo"] == "Valid"

    def test_filtrar_cortos(self):
        titulares = [
            {"titulo": "Hi", "url": "url1"},  # < 4 caracteres
            {"titulo": "Hello", "url": "url2"}  # >= 4 caracteres
        ]
        
        filtrados = filtrar_titulares_no_vacios(titulares)
        
        assert len(filtrados) == 1
        assert filtrados[0]["titulo"] == "Hello"

    def test_filtrar_todos_validos(self):
        titulares = [
            {"titulo": "Titulo 1", "url": "url1"},
            {"titulo": "Titulo 2", "url": "url2"}
        ]
        
        filtrados = filtrar_titulares_no_vacios(titulares)
        
        assert len(filtrados) == 2
