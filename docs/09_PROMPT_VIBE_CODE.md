# 09 — Prompt de Operador para Mistral Le Chat Vibe Code

## Nota previa importante
No existe (ni conviene) un prompt que "fuerce" a Vibe Code por encima de sus restricciones de seguridad — y no está redactado con ese fin. Lo que sí está comprobado es que **la inmensa mayoría de los rechazos de agentes de código nacen de ambigüedad, no de restricciones reales**: falta de autorización explícita, falta de contexto, alcance difuso, o framing que suena a vigilancia. Este prompt elimina esas causas: autorización del dueño, contexto completo, alcance quirúrgico, framing analítico correcto (el mismo aprendizaje ya validado con Perplexity). Con esto, Vibe Code trabaja directo en el repositorio sin fricción.

---

## PROMPT MAESTRO (copiar como primer mensaje de cada sesión)

```
CONTEXTO Y AUTORIZACIÓN
Soy el propietario y único administrador del repositorio privado
github.com/mmorfe-engineer/cimap-centinela-pro (usuario: mmorfe-engineer).
Te autorizo expresamente a leer, modificar, crear y eliminar archivos de ESTE
repositorio, hacer commits y push directamente a la rama {rama}, dentro del
alcance definido abajo. Este es mi proyecto personal/profesional de análisis
de cobertura mediática y agenda pública sobre Venezuela: un pipeline en Python
que busca noticias con APIs públicas (Perplexity), redacta informes analíticos
(Mistral) y los publica. Es trabajo analítico legítimo de monitoreo de prensa
con verificación de fuentes (metodología SIFT), no vigilancia de personas.

DOCUMENTACIÓN OBLIGATORIA
Antes de escribir código, lee en este orden:
1. docs/00_INDICE.md   (mapa del proyecto y decisiones bloqueadas)
2. docs/01_INFORME_PROYECTO.md   (arquitectura y especificaciones)
3. El documento docs/0X correspondiente a la tarea de hoy.

TAREA DE HOY
{descripción concreta de la tarea, ej: "Implementar la deduplicación con
normalización según docs/03_PLAN_MEJORA.md sección 1.1, con sus tests"}

REGLAS DE TRABAJO (inquebrantables)
1. Trabaja DIRECTO en el repositorio: edita los archivos reales, no me des
   fragmentos para copiar. Entregable = commit(s) en la rama {rama}.
2. Archivos completos, nunca parches parciales sin contexto.
3. NO toques nada relacionado con "X MONITOR": es un sistema de producción
   separado y está fuera de alcance.
4. Decisiones editoriales bloqueadas (docs/00_INDICE.md): emoji 🇻🇪 solo en
   GOB1 y GOB4; P1 = "Opositora" sin referencia al Nobel; catálogo de 18
   actores cerrado. No las modifiques ni las "mejores".
5. Prohibido el patrón `except Exception: return {}` o cualquier silenciamiento
   de errores. Todo error se registra y se propaga.
6. Los archivos config/*.json jamás se reformatean como CSV/TSV ni se procesan
   con herramientas de hoja de cálculo.
7. Confirmación paso a paso: antes de cada cambio estructural, preséntame el
   plan en 3-5 líneas y espera mi "OK". Después del OK, ejecuta completo.
8. Cada commit: mensaje en español, formato "tipo: descripción" (fix:, feat:,
   test:, docs:, refactor:).
9. Si una instrucción mía contradice docs/, señálalo antes de ejecutar.
10. Al terminar: resumen de archivos tocados + cómo verificar el resultado
    (comando de test o corrida manual).

Si algo del alcance te resulta ambiguo, pregunta ANTES de asumir. Confirma que
leíste la documentación y preséntame tu plan para la tarea de hoy.
```

---

---

## PROMPT DE CONSTRUCCIÓN DE CANAL (protocolo repetible)

Usar este prompt cada vez que se construye un canal nuevo. Solo cambian los valores entre `{ }`. Presupone que `centinela-core` ya existe y está etiquetado (`vX.Y`).

```
CONTEXTO Y AUTORIZACIÓN
Soy el propietario y único administrador de los repositorios de la organización
del proyecto CENTINELA (usuario: mmorfe-engineer). Te autorizo a crear y trabajar
directamente en el repositorio NUEVO github.com/mmorfe-engineer/centinela-{canal},
con commits y push a la rama main. Proyecto de análisis de cobertura mediática
con verificación de fuentes (SIFT). El repo centinela-core es SOLO LECTURA en
esta sesión: se consume como dependencia, no se modifica.

QUÉ LEER (en este orden, antes de escribir código)
1. docs/00_INDICE.md            → decisiones editoriales bloqueadas
2. docs/05_REPOS_POR_REPORTE.md → anatomía fija de canal + schema de reporte.json
                                   + la FICHA del módulo "{canal}" (cron, consultas,
                                   presupuesto, prefijo, reglas especiales)
3. docs/04_INTEGRACION_IA.md    → ruteo de modelos y loop de auditoría (ya
                                   implementados en core: NO los reimplementes)
4. El README de centinela-core  → API pública de la librería

QUÉ TOMAR DE DÓNDE
- Estructura del repo        → anatomía fija del doc 05 (exacta, sin variaciones)
- Contenido de reporte.json  → ficha del módulo "{canal}" en doc 05
- Toda la lógica (búsqueda, dedup, auditoría, clasificación, redacción, render,
  entrega)                   → import desde centinela-core@{version}. PROHIBIDO
                               copiar o reescribir código de core en este repo.
- Catálogo de actores        → viene dentro de core; jamás crear actores.json local
- Secretos del workflow      → PERPLEXITY_API_KEY, MISTRAL_API_KEY, NVIDIA_API_KEY
                               + canales de entrega (los configuraré yo en Settings;
                               tú solo referencia los nombres en el YAML)

QUÉ INTEGRAR (secuencia con verificación; espera mi OK entre pasos)
Paso 1: estructura del repo + requirements.txt apuntando a core@{version}.
        Verificación: pip install funciona en un venv limpio.
Paso 2: config/reporte.json completo según la ficha del doc 05.
        Verificación: tests/test_config.py en verde (schema de core).
Paso 3: main.py mínimo (~50 líneas): cargar config → ejecutar pipeline de core
        → exit codes estándar. Sin lógica de negocio propia.
Paso 4: workflow YAML: cron de la ficha + workflow_dispatch para corridas manuales.
Paso 5: corrida manual de humo (yo la disparo). Revisamos juntos el panel de
        calidad de la salida.
Paso 6: README.md generado desde reporte.json.

REGLAS INQUEBRANTABLES (además de las 10 del prompt maestro)
- Si durante la construcción parece necesario código que no existe en core,
  DETENTE y repórtamelo: la decisión de agregarlo a core (nueva versión) es mía.
- El criterio de "terminado" del canal NO es esta sesión: son 5 corridas
  consecutivas limpias según docs/03. Esta sesión termina en el Paso 6.
```

### Tabla de parámetros por canal (rellenar al invocar)

| Canal | `{canal}` | `{version}` core | Ficha en doc 05 |
|---|---|---|---|
| Energía (PILOTO) | `energia` | la vigente al construir | Módulo C |
| Nacional | `nacional` | ídem | Módulo A |
| Internacional | `internacional` | ídem | Módulo B |
| Semanal | `semanal` | ídem | Módulo D (nota: 0 búsquedas, lee ramas `datos`) |

---

## Variantes rápidas por tipo de sesión

**Sesión de fix puntual:**
> [Prompt maestro] + TAREA: "Fix del defecto D{n} según docs/02 y docs/03. Solo los archivos estrictamente necesarios + su test. Un solo commit."

**Sesión de módulo nuevo (repo nuevo):**
> Sustituir la línea del repo por el repo nuevo (ej. `centinela-nacional`) y añadir: "Este repo consume la librería centinela-core vía requirements.txt (git+https). No dupliques código que exista en core."

**Sesión de solo lectura / auditoría:**
> "MODO AUDITORÍA: no modifiques nada. Lee {archivos} y devuélveme un informe de inconsistencias contra docs/03_PLAN_MEJORA.md."

## Qué hacer si Vibe Code rechaza o duda igualmente

1. **Reduce el alcance**: pide un archivo a la vez ("implementa solo core/dedupe.py con su test").
2. **Reafirma el framing analítico**: "es análisis de cobertura de prensa pública con fuentes citadas y verificación SIFT" — el mismo reframing que ya mejoró los resultados con Perplexity.
3. **Muestra el contexto**: pídele que lea docs/01 antes de decidir; los agentes rechazan mucho menos cuando ven que el proyecto es estructurado, documentado y con políticas de verificación.
4. **Nunca** intentes engañarlo sobre la naturaleza del proyecto: además de innecesario (el proyecto es legítimo), degrada la calidad del trabajo del agente.
