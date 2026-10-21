# Despliegue en Render (Vektra BI)

Todo el stack vive en **Render** (el VPS anterior y Vercel quedan fuera de juego).

## Servicios

| Servicio | URL pública | Plan | Carpeta |
|---|---|---|---|
| Backend canónico (FastAPI + PostgreSQL) | `https://agente-bi-server-7nav-zifr.onrender.com` | free | `server/` |
| Frontend (Next.js) | `https://agente-bi-client-5nx4.onrender.com` | free | `client/` |

> **Backend canónico: `-zifr` (PostgreSQL persistente).** El servicio
> `agente-bi-server-7nav.onrender.com` usa SQLite no persistente y **no debe usarse
> para datos reales**: pierde las fuentes en cada redeploy. El `render.yaml` todavía
> declara el nombre legado `-7nav` para no crear un duplicado al sincronizar el
> Blueprint; el frontend y `NEXT_PUBLIC_API_URL` apuntan al backend `-zifr`.

> **El nombre real de los servicios incluye el sufijo que Render añadió al
> crearlos.** Si un servicio se borra y Render crea otro con distinto sufijo, hay
> que actualizar de golpe `NEXT_PUBLIC_API_URL`, `NEXTAUTH_URL`, `ALLOWED_ORIGINS`
> y el redirect de Google. La CSP del frontend se deriva automáticamente de
> `NEXT_PUBLIC_API_URL` (`client/next.config.ts`), por lo que no hay que tocarla a mano.

> Los nombres con sufijo (`-5nx4`, `-ci55`) los generó Render automáticamente al
> crear el servicio porque el nombre del `render.yaml` ya estaba ocupado. Si esos
> servicios se borran y se recrean, el sufijo cambia y hay que actualizar a mano
> `NEXT_PUBLIC_API_URL`, `NEXTAUTH_URL`, `ALLOWED_ORIGINS` y el redirect de Google.
> **Regla: no renombrar servicios en `render.yaml` sin comprobar antes**, o el
> Blueprint crea duplicados.

> ⚠️ **`cliente-vektra-bi.onrender.com` es un servicio duplicado** creado por error
> al renombrar el servicio en `render.yaml` (el Blueprint lo tomó como servicio
> nuevo). No usarlo: apunta al backend `-ci55` que ya no existe, tiene
> `NEXTAUTH_URL` apuntando a otro dominio —por eso el login acaba en
> `error=Configuration`— y su origen no está en `ALLOWED_ORIGINS`. Se borró del
> panel de Render.

## Variables de entorno obligatorias

Las marcadas `sync: false` en `render.yaml` hay que definirlas **a mano** en el panel
de cada servicio (no se despliegan desde el repo). Ningún valor va en el repo: es
público.

### Backend `agente-bi-server-7nav-zifr`

| Variable | ¿Para qué? | Si falta |
|---|---|---|
| `AUTH_SECRET` | Verifica el JWT que firma el frontend (≥32 chars, `openssl rand -hex 32`) | 500 "falta definir AUTH_SECRET" |
| `AUTHORIZED_EMAILS` | Lista blanca de correos (separados por coma) | **403 a todo el mundo** |
| `ENCRYPTION_KEY` | Cifra las API keys que guarda cada usuario | Ver nota ⚠️ abajo |
| `DATABASE_URL` | Postgres/Supabase (opcional) | Cae a SQLite local (`server/src/database.py`) |
| `GEMINI_API_KEY` | Solo para pruebas internas | Los usuarios usan su propia key, cifrada en su perfil |
| `ALLOWED_ORIGINS` | Ya viene en `render.yaml` | El navegador bloquea con "Failed to fetch" |
| `ENVIRONMENT` | `production` (viene en `render.yaml`) | Nunca uses `development` en Render: activa el bypass de auth |
| `AUDIT_AGENT_ENABLED` | `true` (activo por defecto desde Fase 2; `false` lo desactiva) | `/analyze` no enruta preguntas de auditoría a hechos verificados |

### Frontend `agente-bi-client-5nx4`

| Variable | Valor |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://agente-bi-server-7nav-zifr.onrender.com` (en `render.yaml`) |
| `NEXTAUTH_URL` | `https://agente-bi-client-5nx4.onrender.com` (en `render.yaml`) |
| `NEXTAUTH_SECRET` | **Idéntico** al `AUTH_SECRET` del backend (`sync: false`) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Credenciales de Google OAuth |

`NEXT_PUBLIC_*` se hornea durante el build: cambiar esa variable exige
**redeploy**, no basta con reiniciar.

Redirect URI en Google Cloud Console:
`https://agente-bi-client-5nx4.onrender.com/api/auth/callback/google`

## Diagnóstico rápido de fallos

| Síntoma | Causa habitual | Dónde mirar |
|---|---|---|
| `Failed to fetch` en el navegador | Origen no está en `ALLOWED_ORIGINS`, o el servicio free estaba dormido (primer request da 502 sin headers CORS) | Pre-flight: `curl -X OPTIONS https://agente-bi-server-7nav-zifr.onrender.com/api/v1/upload -H "Origin: https://<frontend>" -H "Access-Control-Request-Method: POST"` |
| `401 Token de sesión inválido` | `NEXTAUTH_SECRET` ≠ `AUTH_SECRET`, o cookie vieja de otro despliegue | Logs: línea `Token inválido: ...` |
| `401 Se requiere token…` | Petición sin cabecera `Authorization` (frontend sin sesión) | Sesión del usuario |
| `403 Usuario no autorizado` / `Acceso denegado: AUTHORIZED_EMAILS…` | Correo fuera de la lista blanca, o lista vacía | Logs: `AUTH_REJECTED motivo=...` |
| `429` | Rate limit (`/upload`: 5/min y 30/h) | Rate limiters en `server/src/routers/` |
| `404` en `NEXT_PUBLIC_API_URL` | Apunta a un host inexistente (servicio borrado o renombrado) | `curl -o NUL -w "%{http_code}" https://<host>/` |

⚠️ **`ENCRYPTION_KEY` formato exacto**: debe ser una clave Fernet, es decir **44
caracteres base64url terminados en `=`**:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

No vale un hash hex (`openssl rand -hex 32`): son 64 caracteres y el backend no
arranca. Desde el commit `fix(security)` una clave mal formada ya no tumba el
servicio (se deriva una clave estable y se avisa en los logs), pero conviene
corregir la variable en el panel: el valor derivado no es reversible ni
auditable.

Render free duerme el servicio tras ~15 min sin uso: el primer request tarda 30-60 s y
puede fallar con un error feo aunque funcione al reintentar.