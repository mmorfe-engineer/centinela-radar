# 10 — PROYECTO RADAR: Monitoreo Automatizado de Matrices de Opinión en Prensa Global

**Repositorio:** `github.com/mmorfe-engineer/centinela-radar` (independiente, consume `centinela-core`)
**Origen:** automatización del proyecto manual "Radar de los principales medios de comunicación global" (8 analistas, ~35 medios, 2 revisiones diarias)
**Estado:** especificación aprobada — todas las recomendaciones aceptadas (2026-07-10)

---

## 1. Objetivo

Revisar automáticamente un universo **cerrado y nominal** de ~35 medios internacionales, dos veces al día, para:
1. Detectar y clasificar cobertura sobre Venezuela (matriz de opinión: enfoque + valencia).
2. **Certificar** por medio y por corrida si hubo o no cobertura (semáforo de 3 estados — sin omisiones silenciosas).
3. Producir el **Top 5 Venezuela** y el **Top 10 Global** (eventos más repetidos en toda la muestra, sean o no de Venezuela).
4. Alertar de inmediato los hallazgos de alta urgencia por Telegram.
5. Acumular histórico para la **serie temporal de la matriz** (volumen y valencia por región/día).

## 2. Diferencias de diseño respecto a los canales CENTINELA

| Aspecto | Canales CENTINELA | RADAR |
|---|---|---|
| Unidad de trabajo | El tema ("¿qué pasó sobre X?") | El **medio** ("¿qué publicó ESTE medio sobre Venezuela?") |
| Universo de fuentes | Abierto | Cerrado: los medios de `config/radar_medios.json` |
| Garantía central | Verificación de hallazgos (SIFT) | **Certificación de cobertura** por medio (semáforo) |
| Capa primaria | Perplexity | **Determinista (RSS/portada)** + Perplexity como capa 2 |

## 3. El semáforo de certificación (regla central del producto)

| Estado | Significado | Regla dura |
|---|---|---|
| 🟢 CON COBERTURA | Hallazgos sobre Venezuela encontrados, con enlace verificado | Entra a la matriz |
| 🟡 SIN COBERTURA (certificado) | El medio **fue revisado efectivamente** y no publicó sobre Venezuela en la ventana | Solo se emite si al menos una capa (RSS o Perplexity) verificó el medio con éxito |
| 🔴 NO VERIFICABLE | No se pudo revisar (error, timeout, paywall duro, bloqueo) tras los reintentos del loop de auditoría | **Jamás se convierte en 🟡.** Se declara en el tablero y se reintenta en el siguiente corte |

**Principio:** *no encontrar ≠ no haber*. Certificar 🟡 sin revisión efectiva sería una omisión falsa — el peor fallo posible de este producto. El informe abre siempre con el tablero: `35 medios: 🟢 12 · 🟡 20 · 🔴 3`.

## 4. Arquitectura de búsqueda en dos capas

### Capa 1 — Determinista (RSS/portada; costo cero; corre primero)
- Fetch del RSS o portada de cada medio (`radar_medios.json` trae la URL; el Paso 2 del prompt de construcción incluye descubrimiento y validación de feeds).
- Cruce de titulares contra `config/conectores.json` (matching normalizado: minúsculas, sin tildes, alias).
- RSS respondió + ningún match → base real para 🟡. RSS respondió + match → candidato 🟢 (se confirma con fetch del artículo). RSS falló → pasa a depender de la capa 2.
- **Subproducto clave**: TODOS los titulares descargados (matcheen o no) se conservan → insumo del Top 10 Global.

### Capa 2 — Semántica (Perplexity; ~8–10 llamadas, una por región)
- Captura lo que el matching léxico no ve: menciones indirectas, opinión sin "Venezuela" en el título.
- Prompt por región con la lista de medios de esa región + conectores, pidiendo el schema estándar de hallazgo + `medio_id`.
- Framing analítico neutro (regla validada): "cobertura de prensa sobre Venezuela", nunca lenguaje de vigilancia.

### Estados resultantes
Un medio queda 🟢/🟡 solo si **al menos una capa lo verificó efectivamente**. Ambas fallan → 🔴.

## 5. Clasificación de matriz (por hallazgo 🟢)

```json
{
  "medio_id": "wapo",
  "titulo": "...", "url": "...", "fecha": "...",
  "tipo_pieza": "portada|editorial|opinion|nota|analisis",
  "enfoque_matriz": "gobierno|oposicion|pais_general",
  "valencia": "favorable|critica|neutral|mixta",
  "valencia_respecto_a": "gobierno|oposicion",
  "conectores_activados": ["sanciones", "PDVSA"],
  "prominencia": "portada|apertura_seccion|interior",
  "resumen_1_frase": "...",
  "es_editorial_u_opinion": true
}
```
- Clasifica **DeepSeek-R1** (temp 0) con las definiciones del config. El sistema *detecta* la valencia; terminología siempre neutral en prompts y salida (regla editorial: se analizan gobierno, oposición e internacionales por igual).
- ✍️ EDITORIAL/OPINIÓN: etiqueta propia y **peso doble** en el ranking Top 5 (un editorial pesa más como matriz que diez notas informativas).

## 6. Top 5 Venezuela y Top 10 Global

**Top 5 Venezuela** — hallazgos 🟢 rankeados por: `prominencia` (portada/editorial > nota) × `autoridad del medio` × `repetición cross-medio` × (×2 si editorial/opinión).

**Top 10 Global** — desde los titulares de la capa 1 (todos los medios, todos los temas):
1. Agrupación por evento con **embeddings multilingües** (catálogo NIM) + umbral coseno — la muestra mezcla inglés, español, francés, árabe y ruso; se agrupa por significado, no por palabras.
2. Ranking: `repetición cross-medio` (criterio principal: en cuántos de los 35 apareció) × `diversidad regional` × `prominencia` × `autoridad promedio`.
3. Tarjeta por evento: titular canónico + síntesis de 1 línea (R1) + contador "📰 14/35 medios · 6/8 regiones" + enlaces a cada versión.
4. **Cruce Top5×Top10**: si un tema venezolano entra al Top 10 Global, se marca "🔥 Venezuela en agenda global" — señal de intensidad de matriz.

## 7. Funciones adicionales aprobadas

| # | Función | Cómo | Versión |
|---|---|---|---|
| a | **Serie temporal de la matriz** | Agregación de la rama `datos`: volumen de cobertura y valencia por región/día; mini-gráfico en el informe (SVG generado por código, sin JS) | V1 |
| d | **Alerta editorial/opinión** | Etiqueta ✍️ + prioridad en ranking (ya integrada en §5–6) | V1 |
| e | **Archivo selectivo** | Wayback para todos los 🟢 (función de core) | V1 |
| b | **Detector de matriz coordinada** | Si N≥4 medios publican mismo evento + mismo ángulo en ventana ≤6h → marca "patrón simultáneo a observar" (estilo SA2: señala simultaneidad, nunca afirma coordinación) | V1.1 |
| c | **Comparador de framing por región** | Para el evento venezolano más cubierto: tabla de titulares literales lado a lado por región (citas directas, cero juicio del modelo) | V1.1 |
| — | **Alerta temprana** | Hallazgo con urgencia ≥A3 → Telegram inmediato al chat designado, sin esperar el informe (sustituye la "notificación al compañero" del proyecto manual) | V1 |

V1.1 se activa cuando existan ≥2 semanas de rama `datos`.

## 8. Producto y entrega

- **Informe HTML** con la plantilla estándar de core (banda `#0F4C5C`, prefijo 📡 RADAR) — el formato "portal de noticias" queda **diferido** por decisión de Morfe; la estructura de secciones ya lo anticipa para migrar después sin tocar el pipeline.
- Orden de secciones: tablero de certificación → Top 5 Venezuela → Top 10 Global → matriz por región (tarjeta por medio con semáforo y hallazgos) → serie temporal → alertas → panel de calidad.
- **Matriz descargable**: CSV por corrida (`matriz_YYYYMMDD-corte.csv`) con las columnas del §5 — sustituye el Word/Arial 14 del proyecto manual y permite acumulación histórica.
- Canales: Telegram (teaser determinista + alertas A3+), Gmail, Pages en `/radar/`.

## 9. Operación

| Parámetro | Valor |
|---|---|
| Crons | `0 11 * * *` (7:00 VET, matutino) y `0 21 * * *` (17:00 VET, vespertino) |
| Ventana | desde el corte anterior (12h y 10h respectivamente; solapamiento de 1h con dedup cross-corte vía memoria de core) |
| Costo por corrida | ~35 fetches RSS (gratis) + 8–10 Perplexity + clasificación/ranking en NIM y Mistral (sin costo bajo plan) |
| Loop de auditoría | 3 compuertas de core + compuerta propia: **ningún medio puede terminar sin estado asignado** |
| Criterio de terminado | 5 corridas limpias (checklist doc 03) **+** 0 medios sin estado **+** tablero coherente (🟢+🟡+🔴 = total de medios) |

## 10. Archivos especiales de este repositorio

| Archivo | Contenido |
|---|---|
| `config/reporte.json` | Config estándar de canal (schema doc 05) extendida con los bloques RADAR |
| `config/radar_medios.json` | El universo cerrado: ~35 medios con id, región, URLs, RSS, tipo, autoridad, sesgo, idioma, paywall |
| `config/conectores.json` | Conectores temáticos: actores, estructurales, coyuntura (editable), indirectos |
| `PROMPT_VIBE_CODE_RADAR.md` | Prompt de construcción específico de este repo |

## 11. Notas sobre el universo de medios (heredado del proyecto manual)

- El memo original lista "Foreign Affairs" con la URL `revistafal.com` — ese dominio corresponde a *Foreign Affairs Latinoamérica*; la revista del CFR es `foreignaffairs.com`. **Se incluyen ambas** como entradas separadas.
- Medios con paywall duro (WSJ, FT, The Economist, WaPo, Reforma): la capa 1 trabaja sobre RSS/titulares (públicos); la capa 2 los cubre vía Perplexity. Nunca se evade el paywall (compliance del config maestro: citas ≤25 palabras, guardar solo extracto+URL).
- Los "responsables" humanos del memo desaparecen como asignación operativa (el sistema cubre todo), pero el campo `responsable_original` se conserva en `radar_medios.json` como referencia institucional.
