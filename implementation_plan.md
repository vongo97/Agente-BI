# 🛡️ Implementation Plan — Hardening de Seguridad Vektra BI

**Objetivo:** Cerrar los 6 críticos de seguridad de la auditoría (06/02/2026) sin romper funcionalidad existente. Cambios incrementales y revertibles.

---

## FASE 1 — Críticos (Mata-prioridades)

### 1.1 Purgar claves Groq hardcodeadas `MODIFY`
- **Archivos:** `server/scratch/update_groq_key.py`, `server/scratch/update_groq_key_invitado.py`
- **Acción:** Reemplazar claves literales por `os.environ["GROQ_API_KEY"]` (leída de argumento/env). Eliminar valores reales del código.
- **Manual (fuera del repo):** Revocar ambas claves en el panel de Groq.

### 1.2 Eliminar fallback JWT predecible `MODIFY`
- **Archivos:** `server/src/utils/common.py` (líneas ~92, 124), `client/src/auth.ts` (~42)
- **Acción:** Si `AUTH_SECRET`/`JWT_SECRET` no está definido → lanzar error al arrancar en vez de usar fallback; permitir fallback **solo** si `ENVIRONMENT=development` explícito.
- **Verificación:** backend arranca con env; falla limpio con mensaje claro sin env.

### 1.3 Blindar sandbox contra filesystem/red `MODIFY`
- **Archivo:** `server/src/utils/executor.py` (+ orquestador embebido si existe en `run.py`)
- **Acción:**
  - Envolver `pd` expuesto: bloquear `pd.read_csv/read_excel/read_json/...` cuando el argumento sea path de archivo o URL http(s).
  - Quitar `io` de la whitelist de imports (o exponer shim que prohíba `io.open` de paths).
  - AST: bloquear atributos peligrosos (`.read`, `.write`, `.open` sobre objetos no permitidos) — validación conservadora lista negra de atributos: `open`, `read_csv`, `read_excel`, `read_parquet`, `to_csv` hacia paths fuera de `temp_dir`.
  - Ampliar `env_clean`: eliminar TODO el entorno excepto `PATH`, `PYTHONPATH`, `TMP`.
  - `pickle.load` → validar que el archivo esté dentro de `temp_dir` del propio sandbox.
- **Verificación:** test que `import io; io.open('...')` y `pd.read_csv('/etc/passwd')` / `pd.read_csv('http://169.254.169.254')` sean rechazados.

### 1.4 SSRF + cifrado en `/connect-sql` `MODIFY`
- **Archivo:** `server/src/routers/data.py` (líneas ~195-217)
- **Acción:**
  - Parsear host de la URL; rechazar loopback, RFC1918, link-local, `169.254.169.254` (allowlist configurable `ALLOWED_SQL_HOSTS`).
  - Cifrar la URL con la función Fernet existente antes de guardarla en `data_sources.url`; descifrar al usar.
  - Limitar `get_db_schema()` a timeout corto.
- **Verificación:** intentar `postgresql://user:pass@127.0.0.1/db` y `...@169.254.169.254/...` → 400.

### 1.5 Eliminar endpoint destructivo `/sources/clear-force` `MODIFY`
- **Archivo:** `server/src/routers/data.py` (~509)
- **Acción:** Eliminar el endpoint por completo (no gatearlo: eliminarlo). Si hay necesidad de depuración, se hace por CLI fuera de la API.
- **Verificación:** `DELETE /sources/clear-force` → 404.

### 1.6 Filtro SQL — endurecer `MODIFY`
- **Archivo:** `server/src/utils/executor.py` (`validate_sql_safety`)
- **Acción:**
  - Whitelist en vez de blacklist: solo permitir statements que empiecen con `SELECT` o `WITH` (tras parseo), un único statement (rechazar `;` seguido de contenido), y rechazar tokens peligrosos en cualquier posición: `ATTACH PRAGMA VACUUM GRANT CREATE TRUNCATE EXEC COPY pg_read_file lo_export xp_cmdshell`.
  - Rechazar `pg_catalog`/`information_schema` sensibles si aplica.

---

## FASE 2 — Altos

| # | Cambio | Archivo | Acción |
|---|---|---|---|
| 2.1 | Uploads sin fallback a texto plano | `data.py:128` | Si `encrypt_file` falla → abortar upload con 500 genérico, no guardar en claro |
| 2.2 | Validar parseo antes de persistir | `data.py:112` | Parsear DataFrame con pandas ANTES de mover a disco; límite de celdas igual a g-sheets |
| 2.3 | Pickle: eliminar fallback en claro | `common.py:200`, `data.py:159/265/401` | Todo por `save_user_data` cifrado; si el descifrado falla → error, no `read_pickle` claro |
| 2.4 | Rate limit `/user-config` | `auth.py:92` | Añadir `@limiter.limit("10/minute")` |
| 2.5 | Sanitizar logs con email | `common.py:208`, `analysis.py:98` | Enmascarar emails (`u***@domain`) en logs |
| 2.6 | Eliminar XSS Mermaid / DOMPurify | `client/.../MermaidPreview.tsx` | `mermaid securityLevel: 'strict'` + `DOMPurify.sanitize(svg, {USE_PROFILES:{svg:true, svgFilters:true}})` |

---

## FASE 3 — UX / Diseño (del reporte visual)

| # | Cambio | Archivos |
|---|---|---|
| 3.1 | Reemplazar `alert()` nativos por `ToastContext` (14 lugares) | `Chat.tsx`(7), `Sidebar.tsx`(4), `ReportBuilder.tsx`(3), `ChatHeader.tsx`, `InteractiveCanvas.tsx` |

---

## 🧪 Plan de Verificación

1. **Backend:** `cd server && pytest` (añadir tests nuevos: sandbox escape, connect-sql SSRF, clear-force 404, crypto fallback).
2. **Frontend:** `cd client && npm run build` (tipos) y `npm test` (tests existentes no deben romperse).
3. **Manual:** arrancar `run_dev.py`, flujo completo: login → upload CSV → chat → dashboard → simulación → export.

## 🚫 Restricciones
- No instalar dependencias nuevas salvo `dompurify` + `@types/dompurify` en client (imprescindible para XSS).
- No cambiar contratos de API; solo endurecer.
- Sin reescrituras masivas: ediciones dirigidas.
- Preservar comentarios/docstrings ajenos.

## 📦 Estado de ejecución

**FASE 1 — Críticos: ✅ COMPLETADA** (todos los ítems código-resolvibles)
**FASE 2 — Altos: ✅ COMPLETADA** (incluye 2.6 XSS/DOMPurify)
**FASE 3 — Diseño: ✅ COMPLETADA** (14 `alert()` → toasts)

**Verificación:**
- `server`: 43/43 tests nuevos de hardening ✅; suite completa 71 pasan ✅; 8 fallos analizados y confirmados como **preexistentes/ambientales** (red Gemini inalcanzable, mocks a atributos inexistentes, aislamiento de tests) — 0 regresiones.
- `client`: `tsc --noEmit` sin errores en código de app (faltan dev-deps de vitest, preexistente).

**Acciones MANUALES pendientes (fuera del código):**
- [ ] Revocar las 2 claves de Groq expuestas en el panel de console.groq.com
- [ ] Rotar `AUTH_SECRET` y `ENCRYPTION_KEY` y `AUTHORIZED_EMAILS` en el `.env` real
- [ ] Purgar el historial de git de `server/scratch/update_groq_key*.py` (git filter-repo / BFG)
- [ ] Activar TLS (:443) en nginx y añadir `limit_req`
- [ ] Configurar `ALLOWED_SQL_HOSTS` si se usan conexiones SQL a hosts conocidos

