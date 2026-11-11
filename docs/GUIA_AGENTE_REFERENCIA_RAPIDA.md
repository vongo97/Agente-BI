# Guía de Referencia Rápida para el Agente — Vektra BI

> **Propósito:** Esta guía sintetiza la arquitectura, reglas críticas, rutas de archivos y procedimientos de verificación de Vektra BI.
> **Instrucción para el agente:** Consulta este documento al iniciar cualquier tarea para orientarte de inmediato sin necesidad de explorar todo el árbol del repositorio.

---

## 1. Protocolo de Inicio Obligatorio (Regla 0)

Antes de planificar, escribir código o ejecutar comandos que alteren el repositorio:

1. **Lectura obligatoria:** Consulta [`docs/PROBLEMAS_CONOCIDOS.md`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/docs/PROBLEMAS_CONOCIDOS.md) y [`SKILL.md`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/.codex/skills/known-issues-registry/SKILL.md).
2. **Identificar problemas abiertos:** Verifica si el área que vas a tocar tiene un `P-XX` abierto (por ejemplo `P-03` SQL, `P-05` bucle de filtro, `P-08` red sin timeout, `P-10` cifrado, `P-16` sandbox, `P-55`/`P-56` Render).
3. **No empeorar ni reabrir:** Si la tarea toca un problema cerrado (`P-01`, `P-02`, `P-04`, `P-51`, `P-52`), respeta estrictamente su regla anti-repetición.
4. **Plan previo:** Muestra un plan breve al usuario con los archivos afectados (`MODIFY`, `NEW`, `DELETE`) y espera aprobación antes de ejecutar cambios.

---

## 2. Mapa Arquitectónico del Repositorio

### Backend (`server/`)
* **Punto de entrada:** [`server/main.py`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/server/main.py) (FastAPI app, middlewares CORS, eventos de ciclo de vida).
* **Base de datos:** [`server/src/database.py`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/server/src/database.py) (SQLAlchemy, modelos, migraciones de columnas).
* **Routers (`server/src/routers/`):**
  * [`analysis.py`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/server/src/routers/analysis.py): Endpoint `/analyze` (análisis conversacional y multi-fuente).
  * [`data.py`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/server/src/routers/data.py): Carga de archivos (`/upload`), conexión SQL (`/connect-sql`), Google Sheets, gestión de sesiones.
  * [`dashboard.py`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/server/src/routers/dashboard.py): Endpoints de autogeneración de tableros y filtrado (`/dashboard/filter`).
  * [`simulation.py`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/server/src/routers/simulation.py): Motor de simulación estratégica de escenarios multiagente.
  * [`exports.py`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/server/src/routers/exports.py): Generación de PDFs y presentaciones PPTX ejecutivas.
  * [`auth.py`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/server/src/routers/auth.py): Verificación de sesiones y tokens.
* **Motor Inteligente (`server/src/engine/`):**
  * [`bi_analyst.py`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/server/src/engine/bi_analyst.py): Orquestador principal de análisis, prompts y llamadas a modelos.
  * [`executor.py`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/server/src/engine/executor.py): Sandbox de ejecución de código Python generado por IA (ast check + subproceso).
  * [`providers.py`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/server/src/engine/providers.py): Conectores para OpenAI, Anthropic, Gemini, Groq, Mistral y DeepSeek.
  * [`insight_auditor.py`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/server/src/engine/insight_auditor.py) & [`audit_agent.py`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/server/src/engine/audit_agent.py): Auditoría numérica de afirmaciones del LLM contra los datos reales.
* **Seguridad y Utilidades (`server/src/utils/`):**
  * [`security.py`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/server/src/utils/security.py): Cifrado simétrico Fernet, sanitización de inputs y validación SQL.
  * [`common.py`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/server/src/utils/common.py): Autenticación de usuario (`get_current_user`), persistencia cifrada (`save_user_data`), `ensure_user_session`.
  * [`storage_service.py`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/server/src/services/storage_service.py): Integración con bucket de Supabase Storage.
  * [`limiter.py`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/server/src/utils/limiter.py): Rate limiting por IP/usuario.

---

### Frontend (`client/`)
* **Stack:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4.
* **Estilo global:** *Dark BI Workspace Premium* (tokens en [`client/src/app/globals.css`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/client/src/app/globals.css)). Clases clave: `.panel`, `.btn-primary`, `.btn-ghost`, `.btn-toolbar`, `.input-bi`, `.badge`.
* **Páginas (`client/src/app/`):**
  * [`page.tsx`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/client/src/app/page.tsx): Vista principal con tabs (Chat, Dashboard, Visual Summary, Simulation, Settings).
  * [`layout.tsx`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/client/src/app/layout.tsx): Estructura raíz, providers de contexto y temas.
  * [`login/page.tsx`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/client/src/app/login/page.tsx) & [`LoginForm.tsx`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/client/src/app/login/LoginForm.tsx): Acceso vía OAuth Google / Credenciales.
* **Componentes Principales (`client/src/components/`):**
  * [`Sidebar.tsx`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/client/src/components/Sidebar.tsx): Navegación lateral, subida de archivos y selección de fuentes/conversaciones.
  * [`Chat.tsx`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/client/src/components/Chat.tsx) y subcomponentes (`chat/ChatInput.tsx`, `chat/MessageItem.tsx`, `chat/InsightCards.tsx`).
  * [`DashboardView.tsx`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/client/src/components/DashboardView.tsx) & [`AutoDashGrid.tsx`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/client/src/components/AutoDashGrid.tsx): Renderizado de gráficos Plotly y filtros reactivos.
  * [`SettingsView.tsx`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/client/src/components/SettingsView.tsx) & [`settings/ProviderKeysPanel.tsx`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/client/src/components/settings/ProviderKeysPanel.tsx): Claves de API e integración de proveedores IA.
  * [`SimulationSandbox.tsx`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/client/src/components/SimulationSandbox.tsx) & `simulation/*`: Vistas de simulación estratégica multiagente.
  * [`ReportBuilder.tsx`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/client/src/components/ReportBuilder.tsx): Diseñador y exportador de informes ejecutivos.
* **Estado y Red:**
  * [`context/DashboardContext.tsx`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/client/src/context/DashboardContext.tsx): Estado central (fuentes activas, datasets, mensajes, layout de dashboard).
  * [`lib/api.ts`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/client/src/lib/api.ts): Cliente HTTP (`fetchWithAuth`) para llamadas al backend.

---

## 3. Matriz de Enrutamiento de Skills (`.codex/skills/`)

| Tipo de Tarea | Skill a Consultar | Archivo |
|---|---|---|
| **Antes de cualquier cambio** | Known Issues First (Regla 0) | [`.codex/skills/known-issues-registry/SKILL.md`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/.codex/skills/known-issues-registry/SKILL.md) |
| **Protocolo de trabajo y calidad** | User Interaction Protocol | [`.codex/skills/user-interaction-protocol/SKILL.md`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/.codex/skills/user-interaction-protocol/SKILL.md) |
| **Diseño y UI en Vektra** | Vektra Product Design | [`.codex/skills/vektra-product-design/SKILL.md`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/.codex/skills/vektra-product-design/SKILL.md) |
| **Seguridad, auth y tokens** | Vektra Security Review | [`.codex/skills/vektra-security-review/SKILL.md`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/.codex/skills/vektra-security-review/SKILL.md) |
| **Contratos API y esquemas** | Vektra API Contracts | [`.codex/skills/vektra-api-contracts/SKILL.md`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/.codex/skills/vektra-api-contracts/SKILL.md) |
| **Sandbox y ejecución LLM** | LLM Sandbox Hardening | [`.codex/skills/vektra-llm-sandbox-hardening/SKILL.md`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/.codex/skills/vektra-llm-sandbox-hardening/SKILL.md) |
| **Ingesta de CSV, Excel, SQL** | Vektra Data Ingestion | [`.codex/skills/vektra-data-ingestion/SKILL.md`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/.codex/skills/vektra-data-ingestion/SKILL.md) |
| **Refactorización de base de datos** | Vektra Architecture Refactor | [`.codex/skills/vektra-architecture-refactor/SKILL.md`](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/.codex/skills/vektra-architecture-refactor/SKILL.md) |

---

## 4. Reglas Innegociables Anti-Repetición

1. **Persistencia siempre cifrada (`P-02`):** Prohibido usar `pd.to_pickle()`, `to_csv()` directo o archivos temporales en claro. Toda persistencia pasa por `save_user_data()` en `common.py`.
2. **Sin bypasses de autenticación (`P-01`):** `ENVIRONMENT` por defecto es `production`. Nunca asumir un usuario de prueba salvo en desarrollo local explícito con localhost verificado.
3. **Resolución estricta de claves IA (`P-04`):** Cada llamada a IA debe usar la clave correspondiente al proveedor seleccionado. Prohibido hacer fallback a la clave de Gemini si el proveedor configurado es OpenAI, Groq, etc.
4. **Sandbox permisivo pero seguro (`P-51`, `P-52`):** La allowlist de imports debe permitir módulos esenciales de runtime como `time`, y el análisis AST no debe prohibir métodos válidos de pandas como `rename`.
5. **Cero KPIs inventados en la UI (`P-13`):** Si un dato no viene del backend o del dataset, no hardcodear números ni porcentajes decorativos simulando análisis.
6. **No efectos circulares en React (`P-05`):** Evitar bucles infinitos en `useEffect` donde una acción actualiza una variable que vuelve a disparar el efecto.
7. **Regla de paquetes:** No instalar nuevas dependencias sin justificar las 6 preguntas de seguridad y obtener aprobación explícita del usuario.

---

## 5. Comandos de Verificación Rápida

### Backend (Python)
* Activar entorno virtual (PowerShell):
  ```powershell
  & "server/.venv/Scripts/Activate.ps1"
  ```
* Ejecutar suite de pruebas:
  ```powershell
  cd server
  pytest tests/
  ```
* Ejecutar test específico:
  ```powershell
  pytest tests/test_auth_bypass.py
  ```

### Frontend (Next.js / TypeScript)
* Verificación estricta de tipos de TypeScript (sin emitir archivos):
  ```powershell
  cd client
  npx tsc --noEmit
  ```
* Linter:
  ```powershell
  cd client
  npm run lint
  ```
