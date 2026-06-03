---
tags: [proyecto, activo, bi, ai, vektra]
fecha_actualizacion: 2026-05-21
---
# 🚀 Vektra BI (Agente-BI)

## 📝 Descripción y Contexto
**Vektra BI** (internamente conocido como Agente-BI) es una plataforma avanzada de Inteligencia de Negocios (BI) impulsada por Inteligencia Artificial. Está diseñada para transformar datos crudos en decisiones estratégicas sin necesidad de saber programar. Permite a los usuarios cargar datos desde múltiples fuentes, realizar consultas en lenguaje natural ("¿Cuál es la tendencia de ventas?"), y generar análisis complejos con gráficos interactivos y narrativas estratégicas.

### ✨ Funcionalidades Principales de Vektra:
- **Pool de Datos (Hasta 10 fuentes):** Soporta archivos locales (CSV/Excel), enlaces públicos de [[Google Sheets]] y conexiones directas a Bases de Datos [[SQL]].
- **Múltiples Motores de IA:** 
  - ⚡ *Gemini 3.1 Flash* (Rápido, ideal para código y gráficos).
  - 🟣 *Mistral Large* (Ideal para redacciones estratégicas complejas).
  - 🌌 *Cerebro Dual* (Sistema Híbrido que combina la potencia analítica de Gemini con las conclusiones de Mistral).
- **Herramientas Automáticas (1-Clic):**
  - *Magic Clean:* Limpieza automática de datos (nulos, duplicados, formatos).
  - *Auto Dash:* Generación instantánea de dashboards a partir de una tabla de datos.
- **Detective de Datos:** Auditoría silenciosa usando **Z-Score** para alertar sobre valores atípicos (outliers) graves.
- **Simulador Multi-Agente:** Un entorno único de debate donde diferentes agentes de IA (Estratega, Analista, Crítico) discuten hipótesis sobre los datos.
- **Reportes Profesionales:** Exportación a PDF simple, reportes ejecutivos avanzados en PDF/PPTX y descarga de gráficos en PNG.

## 🛠️ Tecnologías y Conceptos (Enlaces para Grafo)
- [[Next.js]] (Frontend App Router v16.1.1)
- [[FastAPI]] (Backend Modular v0.115.0)
- [[PostgreSQL]] y [[SQLite]] (Base de Datos)
- [[Google Gemini Pro]] y [[Mistral]] (Motores LLM)
- [[Vercel]] (Despliegue Frontend)
- [[Render]] (Despliegue Backend)
- [[Supabase]] (Sincronización Cloud)
- [[Pandas]] y [[Plotly]] (Análisis y Visualización interactiva)

## 🕰️ Línea de Tiempo (Pasado, Presente y Futuro)

### 🔙 Qué ha pasado
- Se construyó el motor base `bi_analyst.py` que traduce preguntas a código ejecutable.
- **Refactorización Completa:** El monolito del backend se modularizó usando `APIRouter` (dividiendo en Auth, Data, Analysis, Simulation).
- Se implementó un robusto sistema de seguridad: **Cifrado Fernet** para proteger las API Keys en la base de datos.
- Se implementó un **Sandbox de Ejecución** con un timeout de 10 segundos para prevenir bloqueos por código infinito generado por la IA.
- Se implementó la persistencia de sesiones mediante `pickle` y almacenamiento local/cloud para no perder el estado tras reiniciar el servidor.

### 🔄 Qué está pasando (Estado Actual)
- Vektra es altamente funcional, permitiendo anclar (Pin) gráficos generados por chat directamente a un **Panel (Dashboard) Ejecutivo**.
- El proyecto cuenta con un frontend premium con animaciones en `framer-motion` y un sistema de aislamiento de datos estricto (multi-usuario por email).
- Calificación de arquitectura interna de 8.2/10, acercándose a niveles de producción real.

### 🔜 Qué pasará (Próximos Pasos)
- Implementar **Alembic** para un control de versiones y migraciones de la base de datos profesional.
- Restringir el **CORS** a dominios específicos para mejorar la seguridad en producción.
- Añadir **Rate Limiting** para proteger el consumo de tokens de las APIs de IA.
- Refactorizar componentes densos del frontend (`Chat.tsx` y `SimulationSandbox.tsx`) dividiéndolos en sub-componentes más manejables.
- Aumentar la cobertura de Testing (tests de integración para los nuevos routers).

## 💡 Arquitectura del Sistema
- **Frontend:** Estructura basada en React 19, Tailwind v4, y gestión de estado mediante `DashboardContext`.
- **Backend:** Uvicorn + FastAPI, con protección de builtins peligrosos al ejecutar código IA dinámicamente. 
- **Flujo ("The Loop"):** Usuario pregunta -> Gemini analiza esquema -> Genera código Pandas/Plotly -> Backend ejecuta en entorno seguro -> Frontend renderiza el objeto gráfico.
