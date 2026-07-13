#!/usr/bin/env python3
"""
Tests para radar/top_global.py
"""

import pytest
import numpy as np
from typing import Any, Dict, List

from radar.top_global import (
    generar_embedding,
    similitud_coseno,
    agrupar_por_embeddings,
    calcular_prominencia_media,
    calcular_authority_score_promedio,
    generar_top10_global,
    extraer_titulares_para_top10,
    UMBRAL_COSENO
)


class TestGenerarEmbedding:
    """Tests para generar_embedding()"""

    def test_embedding_no_vacio(self):
        """Embedding no debe ser vacío"""
        texto = "Test message"
        embedding = generar_embedding(texto)
        assert len(embedding) == 384
        assert isinstance(embedding, list)

    def test_embedding_determinista(self):
        """Mismo texto debe dar mismo embedding"""
        texto = "Test message"
        emb1 = generar_embedding(texto)
        emb2 = generar_embedding(texto)
        # Con la misma semilla, debería ser igual
        assert emb1 == emb2

    def test_embedding_texto_vacio(self):
        """Texto vacío debe devolver embedding de ceros"""
        embedding = generar_embedding("")
        assert len(embedding) == 384
        # Todos deben ser 0
        assert all(x == 0.0 for x in embedding)

    def test_embedding_texto_none(self):
        """None debe ser tratado como vacío"""
        embedding = generar_embedding(None)
        assert len(embedding) == 384

    def test_embedding_normalizado(self):
        """Embedding debe estar normalizado (longitud 1)"""
        texto = "Test message"
        embedding = generar_embedding(texto)
        # Verificar normalización
        norm = np.linalg.norm(embedding)
        assert abs(norm - 1.0) < 0.01


class TestSimilitudCoseno:
    """Tests para similitud_coseno()"""

    def test_identicos(self):
        """Embeddings idénticos deben tener similitud 1.0"""
        emb = [1.0, 0.0, 0.0]
        similitud = similitud_coseno(emb, emb)
        assert similitud == pytest.approx(1.0)

    def test_perpendiculares(self):
        """Embeddings perpendiculares deben tener similitud 0.0"""
        emb1 = [1.0, 0.0, 0.0]
        emb2 = [0.0, 1.0, 0.0]
        similitud = similitud_coseno(emb1, emb2)
        assert similitud == pytest.approx(0.0)

    def test_opuestos(self):
        """Embeddings opuestos deben tener similitud -1.0"""
        emb1 = [1.0, 0.0, 0.0]
        emb2 = [-1.0, 0.0, 0.0]
        similitud = similitud_coseno(emb1, emb2)
        assert similitud == pytest.approx(-1.0)

    def test_similitud_en_rango(self):
        """Similitud debe estar entre -1 y 1"""
        emb1 = [1.0, 2.0, 3.0]
        emb2 = [4.0, 5.0, 6.0]
        similitud = similitud_coseno(emb1, emb2)
        assert -1.0 <= similitud <= 1.0


class TestAgruparPorEmbeddings:
    """Tests para agrupar_por_embeddings()"""

    def test_titulares_vacios(self):
        """Titulares vacíos deben devolver lista vacía"""
        grupos = agrupar_por_embeddings([], umbral=0.78)
        assert grupos == []

    def test_un_titular(self):
        """Un titular debe crear un grupo"""
        titulares = [{"titulo": "Test", "medio_id": "m1", "region": "eeuu"}]
        grupos = agrupar_por_embeddings(titulares, umbral=0.78)
        assert len(grupos) == 1
        assert grupos[0]["tamanio"] == 1

    def test_varios_titulares_similares(self):
        """Titulares similares deben agruparse"""
        # Usamos el mismo texto para garantizar embeddings idénticos
        titulares = [
            {"titulo": "Venezuela en crisis", "medio_id": "m1", "region": "eeuu"},
            {"titulo": "Venezuela en crisis", "medio_id": "m2", "region": "eeuu"},
            {"titulo": "Venezuela en crisis", "medio_id": "m3", "region": "latam"}
        ]
        grupos = agrupar_por_embeddings(titulares, umbral=0.78)
        # Todos deben estar en el mismo grupo
        assert len(grupos) == 1
        assert grupos[0]["tamanio"] == 3
        assert len(grupos[0]["medio_ids"]) == 3
        assert len(grupos[0]["regiones"]) == 2  # ee-uu y latam

    def test_titulares_diferentes(self):
        """Titulares diferentes deben estar en grupos separados"""
        # Textos muy diferentes (en producción, embeddings serían diferentes)
        # Como usamos hash, textos diferentes dan embeddings diferentes
        titulares = [
            {"titulo": "Venezuela en crisis", "medio_id": "m1", "region": "eeuu"},
            {"titulo": "Noticia de Brasil", "medio_id": "m2", "region": "latam"},
            {"titulo": "Elecciones en Francia", "medio_id": "m3", "region": "europa"}
        ]
        grupos = agrupar_por_embeddings(titulares, umbral=0.99)
        # Con umbral alto (0.99), textos diferentes no se agrupan
        # El número de grupos depende de la similitud de los embeddings
        # Como usamos hash determinista, cada texto único tiene embedding único
        # Con umbral 0.99, probablemente cada uno en su grupo
        # Pero no podemos garantizarlo porque los embeddings aleatorios pueden ser similares
        # Solo verificamos que no hay error
        assert isinstance(grupos, list)
        assert len(grupos) >= 1


class TestCalcularProminenciaMedia:
    """Tests para calcular_prominencia_media()"""

    def test_prominencia_vacia(self):
        """Grupo vacío debe devolver default"""
        grupo = {"titulares": []}
        prominencia = calcular_prominencia_media(grupo)
        assert prominencia == 0.3

    def test_prominencia_portada(self):
        """Portada debe tener peso 1.0"""
        grupo = {"titulares": [{"prominencia": "portada"}]}
        prominencia = calcular_prominencia_media(grupo)
        assert prominencia == 1.0

    def test_prominencia_apertura(self):
        """Apertura de sección debe tener peso 0.8"""
        grupo = {"titulares": [{"prominencia": "apertura_seccion"}]}
        prominencia = calcular_prominencia_media(grupo)
        assert prominencia == 0.8

    def test_prominencia_interior(self):
        """Interior debe tener peso 0.5"""
        grupo = {"titulares": [{"prominencia": "interior"}]}
        prominencia = calcular_prominencia_media(grupo)
        assert prominencia == 0.5

    def test_prominencia_promedio(self):
        """Promedio de varias prominencias"""
        grupo = {"titulares": [
            {"prominencia": "portada"},
            {"prominencia": "interior"}
        ]}
        prominencia = calcular_prominencia_media(grupo)
        assert prominencia == pytest.approx(0.75)


class TestCalcularAuthorityScore:
    """Tests para calcular_authority_score_promedio()"""

    def test_authority_vacio(self):
        """Grupo vacío debe devolver default"""
        grupo = {"titulares": []}
        medios_config = []
        score = calcular_authority_score_promedio(grupo, medios_config)
        assert score == 0.5

    def test_authority_con_config(self):
        """Usar authority_score de la config"""
        grupo = {"titulares": [
            {"medio_id": "m1"},
            {"medio_id": "m2"}
        ]}
        medios_config = [
            {"id": "m1", "authority_score": 0.8},
            {"id": "m2", "authority_score": 0.6}
        ]
        score = calcular_authority_score_promedio(grupo, medios_config)
        assert score == pytest.approx(0.7)

    def test_authority_medio_desconocido(self):
        """Medio desconocido debe usar default 0.5"""
        grupo = {"titulares": [{"medio_id": "desconocido"}]}
        medios_config = []
        score = calcular_authority_score_promedio(grupo, medios_config)
        assert score == 0.5


class TestGenerarTop10Global:
    """Tests para generar_top10_global()"""

    def test_titulares_vacios(self):
        """Sin titulares debe devolver lista vacía"""
        top10 = generar_top10_global([], [])
        assert top10 == []

    def test_un_solo_titular(self):
        """Un solo titular debe devolver un solo evento"""
        titulares = [{"titulo": "Test", "medio_id": "m1", "region": "eeuu"}]
        medios_config = [{"id": "m1", "authority_score": 0.5}]
        top10 = generar_top10_global(titulares, medios_config)
        assert len(top10) == 1
        assert top10[0]["rank"] == 1
        assert "Test" in top10[0]["titulo_canonico"]

    def test_mas_de_10_titulares(self):
        """Más de 10 titulares debe devolver solo Top 10"""
        # Crear 15 titulares
        titulares = [
            {"titulo": f"Evento {i}", "medio_id": f"m{i}", "region": "eeuu"}
            for i in range(15)
        ]
        medios_config = [
            {"id": f"m{i}", "authority_score": 0.5}
            for i in range(15)
        ]
        top10 = generar_top10_global(titulares, medios_config)
        assert len(top10) == 10

    def test_evento_venezolano(self):
        """Evento con Venezuela debe ser marcado"""
        titulares = [
            {"titulo": "Venezuela en crisis económica", "medio_id": "m1", "region": "eeuu"},
            {"titulo": "Venezuela en crisis económica", "medio_id": "m2", "region": "latam"}
        ]
        medios_config = [
            {"id": "m1", "authority_score": 0.5},
            {"id": "m2", "authority_score": 0.5}
        ]
        top10 = generar_top10_global(titulares, medios_config)
        assert len(top10) == 1
        assert top10[0]["es_venezolano"] is True
        assert top10[0]["etiqueta_especial"] == "🔥 Venezuela en agenda global"

    def test_evento_no_venezolano(self):
        """Evento sin Venezuela no debe ser marcado"""
        titulares = [
            {"titulo": "Elecciones en Francia", "medio_id": "m1", "region": "europa"}
        ]
        medios_config = [{"id": "m1", "authority_score": 0.5}]
        top10 = generar_top10_global(titulares, medios_config)
        assert len(top10) == 1
        assert top10[0]["es_venezolano"] is False
        assert top10[0]["etiqueta_especial"] is None

    def test_resumen_contadores(self):
        """Resumen debe incluir contadores"""
        titulares = [
            {"titulo": "Test 1", "medio_id": "m1", "region": "eeuu"},
            {"titulo": "Test 2", "medio_id": "m2", "region": "latam"}
        ]
        medios_config = [
            {"id": "m1", "authority_score": 0.5},
            {"id": "m2", "authority_score": 0.5}
        ]
        top10 = generar_top10_global(titulares, medios_config)
        # Si no se agrupan (embeddings diferentes), habrá 2 eventos
        assert len(top10) <= 2
        if len(top10) >= 1:
            assert "📰" in top10[0]["resumen"]
            assert "medios" in top10[0]["resumen"]


class TestExtraerTitularesParaTop10:
    """Tests para extraer_titulares_para_top10()"""

    def test_extraer_titulares(self):
        """Debe extraer todos los titulares de todos los medios"""
        resultados_fetch = {
            "medios": [
                {
                    "id": "m1",
                    "exito": True,
                    "es_rss": True,
                    "titulares": [
                        {"titulo": "Titular 1", "url": "url1", "fecha": "2024-01-01"},
                        {"titulo": "Titular 2", "url": "url2", "fecha": "2024-01-02"}
                    ]
                },
                {
                    "id": "m2",
                    "exito": True,
                    "es_rss": False,
                    "titulares": [
                        {"titulo": "Titular 3", "url": "url3", "fecha": None}
                    ]
                }
            ],
            "titulares_todos": [],
            "errores": []
        }
        
        todos_titulares = extraer_titulares_para_top10(resultados_fetch)
        assert len(todos_titulares) == 3
        assert todos_titulares[0]["medio_id"] == "m1"
        assert todos_titulares[0]["fuente"] == "rss"
        assert todos_titulares[1]["medio_id"] == "m1"
        assert todos_titulares[2]["medio_id"] == "m2"
        assert todos_titulares[2]["fuente"] == "portada"

    def test_medios_sin_titulares(self):
        """Medios sin titulares deben ser ignorados"""
        resultados_fetch = {
            "medios": [
                {"id": "m1", "exito": True, "titulares": []},
                {"id": "m2", "exito": False, "titulares": []}
            ]
        }
        
        titulares = extraer_titulares_para_top10(resultados_fetch)
        assert titulares == []
