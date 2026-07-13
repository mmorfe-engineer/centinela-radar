# 05 — Escenario: Un Repositorio Independiente por Tipo de Reporte (optimizado)

Materializa la decisión aprobada del split modular, extendida al modelo "un repo = un reporte" con la librería compartida del doc 03.

## Topología

```
mmorfe-engineer/
├── centinela-core            # Librería compartida (pip install git+...)
│   ├── core/llm.py           # Cliente unificado + ruteo (doc 04)
│   ├── core/dedupe.py        # Normalización + hash + agrupación semántica
│   ├── core/actores.json     # Catálogo único de 18 actores (fuente de verdad)
│   ├── core/calidad.py       # Panel de calidad
│   ├── core/render/          # Plantilla HTML única (doc 08)
│   ├── core/entrega.py       # Canales (heredado y endurecido)
│   └── tests/
├── centinela-nacional        # MÓDULO A
├── centinela-internacional   # MÓDULO B
├── centinela-energia         # MÓDULO C
├── centinela-semanal         # MÓDULO D (síntesis, lee los datos de A+B+C)
└── centinela-sala            # Sala Situacional bajo demanda (doc 06)
```

Cada repo modular contiene solo: `config/reporte.json` (capas, queries, presupuesto), `main.py` (~50 líneas: importa core, ejecuta), workflow YAML, y rama `datos` con su histórico.

---

## MÓDULO A — Nacional (`centinela-nacional`) — parámetros ya aprobados

| Parámetro | Valor |
|---|---|
| Cron | `0 18 * * *` (14:00 VET, diario) |
| Ventana | 24 h, lenguaje relajado ("publicado HOY o en las últimas 24h") |
| Llamadas Perplexity | ~8 |
| Prefijo Telegram | 🇻🇪 NACIONAL |
| Pages | raíz `/` |
| Capas heredadas | 3 (oficialismo, oposición, AN, agenda nacional), 2 (señales indirectas), 10 (Telegram/OSINT nacional) |

**Lista de consultas (8 llamadas):**
1. Anuncios oficiales del Ejecutivo — "declaraciones y anuncios de Delcy Rodríguez, Vicepresidencia y Ejecutivo Nacional de Venezuela publicados hoy"
2. Instituciones — "decisiones y comunicados de Asamblea Nacional, TSJ, CNE y BCV de Venezuela hoy"
3. Oposición — "pronunciamientos de la oposición venezolana, María Corina Machado, Edmundo González, Plataforma Unitaria hoy"
4. Agenda nacional — "principales noticias nacionales de Venezuela hoy: economía, servicios, sociedad, judicial"
5. Seguridad interna — "noticias de seguridad, orden público y frontera en Venezuela hoy"
6. Economía doméstica — "tipo de cambio, inflación, medidas económicas y BCV Venezuela hoy"
7. Señales sociales — "narrativas y tendencias sobre Venezuela circulando en redes hoy" (clasificar SA0–SA4)
8. Telegram/OSINT — "alertas y señales OSINT sobre Venezuela hoy" (clasificar SA0–SA4, nunca como hecho)

---

## MÓDULO B — Internacional / Geopolítica (`centinela-internacional`)

| Parámetro | Valor |
|---|---|
| Cron | `0 19 * * *` (15:00 VET — escalonado 1h tras A para no competir por rate limits) |
| Ventana | 24 h |
| Llamadas Perplexity | ~10 (una por lente geográfico) |
| Prefijo Telegram | 🌐 INTERNACIONAL |
| Pages | `/internacional/` |
| Presupuesto | mayor gasto de búsqueda del sistema; usar `sonar-pro` en lentes EEUU y Europa |

**Lista de consultas (10 lentes, heredados de capa 4):**
1. Suramérica — "cobertura de prensa suramericana sobre Venezuela hoy (Infobae, La Nación, O Globo, El País América)"
2. EEUU — "cobertura de medios estadounidenses sobre Venezuela y política de EEUU hacia Venezuela hoy" [sonar-pro]
3. Europa — "cobertura europea sobre Venezuela y posiciones de la UE hoy (BBC, Guardian, Le Monde)" [sonar-pro]
4. China — "cobertura de medios chinos sobre Venezuela y relaciones China–Venezuela hoy (Xinhua, GT, CGTN)"
5. Rusia — "cobertura de medios rusos sobre Venezuela hoy (TASS, RT) y analistas rusos"
6. India / Sur Global — "cobertura india y del Sur Global sobre Venezuela y geopolítica hoy"
7. Medio Oriente / mundo árabe — "cobertura árabe sobre Venezuela, OPEP y energía hoy (Al Jazeera, Arab News)"
8. Israel — "cobertura israelí sobre Venezuela y Medio Oriente con impacto para Venezuela hoy"
9. Multilaterales — "publicaciones de ONU, OEA, CEPAL, FMI, Banco Mundial sobre Venezuela esta semana"
10. Think tanks / academia — "análisis de think tanks y universidades sobre Venezuela publicados esta semana"

**Regla dura del módulo:** validación post-hoc de cobertura (doc 03 §1.4). Todo lente con 0 hallazgos tras reintento aparece en el informe como "Sin cobertura detectada". Control de volumen: máx. 2 ítems/lente, 8 globales sin mención directa a Venezuela.

---

## MÓDULO C — Energía / Hidrocarburos / Mercados (`centinela-energia`)

| Parámetro | Valor |
|---|---|
| Cron | `30 18 * * *` (14:30 VET) |
| Ventana | 24 h |
| Llamadas Perplexity | ~6 |
| Prefijo Telegram | 🛢️ ENERGÍA |
| Pages | `/energia/` |

**Lista de consultas (6):**
1. PDVSA y Ministerio de Petróleo — comunicados y noticias hoy
2. Producción y exportaciones venezolanas — cifras y reportes recientes (separar dato duro de análisis; guardar unidad, fecha, fuente)
3. OPEP / IEA / EIA — publicaciones y comunicados de hoy
4. Precios y mercados — Brent, WTI, gas; movimientos del día y previsiones
5. Sanciones y licencias — OFAC, Tesoro, licencias Chevron/Repsol/ENI; novedades
6. Datos macro conexos — riesgo país, bonos venezolanos, commodities

**Regla dura del módulo:** todo dato numérico usa el `data_point_schema` del config (valor, unidad, período, fuente, fecha, valor previo, dirección del cambio).

---

## MÓDULO D — Síntesis Semanal (`centinela-semanal`)

| Parámetro | Valor |
|---|---|
| Cron | `0 13 * * 1` (9:00 VET lunes) |
| Insumo | **0 llamadas de búsqueda**: lee las ramas `datos` de A, B y C (7 días) |
| Modelos | DeepSeek-R1 (análisis de tendencias, contradicciones entre semanas) + Mistral Large (prosa) |
| Prefijo Telegram | 📊 SEMANAL |
| Pages | `/semanal/` |
| Contenido | Tendencias de la semana, actores con mayor movimiento, evolución de alertas SA, contradicciones no resueltas, temas a monitorear |

---

## Reglas comunes a todos los repos

1. **actores.json vive solo en centinela-core** — cualquier módulo lo importa; las decisiones editoriales bloqueadas (emojis GOB1/GOB4, P1 "Opositora" sin Nobel) se cumplen en un solo lugar.
2. **Panel de calidad obligatorio** al pie de cada informe.
3. **Rama `datos`** en cada repo con los JSON de cada corrida (histórico analizable, insumo del Módulo D).
4. **Presupuesto declarado** en `config/reporte.json`: `{"max_llamadas_busqueda": 8, "max_tokens_totales": 60000}`; superarlo = error explícito.
5. **Workflows escalonados** (18:00 / 18:30 / 19:00 UTC) para no colisionar en rate limits.
6. **X MONITOR intocable**: ningún repo nuevo comparte código, secretos ni ramas con X MONITOR.

## Anatomía fija de todo canal (obligatoria e idéntica)

```
centinela-{canal}/
├── .github/workflows/{canal}.yml   # cron propio + workflow_dispatch (corridas manuales)
├── config/reporte.json              # ÚNICO archivo que define la identidad del canal
├── main.py                          # ~50 líneas: importa centinela-core, ejecuta el pipeline
├── requirements.txt                 # git+https://github.com/mmorfe-engineer/centinela-core@vX.Y
├── tests/test_config.py             # valida reporte.json contra el schema de core
└── README.md                        # generado desde el propio config
```

**Regla de oro**: toda la personalidad del canal vive en `config/reporte.json` (nombre, banda de color, prefijo Telegram, cron, lista de consultas, presupuesto, secciones activas, ruta Pages). El código de los canales es idéntico entre sí. **Si un canal parece necesitar código propio, lo que falta es una función en centinela-core** — se agrega allí (nueva versión) y el canal la consume.

### Schema de `config/reporte.json`

```json
{
  "canal": "energia",
  "nombre_visible": "🛢️ ENERGÍA",
  "banda_color": "#8C5A0F",
  "cron_utc": "30 18 * * *",
  "ventana_horas": 24,
  "pages_ruta": "/energia/",
  "consultas": [
    {"id": 1, "query": "...", "modelo": "sonar", "lente": null},
    {"id": 2, "query": "...", "modelo": "sonar-pro", "lente": "EEUU"}
  ],
  "presupuesto": {"max_llamadas_busqueda": 6, "max_reintentos_totales": 6},
  "secciones_activas": ["Energética / Hidrocarburos", "Economía", "Internacional / Geopolítica"],
  "modo_redaccion": "reportero",
  "reglas_especiales": ["todo dato numérico usa data_point_schema"]
}
```

## Orden de construcción recomendado (actualizado)

1. `centinela-core` con tests (es el 70% del valor; 1–2 sesiones de Vibe Code).
2. **`centinela-energia` (Módulo C) como PILOTO** — dominio con datos más duros y verificables (cifras, comunicados OPEP/PDVSA, precios): el panel de calidad revela defectos con menos ambigüedad que el canal político. Terminado = 5 corridas consecutivas limpias (checklist doc 03).
3. `centinela-nacional` (Módulo A) — clonar el patrón, solo cambia `reporte.json`.
4. `centinela-internacional` (Módulo B) — ídem.
5. Módulo D Semanal cuando A+B+C tengan ≥2 semanas de rama `datos`.
6. Sala Situacional (doc 06) al final: reutiliza todo lo anterior.

**Protocolo de sesión con Vibe Code para cada canal**: usar el "Prompt de Construcción de Canal" del doc 09 — define qué leer, qué tomar de dónde y qué integrar, paso a paso con verificación.
