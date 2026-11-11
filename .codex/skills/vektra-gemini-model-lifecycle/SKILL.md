---
name: vektra-gemini-model-lifecycle
description: Catalogo y ciclo de vida de los modelos de IA de Agente-BI (Google Gemini y Mistral). Usala ANTES de tocar cualquier identificador de modelo, al validar una API key de Gemini, cuando una llamada devuelva 404/429/deprecation, para elegir que modelo asigna a cada rol del motor (PLANNER, EXECUTOR, VALIDATOR, STRATEGIST), y para migrar a un modelo nuevo sin romper produccion. Incluye la whitelist vigente con su fecha de verificacion, las fechas de apagado y redireccion, el procedimiento de migracion y el endpoint muerto de providers.py.
---

# Ciclo de vida de los modelos de IA - Vektra BI

Esta skill es la **fuente de verdad operativa** sobre que modelos de Google Gemini y
Mistral puede usar Agente-BI. `AI_RULES.md` (inyectado en el prompt de sistema del
motor) contiene solo el resumen; aqui esta el detalle, la tabla de fechas y el
procedimiento.

> **Verificacion de esta skill: 2026-11-11.** Fuente primaria:
> `https://ai.google.dev/gemini-api/docs/deprecations` y
> `https://ai.google.dev/gemini-api/docs/models`. Cuando la fecha quede vieja, vuelve
> a esas paginas antes de cambiar un modelo.

## 1. Por que existo esta skill

La regla #1 de `AI_RULES.md` se escribio congelada en "familia 3.x intocable" y hoy es
**incorrecta en dos direcciones**:

1. Gemini 4 ya existe (`gemini-4-carbon`, `gemini-4-argon`) y es superior a todo 3.x.
2. La propia regla se incumple en produccion: `server/src/engine/providers.py` declara
   `"model": "gemini-2.0-flash"`, un endpoint **apagado el 2026-06-01**. Ese string no
   puede funcionar.

Regla vigente: **usa solo la whitelist de abajo**, no "usa 3.x".

## 2. Whitelist vigente (2026-11-11)

| Modelo | Tipo | Contexto | Cuando usarlo |
|--------|------|----------|----------------|
| `gemini-4-carbon` | Frontier, maximo razonamiento | 1M | Analisis profundo, razonamiento de negocio, auditorias complejas |
| `gemini-4-argon` | Frontier, eficiente en coste | 1M | Codigo generado por LLM, agentes autonomos, uso intensivo |
| `gemini-3.8-flash` | Flash mas inteligente | 1M | Default de alto rendimiento; agentes de tareas largas |
| `gemini-3.6-flash` | Estable y equilibrado | 1M | **Default recomendado** para produccion |
| `gemini-3.5-flash-lite` | Flash mas barato | 1M | Tareas masivas, clasificacion, preprocesamiento |
| `gemini-3.1-pro-preview` | Preview, sin apagado anunciado | 1M | Solo si `gemini-3.8-flash` no da la calidad exigida |
| `gemini-nano-banana-2.1` | Imagen | n/a | Generacion/edicion de imagenes (dashboards, visuales) |
| `gemini-embedding-2` | Embeddings multimodales | n/a | Busqueda semantica / RAG sobre datasets |
| `mistral-large-latest` | Alternativa europea | - | Fallback cuando Gemini da quota |

## 3. Modelos PROHIBIDOS y por que

| Modelo | Estado | Fecha | Sustituto |
|--------|--------|-------|-----------|
| `gemini-2.0-flash` | **APAGADO** | 2026-06-01 | `gemini-3.6-flash` |
| `gemini-2.0-flash-lite` | **APAGADO** | 2026-06-01 | `gemini-3.1-flash-lite` |
| `gemini-2.5-flash` | Deprecado, redirige | 2026-12-01 | `gemini-3.5-flash-lite` |
| `gemini-2.5-pro` | Deprecado, redirige | 2026-12-01 | `gemini-3.8-flash` |
| `gemini-3-flash-preview` | Obsoleto (vive, no recomendado) | - | `gemini-3.6-flash` |
| `gemini-3.7-flash` | Redirige | - | `gemini-3.8-flash` |
| `gemini-3.5-flash` | Redirige | - | `gemini-3.6-flash` |
| `gemini-2.5-computer-use-preview-10-2025` | **APAGADO** | 2026-07-28 | `gemini-3.8-flash` |
| `gemini-3-pro-preview` | **APAGADO** | 2026-03-09 | `gemini-3.1-pro-preview` |

Los "redirigen" significa que la API sigue respondiendo pero **cambia el modelo y la
facturacion por debajo** a partir de la fecha indicada. No son un fallo visible, son
una trampa de coste: el dia de la redireccion, tu factura cambia sin que nadie toque
el codigo.

`gemini-2.5-flash-lite` no esta deprecado, pero Google limita los 2.5 a usuarios
preexistentes y recomienda `gemini-3.5-flash-lite` o `gemini-3.8-flash` para proyectos
nuevos. No lo uses como default.

## 4. Donde viven los strings de modelo (FUENTE UNICA)

Hoy hay **dos** lugares, y por eso hay un endpoint muerto:

| Archivo | Lineaapprox. | Estado |
|---------|--------------|--------|
| `server/src/engine/bi_analyst.py` | `MODELS` (L25-32) | `gemini-3-flash-preview` + `gemini-3.1-pro-preview` (viven, pero obsoletos) |
| `server/src/engine/swarm_engine.py` | L22-23 | duplica los mismos strings |
| `server/src/engine/providers.py` | `PROVIDERS["gemini"]["model"]` (L33) | **`gemini-2.0-flash` = APAGADO** |

Regla de arquitectura (ver `AI_RULES.md` #1): **todos los identificadores de modelo
deben vivir en un solo modulo**, `server/src/engine/model_catalog.py`, con la whitelist
y la fecha de verificacion como datos. Los demas modulos importan de ahi:

```python
# server/src/engine/model_catalog.py
GEMINI_DEFAULT = "gemini-3.6-flash"      # default de produccion
GEMINI_FAST    = "gemini-3.5-flash-lite" # tareas masivas
GEMINI_AGENT   = "gemini-3.8-flash"      # agentes de tareas largas
GEMINI_DEEP    = "gemini-4-carbon"       # razonamiento profundo
GEMINI_CODE    = "gemini-4-argon"        # codigo generado
VERIFIED_ON    = "2026-11-11"            # fecha de la ultima verificacion
```

Si ese archivo no existe, crearlo es el primer paso de cualquier cambio de modelo.
Nunca anadas un string de modelo nuevo en un archivo que no sea el catalogo.

## 5. Como verificar un modelo ANTES de usarlo

No te fies de la memoria ni de un documento. Comprueba contra la API:

```powershell
# Listar todos los modelos disponibles para tu key
$env:GOOGLE_API_KEY = "<tu-key>"
curl "https://generativelanguage.googleapis.com/v1beta/models?key=$env:GOOGLE_API_KEY"

# Comprobar uno concreto (404 = no existe o esta apagado)
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash?key=$env:GOOGLE_API_KEY"

# Con el SDK (script standalone, nunca dentro del event loop)
python -c "from google import genai; c=genai.Client(); [print(m.name) for m in c.models.list()]"
```

Criterio de decision:

- `200` + el modelo aparece en la lista -> vivo, usalo (y anadelo a la whitelist).
- `200` + aparece en la lista pero Google marca "deprecated" -> migra ya.
- `404 NOT_FOUND` -> apagado o nombre incorrecto. Sustituye segun la tabla de la seccion 3.
- `429 RESOURCE_EXHAUSTED` -> el modelo existe; el problema es de cuota (ver `AI_RULES.md` #3).

Ademas, revisa siempre la pagina de deprecaciones antes de un despliegue: las fechas se
mueven y no avisan por log.

## 6. Que modelo para cada rol del motor

El motor de analisis (`server/src/engine/`) tiene cuatro roles LLM, definidos en
`skill_loader.py::AGENT_SKILLS_MAP`:

| Rol | Modelo recomendado | Razon |
|-----|---------------------|-------|
| PLANNER | `gemini-3.6-flash` | Stable, plano, muchas llamadas |
| EXECUTOR | `gemini-4-argon` | Genera codigo Python: pide razonamiento de codigo |
| VALIDATOR | `gemini-3.6-flash` | Verificacion de salida, coste sensible |
| STRATEGIST | `gemini-4-carbon` | Reporte final y lectura de negocio |
| Swarm / batch | `gemini-3.8-flash` | Agente autonomo de tareas largas |
| Tareas masivas | `gemini-3.5-flash-lite` | Coste minimo |

Nota: hoy `bi_analyst.py` no selecciona por rol, solo tiene tres constantes
(`GEMINI_SWARM`, `GEMINI_ANALYTICS`, `GEMINI_STRATEGY`) mas un alias `GEMINI`. Al
migrar, mapea esas constantes al catalogo y no las dupliques.

## 7. Procedimiento de migracion (sin romper produccion)

1. **Verifica** el modelo sustituto contra la API (seccion 5) y actualiza la fecha de
   verificacion.
2. **Crea o actualiza** `server/src/engine/model_catalog.py` con el string nuevo.
3. **Cambia** los importes en `bi_analyst.py`, `swarm_engine.py` y `providers.py`.
   Elimina los strings duplicados: no debe quedar ningun literal de modelo fuera del
   catalogo.
4. **Busca residuos** en todo el repo (excluye `.venv`, `node_modules`, `.next`):

   ```powershell
   Get-ChildItem server,client -Recurse -Include *.py,*.ts,*.tsx,*.json,*.env,*.example |
     Where-Object { $_.FullName -notmatch '\\(\.venv|node_modules|\.next)\\' } |
     Select-String -Pattern 'gemini-[0-9][a-z0-9\.\-]*'
   ```

5. **Verifica sintaxis** (no declares terminado sin esto):

   ```powershell
   server\.venv\Scripts\python.exe -m py_compile server\src\engine\bi_analyst.py `
     server\src\engine\providers.py server\src\engine\swarm_engine.py
   server\.venv\Scripts\python.exe -m pytest server\tests -q
   ```

6. **Prueba real** con una llamada minima y comprueba que el texto sale limpio.
   Cuidado: `nvidia/nemotron-3-ultra-550b-a55b` devuelve sopa de tokens en streaming
   pero texto correcto en no-streaming (bug upstream de NVIDIA NIM, no del SDK).
7. **Documenta** el cambio en `docs/PROBLEMAS_CONOCIDOS.md` si afecta a un P-XX
   abierto, y actualiza `AI_RULES.md` #1 con la nueva whitelist y fecha.
8. **Actualiza esta skill** con la misma fecha. Si las dos se desincronizan, vuelve a
   ser la regla congelada que causo el problema.

## 8. Errores tipicos

- "El modelo 3.x no funciona, lo bajo a 2.5" -> al revés: 2.x esta apagado o redirige.
- "La API devuelve 429, cambio de modelo" -> el modelo esta bien; es cuota. Ver
  `AI_RULES.md` #3.
- "Actualizo `MODELS` en `bi_analyst.py`" -> primero el catalogo, luego los importes.
- "Uso `gemini-flash-latest`" -> los alias `latest` se hot-swapean sin aviso. Usa
  strings concretos para produccion.
- "El modelo 3.1-pro-preview es preview, lo quito" -> sin fecha de apagado anunciada;
  mientras viva, es legitimo.
