# CENTINELA PRO — Documentación Maestra del Proyecto
**Fecha de corte:** 2026-07-10 | **Propietario:** mmorfe-engineer (CIMAP) | **Estado:** Pausado para reformulación

## Índice de documentos

| # | Archivo | Contenido |
|---|---------|-----------|
| 01 | `01_INFORME_PROYECTO.md` | Informe completo: acuerdos, arquitectura, especificaciones técnicas, términos de referencia, rutas del repositorio |
| 02 | `02_DEBILIDADES_RIESGOS.md` | Análisis de debilidades y riesgos del proyecto tal como está formulado |
| 03 | `03_PLAN_MEJORA.md` | Plan de recomendaciones: viabilidad, optimización y escalamiento |
| 04 | `04_INTEGRACION_IA.md` | **v2** — Integración de IA por acción + **loop de auditoría** con re-solicitud automática (Perplexity obligatoria para verificación web; Mistral Large y DeepSeek-V3/R1 sin costo bajo plan) |
| 05 | `05_REPOS_POR_REPORTE.md` | **v2** — Repos independientes + anatomía fija de canal + schema de `reporte.json` + orden actualizado (Energía como piloto) |
| 06 | `06_SALA_SITUACIONAL.md` | Escenario: consulta de Sala Situacional por Tema Especial (agente selector de fuentes) |
| 07 | `07_EDITOR_ANALITICO.md` | Diseño del "Editor" de contenido con análisis profundo por especialidad temática |
| 08 | `08_ESQUEMA_VISUAL_REPORTES.md` | Esquema visual optimizado, versátil y único para todos los reportes |
| 09 | `09_PROMPT_VIBE_CODE.md` | **v2** — Prompt maestro + **Prompt de Construcción de Canal** (protocolo repetible: qué leer, qué tomar de dónde, qué integrar, con verificación por paso) |

## Cómo usar esta carpeta con Mistral Le Chat Vibe Code
1. Sube esta carpeta completa al repositorio en `docs/` (ej. `github.com/mmorfe-engineer/cimap-centinela-pro/docs/`).
2. Al iniciar sesión en Vibe Code, indica: *"Lee primero `docs/00_INDICE.md` y luego el documento correspondiente a la tarea."*
3. Usa el prompt maestro de `09_PROMPT_VIBE_CODE.md` como primer mensaje de cada sesión.

## Decisiones editoriales bloqueadas (NO modificar sin autorización de Morfe)
- Solo **GOB1 (Delcy Rodríguez)** y **GOB4 (Pedro Infante Aparicio)** llevan el emoji 🇻🇪.
- **P1 (María Corina Machado)** lleva `cargo="Opositora"` sin referencia al Nobel.
- **X MONITOR** es un sistema de producción separado: **no se modifica nunca** desde este proyecto.
- Catálogo de actores: 18 entradas fijas (GOB1–5, P1–5, INST1–5, INT1–4). Ningún código fuera del catálogo es válido.
