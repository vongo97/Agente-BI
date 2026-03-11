# 🔍 Evaluación Completa — Agente BI

## Resumen Ejecutivo

**Agente BI** es una plataforma de inteligencia de negocios impulsada por IA que permite a los usuarios subir datos (CSV, Excel, SQL, Google Sheets) y hacer preguntas en lenguaje natural que se traducen en análisis con gráficos Plotly y narrativas estratégicas generadas por LLMs (Gemini/Mistral).

| Dimensión         | Calificación | Nota                                          |
| ----------------- | ------------ | --------------------------------------------- |
| 🏗️ Arquitectura   | ⭐⭐⭐⭐     | Desacoplamiento frontend/backend sólido       |
| 🔒 Seguridad      | ⭐⭐⭐       | Sandbox AST presente, pero con gaps           |
| 📊 Funcionalidad  | ⭐⭐⭐⭐⭐   | Muy completo para un MVP avanzado             |
| 🧪 Testing        | ⭐⭐         | Cobertura mínima (1 archivo, 5 tests)         |
| 📝 Documentación  | ⭐⭐⭐⭐     | Buen `ESPECIFICACIONES_TECNICAS.md`           |
| 🎨 Frontend       | ⭐⭐⭐⭐     | Stack moderno, bien estructurado              |
| 🚀 DevOps         | ⭐⭐⭐       | DevContainer + deploy scripts, pero sin CI/CD |
| 📦 Mantenibilidad | ⭐⭐⭐       | `main.py` monolítico necesita refactor        |

**Calificación Global: 7.2 / 10** — Un proyecto impresionante para un MVP, con áreas claras de mejora para producción.

---

## 📁 Análisis de Arquitectura

### Stack Tecnológico

| Capa          | Tecnología                       | Versión       |
| ------------- | -------------------------------- | ------------- |
| Frontend      | Next.js (App Router)             | 16.1.1        |
| UI Framework  | React                            | 19.2.3        |
| Estilos       | Tailwind CSS                     | v4            |
| Animaciones   | framer-motion                    | 12.x          |
| Gráficos      | Plotly.js + react-plotly.js      | 3.3.1         |
| Auth Frontend | NextAuth                         | 5.0.0-beta.30 |
| Backend       | FastAPI + Uvicorn                | latest        |
| ORM           | SQLAlchemy                       | latest        |
| DB            | PostgreSQL (prod) / SQLite (dev) | —             |
| IA Principal  | Google Gemini 2.5 Flash          | latest        |
| IA Secundaria | Mistral Large                    | latest        |
| Exportación   | FPDF2, python-pptx, Kaleido      | —             |

### Estructura de Archivos

```
Agente-BI/
├── client/                    # Frontend Next.js
│   ├── src/
│   │   ├── app/               # App Router (page, layout, login, api)
│   │   ├── components/        # 8 componentes React
│   │   │   ├── Chat.tsx       # 29KB - Componente principal de interacción
│   │   │   ├── Sidebar.tsx    # 25KB - Navegación + fuentes de datos
│   │   │   ├── DashboardView  # 13KB - Vista de dashboard
│   │   │   └── ...
│   │   ├── context/           # DashboardContext + ThemeContext
│   │   └── lib/api.ts         # 21 funciones de comunicación con backend
│   └── next.config.ts         # Proxy /backend → FastAPI
│
├── server/                    # Backend FastAPI
│   ├── main.py                # 674 líneas - MONOLITO con 33 endpoints
│   ├── app.py                 # 200 líneas - Versión legacy Streamlit
│   ├── src/
│   │   ├── engine/
│   │   │   ├── bi_analyst.py  # 523 líneas - Motor multi-engine IA
│   │   │   ├── executor.py    # 222 líneas - Sandbox de ejecución
│   │   │   ├── prompts.py     # 192 líneas - 8 plantillas LLM
│   │   │   └── pptx_gen.py    # Generador de presentaciones
│   │   ├── database.py        # 4 modelos ORM
│   │   └── utils/             # auth, exporter, report_gen
│   ├── tests/
│   │   └── test_engine.py     # 81 líneas, 5 tests
│   └── requirements.txt       # 22 dependencias
│
└── ESPECIFICACIONES_TECNICAS.md
```

---

## ✅ Fortalezas

### 1. Motor Multi-Engine Inteligente

El sistema soporta 3 modos de IA (`gemini`, `mistral`, `hybrid`), donde el modo híbrido usa Gemini como "ingeniero de código" y Mistral como "estratega narrativo". Excelente diseño de separación de responsabilidades.

### 2. Sandbox de Ejecución con Validación AST

[executor.py](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/server/src/engine/executor.py) implementa:

- Análisis AST para detectar patrones maliciosos
- Imports restringidos (solo pandas, plotly, numpy, etc.)
- Builtins limitados (sin `eval`, `exec`, `open`)
- `SmartDataContext` con alias automáticos para compatibilidad con "alucinaciones" de la IA

### 3. Prompts Centralizados y Bien Diseñados

[prompts.py](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/server/src/engine/prompts.py) centraliza 8 plantillas de alta calidad con roles claros (Ingeniero, Estratega, Auditor, Consultor BI).

### 4. Suite de Features Completa

- Upload CSV/Excel + conexión SQL + Google Sheets
- Chat conversacional con historial persistente
- Dashboard con pin/unpin de gráficos
- Auto-Dashboard (generación automática de 4 gráficos)
- Exportación: PNG, PDF, PPTX
- Limpieza IA de datos
- Detección de anomalías (Z-Score + interpretación IA)
- Sugerencias inteligentes de preguntas

### 5. Frontend Moderno

Stack de última generación (Next.js 16, React 19, Tailwind v4) con proxy inteligente via rewrites y soporte para tema oscuro/claro.

---

## ⚠️ Áreas de Mejora

### 🔴 Problemas Críticos

#### 1. `main.py` es un Monolito de 674 líneas

Todos los 33 endpoints viven en un solo archivo. Esto dificulta el mantenimiento y testing.

> [!CAUTION]
> **Refactor recomendado**: Separar en FastAPI Routers por dominio:
>
> - `routers/data.py` → upload, connect-sql, connect-gsheets, clean-data
> - `routers/analysis.py` → analyze, suggest-questions, detect-anomalies
> - `routers/dashboard.py` → pin, unpin, get, auto-dashboard
> - `routers/exports.py` → chart, report, pdf, pptx
> - `routers/auth.py` → validate-key, user-config

#### 2. Almacenamiento de Datos en Memoria (`data_store = {}`)

Los datos del usuario se guardan en un diccionario Python en memoria. Esto significa:

- **Se pierden al reiniciar** el servidor
- **No escala** con múltiples workers/instancias
- **Memory leaks potenciales** si no se limpia

> [!IMPORTANT]
> Migrar a Redis o almacenamiento en disco con gestión de TTL.

#### 3. API Keys almacenadas en texto plano en la DB

La tabla `UserConfig` guarda `gemini_key`, `mistral_key` y `gamma_key` sin cifrar. Cualquier acceso a la DB expone las keys.

> [!CAUTION]
> Implementar cifrado simétrico (Fernet) para las API keys en reposo.

#### 4. `exec()` en Producción

Aunque existe validación AST, el código generado por IA se ejecuta con `exec()`, lo cual es un riesgo inherente. Algunos gaps detectados:

- No hay timeout para la ejecución (un loop infinito bloquea el worker)
- No hay límite de memoria
- `getattr` está en los builtins permitidos, lo que podría usarse para acceso indirecto a atributos peligrosos

### 🟡 Problemas Moderados

#### 5. Código Legacy Muerto

- [app.py](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/server/app.py) es la versión Streamlit anterior (200 líneas) que ya no se usa
- [auth.py](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/server/src/utils/auth.py) usa `streamlit` imports pero el frontend es Next.js ahora
- Archivo `data_connectors.py` en la raíz del client (parece fuera de lugar)

#### 6. Cobertura de Testing Mínima

Solo existe un archivo de tests ([test_engine.py](file:///c:/Users/vongo/OneDrive/Escritorio/Proyectos/Agente-BI/server/tests/test_engine.py)) con 5 tests unitarios. No hay:

- Tests de integración para los endpoints
- Tests del frontend
- Tests E2E
- CI/CD que ejecute los tests automáticamente

#### 7. CORS Totalmente Abierto

```python
allow_origin_regex=".*"  # Permite TODOS los orígenes
```

Esto es un riesgo en producción. Debería limitarse a los dominios conocidos.

#### 8. Sin Versionado de API

Los endpoints no tienen prefijo de versión (`/api/v1/`), lo que dificulta cambios futuros sin romper clientes existentes.

#### 9. Sin Rate Limiting

No hay protección contra abuso de la API. Un usuario podría hacer miles de peticiones de análisis (que consumen tokens de IA costosos).

#### 10. Logging Inconsistente

Mezcla de `print()`, `logger.error()` y `logger.warning()`. Debería estandarizarse con logging estructurado.

### 🟢 Mejoras Menores

#### 11. Dependencias No Versionadas

`requirements.txt` no fija versiones. Esto puede causar builds inconsistentes:

```
# Actual
fastapi
pandas
# Recomendado
fastapi==0.115.0
pandas==2.2.0
```

#### 12. Sin Migraciones de Base de Datos

Se usa `Base.metadata.create_all()` directamente. Para producción, sería mejor usar **Alembic** para migraciones controladas.

#### 13. `declarative_base()` Deprecado

SQLAlchemy recomienda usar `DeclarativeBase` desde la v2.0:

```python
# Deprecado
Base = declarative_base()
# Moderno
from sqlalchemy.orm import DeclarativeBase
class Base(DeclarativeBase): pass
```

#### 14. Import Duplicado de `logging` en bi_analyst.py

```python
# Línea 7
import logging
logger = logging.getLogger(__name__)
# Línea 395 (duplicado)
import logging
logger = logging.getLogger(__name__)
```

---

## 🗺️ Roadmap Recomendado

### Fase 1 — Estabilización (1–2 semanas)

- [ ] Refactorizar `main.py` en FastAPI Routers
- [ ] Eliminar código legacy (`app.py`, auth Streamlit)
- [ ] Fijar versiones en `requirements.txt`
- [ ] Agregar timeout al `exec()` del sandbox
- [ ] Restringir CORS a dominios conocidos

### Fase 2 — Seguridad (1 semana)

- [ ] Cifrar API keys en la DB
- [ ] Remover `getattr` de los builtins del sandbox
- [ ] Implementar rate limiting (ej: slowapi)
- [ ] Agregar versionado de API (`/api/v1/`)

### Fase 3 — Calidad (2 semanas)

- [ ] Configurar logging estructurado (ej: structlog)
- [ ] Escribir tests de integración para endpoints críticos
- [ ] Configurar CI/CD (GitHub Actions)
- [ ] Implementar Alembic para migraciones
- [ ] Migrar data_store a Redis

### Fase 4 — Escalabilidad (Futuro)

- [ ] Migrar de `exec()` a ejecución en containers aislados
- [ ] Implementar WebSockets para análisis streaming
- [ ] Añadir caché de resultados (evitar re-análisis)
- [ ] Monitoreo con Sentry o equivalente

---

## 📊 Métricas del Proyecto

| Métrica                       | Valor                                        |
| ----------------------------- | -------------------------------------------- |
| Archivos de código (backend)  | ~15 archivos                                 |
| Archivos de código (frontend) | ~18 archivos                                 |
| Líneas de código backend      | ~2,200+                                      |
| Líneas de código frontend     | ~90,000+ (incluyendo Chat.tsx, Sidebar.tsx)  |
| Endpoints API                 | 33                                           |
| Modelos de DB                 | 4 (Chat, Message, UserConfig, DashboardItem) |
| Tests unitarios               | 5                                            |
| Dependencias Python           | 22                                           |
| Dependencias npm              | 18                                           |
| Prompts de IA                 | 8 plantillas centralizadas                   |

---

> [!NOTE]
> Este análisis se basa en la revisión estática del código fuente. No se ejecutó la aplicación ni se corrieron los tests existentes como parte de esta evaluación. Para una auditoría más profunda, se recomienda ejecutar los tests, analizar el rendimiento en carga, y realizar un pentest del sandbox de ejecución.
