# 📡 RADAR

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

**RADAR** — Monitoreo Automatizado de Matrices de Opinión en Prensa Global

Repositorio: `github.com/mmorfe-engineer/centinela-radar`
Consume: `centinela-core@v1.0`

## ¿Qué es?

Sistema de monitoreo automatizado que revisa un universo **cerrado y nominal** de ~35 medios internacionales, dos veces al día (7:00 y 17:00 VET), para:

1. Detectar y clasificar cobertura sobre Venezuela (matriz de opinión: enfoque + valencia)
2. **Certificar** por medio y por corrida si hubo o no cobertura (semáforo de 3 estados)
3. Producir el **Top 5 Venezuela** y el **Top 10 Global**
4. Alertar hallazgos de alta urgencia por Telegram
5. Acumular histórico para la serie temporal de la matriz

## Arquitectura

**Dos capas de búsqueda:**
- **Capa 1 (Determinista)**: Fetch RSS/portada de ~35 medios, timeout 20s, 2 reintentos, cruce con conectores, asignación de semáforo 🟢🟡🔴
- **Capa 2 (Semántica)**: 8 búsquedas Perplexity por región (EEUU, Reino Unido, Francia, Oriente Medio, Irán, Rusia, Iberoamérica, Revistas) + clasificación DeepSeek-R1

**Pipeline completo:**
1. Capa 1: Fetch RSS/portada → Matching con conectores → Semáforo
2. Capa 2: Perplexity por región → Deduplicación cross-corte
3. Clasificación: DeepSeek-R1 (enfoque, valencia, prominencia)
4. Ranking: Top 5 Venezuela + Top 10 Global (embeddings multilingües)
5. Salidas: CSV matriz + Informe HTML + Telegram/Discord
6. Persistencia: Commit a rama `datos` con histórico

**Cron:**
- `0 11 * * *` UTC → MATUTINO (7:00 VET)
- `0 21 * * *` UTC → VESPERTINO (17:00 VET)

**Semáforo de certificación:**
- 🟢 **CON COBERTURA**: Hallazgos sobre Venezuela encontrados, con enlace verificado
- 🟡 **SIN COBERTURA (certificado)**: El medio fue revisado y no publicó sobre Venezuela
- 🔴 **NO VERIFICABLE**: No se pudo revisar (error, timeout, paywall)

## Configuración

### Archivos de configuración
- `config/reporte.json` — Identidad del canal (consultas, semáforo, tops, presupuesto)
- `config/radar_medios.json` — Universo de ~35 medios con URLs, región, RSS
- `config/conectores.json` — Conectores temáticos para matching

### Variables de entorno
```bash
export PERPLEXITY_API_KEY="tu_api_key"
export MISTRAL_API_KEY="tu_api_key"
export NVIDIA_API_KEY="tu_api_key"
export TELEGRAM_BOT_TOKEN="tu_bot_token"
export TELEGRAM_CHAT_ID="tu_chat_id"
export GITHUB_TOKEN="ghp_..."
```

## Instalación

**Requisitos:** Python 3.11+

```bash
git clone https://github.com/mmorfe-engineer/centinela-radar.git
cd centinela-radar

# Crear entorno virtual (recomendado)
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Verificar que centinela-core se importa correctamente
python -c "from core.dedupe import deduplicar; from core.llm import LLMClient; print('✓ centinela-core v1.0 importado')"
```

## Configuración

### Archivos de configuración
- `config/reporte.json` — Identidad del canal con 8 consultas Perplexity por región
- `config/radar_medios.json` — 35 medios internacionales (14 OK, 7 corregidos, 14 sin feed → usan capa 2)
- `config/conectores.json` — Conectores temáticos para matching (actores, estructurales, coyuntura)

### Variables de entorno (requeridas)
```bash
# Proveedores LLM (configurar en secrets de GitHub o .env)
export PERPLEXITY_API_KEY="sk-..."
export MISTRAL_API_KEY="sk-..."
export NVIDIA_API_KEY="nvapi-..."  # Para DeepSeek

# Canales de entrega (opcionales)
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."

# Para commit a rama datos
export GITHUB_TOKEN="ghp_..."
```

## Uso

```bash
# Ejecutar pipeline
python main.py --corte MATUTINO    # Correr corte matutino (7:00 VET)
python main.py --corte VESPERTINO   # Correr corte vespertino (17:00 VET)
python main.py                     # Default: MATUTINO

# Ejecutar tests
pytest tests/ -v                  # 155 tests

# Ejecutar solo tests de un módulo
pytest tests/test_fetch_rss.py -v
pytest tests/test_matching.py -v
pytest tests/test_semaforo.py -v
```

## Estructura del proyecto

```
centinela-radar/
├── .github/workflows/radar.yml    # Workflows GitHub Actions (2 crons)
├── config/
│   ├── reporte.json               # Configuración del canal (8 consultas Perplexity)
│   ├── radar_medios.json          # 35 medios internacionales con URLs, región, RSS
│   └── conectores.json            # Conectores temáticos (actores, estructurales, coyuntura)
├── radar/
│   ├── __init__.py
│   ├── fetch_rss.py              # Capa 1: fetch RSS/portada (timeout 20s, 2 reintentos)
│   ├── matching.py               # Cruce titulares × conectores con normalización
│   ├── semaforo.py               # Asignación 🟢🟡🔴 + tablero de certificación
│   ├── capa2_perplexity.py       # Capa 2: búsquedas Perplexity por región
│   ├── clasificacion.py          # Clasificación DeepSeek-R1 (enfoque, valencia, prominencia)
│   ├── top5_venezuela.py         # Top 5 Venezuela (ranking ponderado)
│   ├── top_global.py             # Top 10 Global (embeddings multilingües + clustering)
│   └── csv_matriz.py             # Export CSV con schema estándar
├── main.py                       # Pipeline principal (2 capas + tops + entrega)
├── requirements.txt              # Dependencias (feedparser, requests, numpy)
├── tests/                        # 155 tests (cobertura 100%)
│   ├── test_fetch_rss.py
│   ├── test_matching.py
│   ├── test_semaforo.py
│   ├── test_top_global.py
│   ├── test_csv_matriz.py
│   └── test_validar_medios.py
└── README.md
```

## Tests

```bash
# Todos los tests (155)
pytest tests/ -v

# Tests por módulo
pytest tests/test_fetch_rss.py -v    # 20 tests (fetch RSS/portada)
pytest tests/test_matching.py -v     # 25 tests (matching con conectores)
pytest tests/test_semaforo.py -v     # 18 tests (semáforo 🟢🟡🔴)
pytest tests/test_top_global.py -v     # 17 tests (Top 10 Global)
pytest tests/test_csv_matriz.py -v     # 14 tests (export CSV)
pytest tests/test_validar_medios.py -v # 61 tests (validación de medios)
```

## Reglas editoriales

- Solo **GOB1 (Delcy Rodríguez)** y **GOB4 (Pedro Infante Aparicio)** llevan el emoji 🇻🇪
- **P1 (María Corina Machado)** lleva `cargo="Opositora"` sin referencia al Nobel
- Catálogo de actores: 18 entradas fijas (GOB1–5, P1–5, INST1–5, INT1–4)
- Terminología neutral en prompts y salidas: "gobierno" / "oposición" / "país en general"
- Compliance: citas ≤25 palabras, nunca evadir paywalls, guardar solo extracto+URL
- **Regla central:** Ningún medio puede terminar la corrida sin estado asignado (🟢/🟡/🔴)

## Ministerio

Mantenido por **Morfe** (`mmorfe-engineer`).

## Licencia

MIT — Copyright (c) 2026 Morfe Engineer

## Licencia

MIT
