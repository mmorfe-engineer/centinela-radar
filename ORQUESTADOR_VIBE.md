# ORQUESTADOR — Secuencia Maestra para Mistral Vibe Code

Pegar este bloque AL INICIO de **cualquier** sesión de Vibe Code del ecosistema CENTINELA/RADAR, seguido del prompt específico de la fase. Hace que Vibe verifique en qué punto de la secuencia global estamos y se niegue a construir fuera de orden.

---

```
SECUENCIA MAESTRA DEL ECOSISTEMA (no construyas nada fuera de este orden)

  FASE 1: centinela-core        → completar módulos → tests verdes → tag v1.0
  FASE 2: centinela-radar       → requiere core@v1.0 instalable   (paralelo con Fase 3)
  FASE 3: centinela-energia     → requiere core@v1.0 (canal piloto CENTINELA)
  FASE 4: centinela-nacional    → requiere Fase 3 terminada (5 corridas limpias)
  FASE 5: centinela-internacional → ídem
  FASE 6: centinela-semanal     → requiere Fases 3-5 con ≥2 semanas de rama 'datos'
  FASE 7: centinela-sala        → la última; reutiliza todo

VERIFICACIÓN OBLIGATORIA AL INICIAR (antes de tu plan, ejecútala y repórtame):
1. ¿En qué repositorio estamos? ¿A qué fase corresponde?
2. Si la fase requiere centinela-core: verifica que
   pip install git+https://github.com/mmorfe-engineer/centinela-core@v1.0
   instala sin error y que `python -c "from core.dedupe import deduplicar"`
   importa. Si falla → DETENTE y repórtame: la fase previa no está terminada.
3. Si la fase es un canal 4-7: pregúntame si el canal anterior cumplió su
   criterio de terminado (5 corridas limpias). No lo asumas.
4. Revisa que docs/ del repo contenga los documentos que el prompt de la fase
   manda leer. Si falta alguno → DETENTE y dime cuál.
Solo después de reportar estas 4 verificaciones, presenta tu plan del Paso 1.

DIVISIÓN DE RESPONSABILIDADES (no intentes hacer lo que es mío)
- MÍO (Morfe, fuera de tus sesiones): crear los repos en GitHub, subir las
  carpetas SUBIR_*, cargar secretos en Settings→Actions, disparar corridas
  manuales, dar los OK entre pasos, crear los tags de versión que yo apruebe.
- TUYO (Vibe): leer docs, escribir código y tests, commits y push al repo de
  la sesión, reportar verificaciones y esperar mis OK.

AL TERMINAR TU FASE, tu último mensaje debe incluir:
- Checklist de lo completado con evidencia (tests en verde, archivos).
- Qué me toca hacer a MÍ antes de la siguiente fase (tag, secretos, corridas).
- Cuál es la siguiente fase y qué prompt me corresponde usar.
```

---

## Cómo se usa en la práctica (tu operación por fase)

| Fase | Tú haces antes | Pegas en Vibe | Prompt de la fase |
|---|---|---|---|
| 1 | Crear repo + subir `SUBIR_repo_centinela-core/` | ORQUESTADOR + | `PROMPT_VIBE_CODE_CORE.md` |
| 2 | Crear repo + subir `SUBIR_repo_centinela-radar/` + secretos | ORQUESTADOR + | `PROMPT_VIBE_CODE_RADAR.md` |
| 3–6 | Crear repo del canal + secretos | ORQUESTADOR + | doc 09 §Prompt de Construcción de Canal (con `{canal}`) |
| 7 | Crear repo | ORQUESTADOR + | doc 06 como spec + prompt de canal adaptado |

> El tag `v1.0` de core lo creas tú cuando la Fase 1 termine con todo en verde:
> `git tag v1.0 && git push origin v1.0` (o desde GitHub → Releases).
