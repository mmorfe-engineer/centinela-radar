"""
Tests para radar/semaforo.py
"""

import pytest

from radar.semaforo import (
    ESTADO_VERDE,
    ESTADO_AMARILLO,
    ESTADO_ROJO,
    esta_en_cobertura,
    asignar_estado_medio,
    asignar_estados,
    generar_tablero,
    validar_tablero,
)


class TestEstaEnCobertura:
    """Tests para esta_en_cobertura()"""

    def test_cobertura_con_hallazgos(self):
        medio_resultado = {"exito": True, "titulares": []}
        hallazgos = [{"titulo": "Test"}]
        
        assert esta_en_cobertura(medio_resultado, hallazgos) is True

    def test_no_cobertura_sin_hallazgos(self):
        medio_resultado = {"exito": True, "titulares": []}
        hallazgos = []
        
        assert esta_en_cobertura(medio_resultado, hallazgos) is False

    def test_no_cobertura_fetch_fallido(self):
        medio_resultado = {"exito": False, "titulares": []}
        hallazgos = [{"titulo": "Test"}]
        
        assert esta_en_cobertura(medio_resultado, hallazgos) is False


class TestAsignarEstadoMedio:
    """Tests para asignar_estado_medio()"""

    def test_estado_verde(self):
        medio_config = {"id": "test1"}
        medio_resultado = {"exito": True, "error": None}
        hallazgos = [{"titulo": "Test"}]
        
        estado, explicacion = asignar_estado_medio(medio_config, medio_resultado, hallazgos)
        
        assert estado == ESTADO_VERDE
        assert "hallazgos" in explicacion.lower()

    def test_estado_amarillo(self):
        medio_config = {"id": "test2"}
        medio_resultado = {"exito": True, "error": None}
        hallazgos = []  # Sin hallazgos
        
        estado, explicacion = asignar_estado_medio(medio_config, medio_resultado, hallazgos)
        
        assert estado == ESTADO_AMARILLO
        assert "sin hallazgos" in explicacion.lower()

    def test_estado_rojo_timeout(self):
        medio_config = {"id": "test3"}
        medio_resultado = {"exito": False, "error": "Timeout después de 2 reintentos"}
        hallazgos = []
        
        estado, explicacion = asignar_estado_medio(medio_config, medio_resultado, hallazgos)
        
        assert estado == ESTADO_ROJO
        assert "Timeout" in explicacion

    def test_estado_rojo_bloqueado(self):
        medio_config = {"id": "test4"}
        medio_resultado = {"exito": False, "error": "Bloqueado: HTTP 403"}
        hallazgos = []
        
        estado, explicacion = asignar_estado_medio(medio_config, medio_resultado, hallazgos)
        
        assert estado == ESTADO_ROJO
        assert "Bloqueado" in explicacion


class TestAsignarEstados:
    """Tests para asignar_estados()"""

    def test_asignar_estados_varios_medios(self):
        medios_config = [
            {"id": "m1", "nombre": "Medio 1"},
            {"id": "m2", "nombre": "Medio 2"},
            {"id": "m3", "nombre": "Medio 3"}
        ]
        
        resultados_fetch = {
            "medios": [
                {"id": "m1", "exito": True, "error": None},
                {"id": "m2", "exito": False, "error": "Timeout"},
                {"id": "m3", "exito": True, "error": None}
            ],
            "titulares_todos": [],
            "errores": []
        }
        
        hallazgos_por_medio = {
            "m1": [{"titulo": "Test"}],  # Tiene hallazgos -> VERDE
            "m2": [],  # Fetch fallido -> ROJO
            "m3": []   # Sin hallazgos -> AMARILLO
        }
        
        estados, tablero = asignar_estados(
            medios_config, resultados_fetch, hallazgos_por_medio
        )
        
        assert estados["m1"] == ESTADO_VERDE
        assert estados["m2"] == ESTADO_ROJO
        assert estados["m3"] == ESTADO_AMARILLO
        
        assert tablero["total"] == 3
        assert tablero[ESTADO_VERDE] == 1
        assert tablero[ESTADO_AMARILLO] == 1
        assert tablero[ESTADO_ROJO] == 1

    def test_asignar_estados_todos_verdes(self):
        medios_config = [
            {"id": "m1", "nombre": "Medio 1"},
            {"id": "m2", "nombre": "Medio 2"}
        ]
        
        resultados_fetch = {
            "medios": [
                {"id": "m1", "exito": True, "error": None},
                {"id": "m2", "exito": True, "error": None}
            ],
            "titulares_todos": [],
            "errores": []
        }
        
        hallazgos_por_medio = {
            "m1": [{"titulo": "Test"}],
            "m2": [{"titulo": "Test"}]
        }
        
        estados, tablero = asignar_estados(
            medios_config, resultados_fetch, hallazgos_por_medio
        )
        
        assert estados["m1"] == ESTADO_VERDE
        assert estados["m2"] == ESTADO_VERDE
        assert tablero[ESTADO_VERDE] == 2

    def test_asignar_estados_medio_sin_fetch_asignado_como_rojo(self):
        # Medio sin resultado de fetch debe ser asignado como ROJO
        medios_config = [
            {"id": "m1", "nombre": "Medio 1"},
            {"id": "m2", "nombre": "Medio 2"}
        ]
        
        resultados_fetch = {
            "medios": [
                {"id": "m1", "exito": True, "error": None}
                # Falta m2
            ],
            "titulares_todos": [],
            "errores": []
        }
        
        hallazgos_por_medio = {}
        
        estados, tablero = asignar_estados(medios_config, resultados_fetch, hallazgos_por_medio)
        
        # m2 no tuvo fetch, debe ser ROJO
        assert estados["m2"] == ESTADO_ROJO
        # Tablero debe ser coherente
        assert tablero["total"] == 2
        assert tablero[ESTADO_ROJO] == 1

    def test_asignar_estados_tablero_incoherente(self):
        # Esto no debería pasar si los datos son consistentes,
        # pero testeamos la verificación
        medios_config = [
            {"id": "m1", "nombre": "Medio 1"}
        ]
        
        resultados_fetch = {
            "medios": [
                {"id": "m1", "exito": True, "error": None}
            ],
            "titulares_todos": [],
            "errores": []
        }
        
        hallazgos_por_medio = {"m1": [{"titulo": "Test"}]}
        
        estados, tablero = asignar_estados(
            medios_config, resultados_fetch, hallazgos_por_medio
        )
        
        # Verificar coherencia
        assert tablero["total"] == tablero[ESTADO_VERDE] + tablero[ESTADO_AMARILLO] + tablero[ESTADO_ROJO]


class TestGenerarTablero:
    """Tests para generar_tablero()"""

    def test_generar_tablero_basico(self):
        estados = {
            "m1": ESTADO_VERDE,
            "m2": ESTADO_AMARILLO,
            "m3": ESTADO_ROJO
        }
        
        medios_config = [
            {"id": "m1", "nombre": "Medio 1", "region": "eeuu"},
            {"id": "m2", "nombre": "Medio 2", "region": "eeuu"},
            {"id": "m3", "nombre": "Medio 3", "region": "reino_unido"}
        ]
        
        tablero = generar_tablero(estados, medios_config)
        
        assert tablero["total"] == 3
        assert tablero["estados"][ESTADO_VERDE] == 1
        assert tablero["estados"][ESTADO_AMARILLO] == 1
        assert tablero["estados"][ESTADO_ROJO] == 1
        
        # Verificar por región
        assert "eeuu" in tablero["por_region"]
        assert "reino_unido" in tablero["por_region"]
        
        # Verificar lista de medios
        assert len(tablero["medios"]) == 3

    def test_generar_tablero_todos_verdes(self):
        estados = {
            "m1": ESTADO_VERDE,
            "m2": ESTADO_VERDE,
            "m3": ESTADO_VERDE
        }
        
        medios_config = [
            {"id": "m1", "nombre": "M1", "region": "r1"},
            {"id": "m2", "nombre": "M2", "region": "r1"},
            {"id": "m3", "nombre": "M3", "region": "r2"}
        ]
        
        tablero = generar_tablero(estados, medios_config)
        
        assert tablero["estados"][ESTADO_VERDE] == 3
        assert tablero["estados"][ESTADO_AMARILLO] == 0
        assert tablero["estados"][ESTADO_ROJO] == 0


class TestValidarTablero:
    """Tests para validar_tablero()"""

    def test_validar_tablero_coherente(self):
        tablero = {
            "total": 3,
            "estados": {
                ESTADO_VERDE: 1,
                ESTADO_AMARILLO: 1,
                ESTADO_ROJO: 1
            }
        }
        
        assert validar_tablero(tablero, 3) is True

    def test_validar_tablero_incoherente_total(self):
        tablero = {
            "total": 4,  # Incorrecto
            "estados": {
                ESTADO_VERDE: 1,
                ESTADO_AMARILLO: 1,
                ESTADO_ROJO: 1
            }
        }
        
        with pytest.raises(RuntimeError) as exc_info:
            validar_tablero(tablero, 3)
        
        assert "incoherente" in str(exc_info.value)

    def test_validar_tablero_incoherente_suma(self):
        tablero = {
            "total": 3,
            "estados": {
                ESTADO_VERDE: 2,
                ESTADO_AMARILLO: 2,  # Suma = 4
                ESTADO_ROJO: 0
            }
        }
        
        with pytest.raises(RuntimeError) as exc_info:
            validar_tablero(tablero, 3)
        
        assert "incoherente" in str(exc_info.value)
