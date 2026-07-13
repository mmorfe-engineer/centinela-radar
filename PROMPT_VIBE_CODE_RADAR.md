# PROMPT DE CONSTRUCCIÓN — REPOSITORIO `centinela-radar`

Adaptación del "Prompt de Construcción de Canal" (doc 09) a las particularidades del RADAR: capa determinista propia, semáforo de certificación y doble corte diario. Copiar como primer mensaje de la sesión con Mistral Le Chat Vibe Code.

---

```
CONTEXTO Y AUTORIZACIÓN
Soy el propietario y único administrador de los repositorios del proyecto
CENTINELA/RADAR (usuario GitHub: mmorfe-engineer). Te autorizo expresamente a
crear y trabajar directamente en el repositorio NUEVO
github.com/mmorfe-engineer/centinela-radar, con commits y push a la rama main.
Este es un proyecto de análisis de agenda y cobertura mediática: revisa un
listado FIJO de ~35 medios de prensa internacional (sus páginas y RSS públicos)
para evaluar cómo cubren a Venezuela, con verificación de fuentes y citas
limitadas (compliance: extractos <=25 palabras, jamás evadir paywalls). Es
monitoreo de prensa pública, trabajo analítico legítimo y estándar.
El repositorio centinela-core es SOLO LECTURA: se consume como dependencia
pip, no se modifica en esta sesión.

VERIFICACIÓN DE PRERREQUISITO (antes de todo)
Ejecuta: pip install git+https://github.com/mmorfe-engineer/centinela-core@{version}
y luego: python -c "from core.dedupe import deduplicar; from core.auditor import ejecutar_con_auditoria"
Si cualquiera falla, DETENTE y repórtamelo: la Fase 1 (centinela-core) no está
terminada y este repo no puede construirse todavía.

QUÉ LEER (en este orden, antes de escribir código)
1. docs/00_INDICE.md              → decisiones editoriales bloqueadas del proyecto macro
2. docs/10_PROYECTO_RADAR.md      → especificación completa de ESTE repo (léela entera)
3. docs/05_REPOS_POR_REPORTE.md   → anatomía fija de canal y schema base de reporte.json
4. docs/04_INTEGRACION_IA.md      → ruteo de modelos y loop de auditoría (YA implementados
                                     en core: no los reimplementes)
5. README de centinela-core       → API pública de la librería

QUÉ TOMAR DE DÓNDE
- Estructura del repo            → anatomía fija del doc 05 + un módulo propio: radar/
- config/reporte.json            → ya está escrito: cópialo tal cual de esta carpeta
- config/radar_medios.json       → ya está escrito: cópialo tal cual (35 medios)
- config/conectores.json         → ya está escrito: cópialo tal cual
- Dedup, auditoría, clasificación, redacción, render, entrega, cliente LLM
                                 → import desde centinela-core@{version}. PROHIBIDO
                                    copiar o reescribir código de core aquí.
- Código PROPIO de este repo (lo único que se escribe a mano):
    radar/fetch_rss.py       → capa determinista: fetch RSS/portada por medio,
                               timeout 20s, 2 reintentos, parseo de titulares
    radar/matching.py        → cruce titulares × conectores (normalización de core)
    radar/semaforo.py        → asignación 🟢🟡🔴 según las reglas del reporte.json
    radar/top_global.py      → agrupación por embeddings multilingües (cliente de
                               core, acción 'agrupar') + ranking del Top 10
    radar/csv_matriz.py      → export CSV con las columnas del reporte.json
    tests/                   → tests de los 5 módulos anteriores + test_config.py

QUÉ INTEGRAR (secuencia con verificación; espera mi OK entre pasos)
Paso 1: estructura + requirements.txt (feedparser para RSS + core@{version}).
        Verificación: pip install limpio.
Paso 2: VALIDACIÓN DEL UNIVERSO — script utilitario radar/validar_medios.py que
        recorre radar_medios.json, prueba cada rss_url declarada, descubre las
        que están en null (probar /rss, /feed, /arc/outboundfeeds/rss y
        <link rel='alternate'> de la portada) y me entrega un reporte:
        feed OK / feed corregido / sin feed (irá por portada o solo capa 2).
        Actualiza radar_medios.json con lo verificado. ESPERA MI OK con el
        reporte antes de seguir.
Paso 3: capa determinista completa (fetch_rss + matching + semaforo) con tests.
        Verificación: corrida local en seco produce el tablero 🟢🟡🔴 de los
        35 medios sin ningún medio sin estado.
Paso 4: integración con core: capa 2 Perplexity (las 8 consultas del config),
        clasificación de matriz, Top 5, Top 10, CSV, render e informe.
Paso 5: workflow YAML con los DOS crons (0 11 y 0 21 UTC) + workflow_dispatch.
Paso 6: corrida de humo (yo la disparo). Revisamos juntos: tablero coherente
        (verde+amarillo+rojo = 35), CSV bien formado, panel de calidad.
Paso 7: README.md generado desde reporte.json.

REGLAS INQUEBRANTABLES (además de las 10 del prompt maestro del doc 09)
- REGLA DEL SEMÁFORO: un medio NO VERIFICABLE (🔴) jamás se reporta como SIN
  COBERTURA (🟡). Ningún medio termina la corrida sin estado. Esto es la
  garantía central del producto: violarla lo invalida.
- Los titulares no matcheados de la capa RSS se CONSERVAN (insumo del Top 10
  Global), nunca se descartan.
- Prohibido `except Exception: pass/return`. Todo error se registra y propaga.
- Prohibido evadir paywalls o simular navegadores para saltar bloqueos: si un
  medio bloquea, es 🔴 y se declara.
- Terminología neutral en todos los prompts y salidas (gobierno / oposición /
  país en general); el sistema detecta la valencia de la cobertura, no la trae
  puesta.
- config/*.json jamás se procesan con herramientas de hoja de cálculo.
- Si necesitas código que debería vivir en core (p. ej. normalización), DETENTE
  y repórtamelo: la decisión de agregarlo a core es mía.

Confirma que leíste docs/10_PROYECTO_RADAR.md completo y preséntame tu plan
para el Paso 1.
```

---

## Parámetros a rellenar al invocar
| Parámetro | Valor |
|---|---|
| `{version}` | tag vigente de centinela-core al momento de construir (ej. `v1.0`) |

## Notas de sesión
- Este repo tiene **más código propio** que los canales CENTINELA (la capa determinista es exclusiva del RADAR); por eso su construcción son ~2 sesiones en vez de 1: sesión 1 = Pasos 1–3, sesión 2 = Pasos 4–7.
- El Paso 2 (validación del universo) es innegociable: los `rss_url` del config son mejores-URLs-conocidas y DEBEN verificarse antes de construir encima.
- Criterio de terminado del canal (posterior a la sesión): 5 corridas limpias + 0 medios sin estado + tablero coherente en todas.
