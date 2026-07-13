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
- **Capa 1 (Determinista)**: Fetch RSS/portada de cada medio, cruce con conectores, asignación de semáforo
- **Capa 2 (Semántica)**: Búsquedas Perplexity por región + clasificación DeepSeek

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

```bash
git clone https://github.com/mmorfe-engineer/centinela-radar.git
cd centinela-radar

# Instalar dependencias
pip install -r requirements.txt

# Verificar
python -c "from core.dedupe import deduplicar; print('✓ centinela-core importado')"
```

## Uso

```bash
# Ejecutar pipeline
python main.py

# Ejecutar tests
pytest tests/ -v
```

## Estructura del proyecto

```
centinela-radar/
├── .github/workflows/radar.yml    # Workflows GitHub Actions
├── config/
│   ├── reporte.json               # Configuración del canal
│   ├── radar_medios.json          # Lista de medios
│   └── conectores.json            # Conectores temáticos
├── radar/
│   ├── __init__.py
│   ├── fetch_rss.py              # Capa determinista: fetch RSS/portada
│   ├── matching.py               # Cruce titulares × conectores
│   ├── semaforo.py               # Asignación 🟢🟡🔴
│   ├── top_global.py             # Top 5 Venezuela + Top 10 Global
│   └── csv_matriz.py             # Export CSV
├── main.py                       # Pipeline principal
├── requirements.txt
├── tests/
│   └── test_config.py            # Tests de configuración
└── README.md
```

## Crons

- `0 11 * * *` — Matutino (7:00 VET)
- `0 21 * * *` — Vespertino (17:00 VET)

## Reglas editoriales

- Solo **GOB1 (Delcy Rodríguez)** y **GOB4 (Pedro Infante Aparicio)** llevan el emoji 🇻🇪
- **P1 (María Corina Machado)** lleva `cargo="Opositora"` sin referencia al Nobel
- Catálogo de actores: 18 entradas fijas (GOB1–5, P1–5, INST1–5, INT1–4)
- Terminología neutral en prompts y salidas
- Compliance: citas ≤25 palabras, nunca evadir paywalls

## Ministerio

Mantenido por Morfe (`mmorfe-engineer`, `morfemartin`).

## Licencia

MIT
