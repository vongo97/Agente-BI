# REGLAS ESTRICTAS PARA AGENTES DE IA (AI_RULES.md)

Reglas no negociables de este repositorio. Este archivo se inyecta en el prompt de sistema del motor de analisis (PLANNER / EXECUTOR / VALIDATOR / STRATEGIST). Aplica cada regla sin discusion.

## REGLA #1 - MODELOS DE GEMINI: SOLO LA WHITELIST VIGENTE

- **Whitelist verificada el 2026-11-11** (fuente: `ai.google.dev/gemini-api/docs/deprecations`):
  - `gemini-4-argon` - razonamiento frontier eficiente, 1M ctx. Codigo y agentes.
  - `gemini-4-carbon` - razonamiento mas potente, 1M ctx. Solo analisis profundo.
  - `gemini-3.8-flash` - Flash mas inteligente. Agentes autonomos y trabajo largo.
  - `gemini-3.6-flash` - estable y equilibrado. **Default recomendado.**
  - `gemini-3.5-flash-lite` - el mas barato. Solo tareas masivas.
  - `gemini-3.1-pro-preview` - sin fecha de apagado anunciada; solo si `gemini-3.8-flash` no basta.
- **PROHIBIDO**: `gemini-2.0-flash` (APAGADO el 2026-06-01), `gemini-2.5-flash` y `gemini-2.5-pro` (redirigen el 2026-12-01), `gemini-3-flash-preview` (obsoleto, usar `gemini-3.6-flash`), `gemini-3.7-flash` y `gemini-3.5-flash` (redirigen solos).
- **FUENTE UNICA**: los identificadores de modelo viven en un solo modulo, `server/src/engine/model_catalog.py`. Si ese archivo no existe, crealo antes de tocar modelos. Nunca repitas un string de modelo en otro archivo.
- Si un modelo no esta en la whitelist, no lo uses: actualiza `model_catalog.py` y su fecha de verificacion primero.
- Esta regla ya no dice "familia 3.x intocable": dice "usa la whitelist vigente". Bajar de generacion esta permitido si el modelo concreto sigue vivo.

## REGLA #2 - LOS CLIENTES DE IA NUNCA TOCAN EL EVENT LOOP DE FASTAPI

- Llama a Gemini/Mistral desde funciones `def` (sincronas), nunca desde `async def` directamente.
- El cliente HTTP del SDK se cierra al salir del contexto y falla con `CANNOT SEND A REQUEST, AS THE CLIENT HAS BEEN CLOSED`.
- Si necesitas async, usa la API asincrona nativa del SDK (`client.aio.*`) o `run_in_threadpool` / `asyncio.to_thread` sobre una funcion `def`.
- Patron minimo: `def _llm_call(...)` y `await run_in_threadpool(_llm_call, ...)`.

## REGLA #3 - EL VALIDADOR DE LLAVES DEBE SER FLEXIBLE

- Un error de cuota (429, `quota`, `exhausted`, `rate limit`) significa que **la LLAVE ES VALIDA**: guardala.
- No bloquees la interfaz: permite al usuario cambiar de proveedor (Mistral, OpenAI, Anthropic) mientras se restablece la cuota.
- Un 401/403 si significa llave rechazada: no la actives.
- Ante error de red la validacion es **inconcluyente**: no bloquees al usuario.

## REGLA #4 - CARGA OBLIGATORIA DEL PROTOCOLO DE INTERACCIÓN

- En el primer turno y ante cada requerimiento nuevo, lee la skill del protocolo de interaccion: `.codex/skills/user-interaction-protocol/SKILL.md` (Codex/Antigravity) o `.claude/skills/user-interaction-protocol/SKILL.md` (Claude Code).
- Lee tambien `docs/PROBLEMAS_CONOCIDOS.md` antes de planificar o modificar: si un problema ya esta registrado, no lo re-descubras ni lo repitas.
- Motivo: criterios de aceptacion 10/10, sin reprocesos y sin reincidir en fallos ya documentados.

## REGLA #5 - VERIFICACIÓN OBLIGATORIA ANTES DE DECLARAR TERMINADO

- Backend: `server\.venv\Scripts\python.exe -m py_compile <archivos modificados>` y `server\.venv\Scripts\python.exe -m pytest server\tests -q`.
- Frontend: `cd client; npm run lint; npm run build`.
- No declares completada una tarea sin ejecutar la verificacion, o sin informar explicitamente por que no se pudo ejecutar.
