# 04 — Plan de Integración de IA por Tipo de Acción (v2 — con Loop de Auditoría)

> **v2 (2026-07-10)** — Actualizado con las confirmaciones de Morfe: (a) Perplexity obligatoria como única capa con index/verificación web viva; (b) Mistral Large sin costo bajo el plan actual → se usa el mejor modelo en todo, no el eficiente; (c) DeepSeek-V3 y otros modelos NIM sin costo → auditor transversal viable; (d) se incorpora el **loop auditor/revisor** con re-solicitud automática de procesos con error.

APIs disponibles bajo plan: **Perplexity Sonar**, **Mistral**, **NVIDIA NIM** (catálogo que incluye DeepSeek-R1/V3, Llama 3.x, Qwen y otros, vía endpoint compatible OpenAI `https://integrate.api.nvidia.com/v1`).

## Principio rector (validado en el proyecto)
> **Perplexity recolecta y verifica contra la web; los modelos generativos redactan y razonan; el auditor vigila cada etapa.** La estructura de costos actual (Mistral y NIM sin costo bajo plan) permite auditar agresivamente: el único presupuesto real a cuidar son los **reintentos de Perplexity**.

## Matriz de asignación por tipo de acción

| Acción | Modelo primario | Fallback | Justificación |
|---|---|---|---|
| **Búsqueda + verificación web en vivo** | Perplexity `sonar` | Perplexity `sonar-pro` (capas críticas: nacional e internacional) | **Innegociable**: único componente del stack con index web vivo; da la certeza de que el reporte refleja lo publicado realmente |
| **Extracción estructurada de hallazgos** | Perplexity con `response_format` json_schema | Reparación de JSON con Mistral Large | Forzar schema en origen minimiza parseo fallido (A8) |
| **Clasificación de urgencia (A0–A4) y SA0–SA4** | **DeepSeek-R1 vía NIM** | Mistral Large | Tarea de razonamiento con reglas: R1 razona en cadena antes de clasificar; resuelve D6 (clasificación doble). Temperatura 0 |
| **Agrupación de eventos (dedup semántica)** | Embeddings NIM (`nv-embedqa` o similar) + umbral coseno | `difflib` local | Segunda pasada tras la dedup por hash normalizado |
| **Redacción narrativa del informe** | **Mistral Large** (`mistral-large-latest`) | Llama 3.3-70B vía NIM | Sin costo bajo plan → siempre el mejor modelo; excelente español; temp 0.1 |
| **Resúmenes ejecutivos** | **Mistral Large** | — | v2: ya no se degrada a Ministral; el plan lo permite |
| **AUDITOR LLM (nivel 2, transversal)** | **DeepSeek-V3 vía NIM** | Mistral Large | Sin costo → puede auditar cada etapa sin dolor presupuestario. Temp 0 |
| **Verificación afirmación↔fuente** | DeepSeek-V3 (integrada al auditor de la etapa de redacción) | Mistral Large | Cotejo mecánico bullet↔URL |
| **Análisis profundo por especialidad (Editor, doc 07)** | DeepSeek-R1 (razonamiento) + Mistral Large (prosa) | — | R1 estructura; Mistral redacta |
| **Sala Situacional: planificación (doc 06)** | DeepSeek-R1 → Perplexity ejecuta | Mistral Large | El planificador razona fuentes/queries; Perplexity ejecuta y verifica |
| **Teaser Telegram** | Ninguno (función determinista desde el JSON) | — | No usar LLM donde el código basta (resuelve P2) |
| **Control de calidad determinista (nivel 1)** | Ninguno (código puro + tests) | — | Primera línea del auditor, costo cero |

---

## EL LOOP DE AUDITORÍA (evaluator-optimizer con re-solicitud acotada)

### Concepto
Cada etapa del pipeline pasa por una **compuerta de validación** antes de avanzar. Si falla, el auditor produce un **diagnóstico estructurado** que se inyecta en el reintento de esa misma etapa. El auditor nunca corrige contenido por sí mismo: solo diagnostica y re-solicita.

```
BÚSQUEDA (Perplexity) ──► Compuerta 1 ──► CLASIFICACIÓN (R1) ──► Compuerta 2 ──► REDACCIÓN (Mistral) ──► Compuerta 3 ──► ENTREGA
                            │ falla                  │ falla                        │ falla
                            ▼                        ▼                              ▼
                     re-consulta con             re-clasifica SOLO             re-redacta SOLO la
                     prompt corregido            los ítems inválidos           sección defectuosa
                     (máx 2 reintentos)          (máx 2)                       (máx 2)
```

### Dos niveles de auditor

**Nivel 1 — Determinista (código puro; corre SIEMPRE primero; costo cero):**
- JSON parsea contra el schema; URLs con formato válido y dominio real
- Códigos de actor dentro del catálogo de 18 (D4)
- Timestamps plausibles: no >50% idénticos (D5)
- Duplicados post-normalización = 0 (D1)
- Cada lente geográfico con ≥1 hallazgo o vacío justificado (D3)
- Cada bullet del informe contiene una URL presente en el material base (R7)
- Sin dict literals ni `None` en el render (D2)

**Nivel 2 — LLM (DeepSeek-V3, temp 0; solo audita lo que pasó el nivel 1):**
- ¿El resumen ejecutivo sintetiza o solo concatena?
- ¿Alguna señal SA1–SA3 quedó redactada como hecho confirmado?
- ¿La urgencia asignada es coherente con las definiciones A0–A4?
- ¿Hay afirmaciones sin respaldo en los hallazgos numerados?
- ¿Se respetan las decisiones editoriales bloqueadas (emojis, cargos)?

### Esqueleto de implementación (`centinela-core/core/auditor.py`)

```python
def ejecutar_con_auditoria(etapa, entrada, max_reintentos=2):
    diagnostico = None
    for intento in range(1, max_reintentos + 2):
        salida = etapa.ejecutar(entrada, correccion=diagnostico)

        fallas = auditar_determinista(salida, etapa.reglas)      # nivel 1, siempre
        if not fallas:
            fallas = auditar_llm(salida, etapa.criterios)        # nivel 2, DeepSeek-V3

        if not fallas:
            return salida, {"intentos": intento, "estado": "OK"}

        diagnostico = construir_correccion(fallas)
        # Ejemplo de diagnóstico inyectado al reintento:
        # "Tu respuesta anterior falló la auditoría:
        #  - 3 códigos de actor inválidos (EEUU, FMI, NA). Usa SOLO el catálogo adjunto;
        #    actores fuera de catálogo van en texto libre con codigo_actor=null.
        #  - H2, H7 y H9 comparten timestamp idéntico: marca fecha_confianza='baja'.
        #  Corrige ÚNICAMENTE estos puntos manteniendo el resto intacto."
        registrar(etapa.nombre, intento, fallas)                 # nunca silencioso

    # Reintentos agotados: el trabajo NO se descarta ni se inventa
    return salida, {"estado": "DEGRADADO", "fallas_residuales": fallas}
```

### Las tres reglas que evitan que el loop se convierta en problema

1. **Tope duro**: 2 reintentos por etapa + tope global por corrida (`max_reintentos_totales` en config). Un fallo estructural (API caída) no puede reintentar infinito. Los reintentos de **Perplexity** son el único gasto real: su tope es el más importante.
2. **Fallo residual = degradación visible, jamás descarte ni silencio.** Si tras los reintentos un lente sigue vacío, el informe sale con la marca "⚠ Lente China: sin cobertura verificable tras 3 intentos" y el panel de calidad lo registra. El auditor no puede convertirse en un nuevo mecanismo de fallo silencioso "corrigiendo" hacia contenido inventado. Coherente con la filosofía *fail loud* del doc 03.
3. **El auditor jamás edita contenido; solo diagnostica y re-solicita.** Si el auditor LLM "arreglara" el texto directamente sería un segundo redactor sin fuentes. La corrección la ejecuta siempre la etapa original con sus fuentes.

### Telemetría del loop (al panel de calidad de cada informe)
`intentos_por_etapa`, `fallas_detectadas` (por tipo), `fallas_corregidas`, `fallas_residuales`, `costo_reintentos_perplexity`. Con 2 semanas de datos en la rama `datos`, esta telemetría dice qué prompts necesitan mejora permanente (falla que se repite cada día = arreglar el prompt, no confiar en el loop).

---

## Arquitectura de clientes (centinela-core)

Un solo cliente unificado porque **NVIDIA NIM y Mistral son compatibles con el formato OpenAI**:

```python
# core/llm.py
PROVEEDORES = {
    "perplexity": {"base": "https://api.perplexity.ai", "key_env": "PERPLEXITY_API_KEY"},
    "mistral":    {"base": "https://api.mistral.ai/v1", "key_env": "MISTRAL_API_KEY"},
    "nvidia":     {"base": "https://integrate.api.nvidia.com/v1", "key_env": "NVIDIA_API_KEY"},
}

RUTEO = {  # acción → (proveedor, modelo, fallback)
    "buscar":            ("perplexity", "sonar", None),
    "buscar_critico":    ("perplexity", "sonar-pro", ("perplexity", "sonar")),
    "clasificar":        ("nvidia", "deepseek-ai/deepseek-r1", ("mistral", "mistral-large-latest")),
    "auditar":           ("nvidia", "deepseek-ai/deepseek-v3", ("mistral", "mistral-large-latest")),
    "redactar":          ("mistral", "mistral-large-latest", ("nvidia", "meta/llama-3.3-70b-instruct")),
    "resumir":           ("mistral", "mistral-large-latest", None),
    "analizar_profundo": ("nvidia", "deepseek-ai/deepseek-r1", ("mistral", "mistral-large-latest")),
}
```

**Nota sobre nombres de modelo NIM**: los identificadores exactos del catálogo NVIDIA (p. ej. `deepseek-ai/deepseek-r1`) cambian con las versiones; verificar en `https://build.nvidia.com` los strings vigentes del plan antes de fijarlos en `RUTEO`.

## Reglas de integración

1. **Secreto nuevo**: `NVIDIA_API_KEY` en Actions de cada repo modular.
2. **Fallback siempre declarado y registrado**: usarlo deja huella en `metadata.fallbacks_usados`.
3. **Presupuesto por acción y corrida** (`presupuesto_tokens` en config); superarlo aborta con error explícito. Con Mistral/NIM sin costo, el presupuesto vigila principalmente Perplexity y el tiempo total de corrida.
4. **DeepSeek-R1 y el razonamiento visible**: separar las cadenas `<think>` del contenido final; guardarlas en `metadata.razonamiento` para auditoría — nunca al informe.
5. **Framing analítico en prompts a Perplexity**: mantener el reframing validado ("monitoreo de cobertura de prensa", "análisis de agenda mediática").
6. **Temperaturas fijas**: buscar/clasificar/auditar = 0; redactar = 0.1; analizar = 0.3.
7. **Trazabilidad**: cada bloque registra `generado_por` + resultado de auditoría, visibles en el panel de calidad.

## Estimación de llamadas por corrida (Módulo A, escenario típico con loop)

| Acción | Llamadas base | Reintentos típicos | Modelo |
|---|---|---|---|
| Búsqueda por capa/lente | ~8 | 0–2 (tope 2/etapa) | sonar / sonar-pro |
| Auditoría nivel 2 por etapa | 3 | — | DeepSeek-V3 (sin costo) |
| Clasificación por lote | 1 | 0–1 | DeepSeek-R1 (sin costo) |
| Redacción | 1 | 0–1 | Mistral Large (sin costo) |
| **Total típico** | **~13–17** | | 3 proveedores |

El sobrecosto real del loop es marginal: solo los reintentos de Perplexity cuestan; todo lo demás corre sobre planes sin costo.
