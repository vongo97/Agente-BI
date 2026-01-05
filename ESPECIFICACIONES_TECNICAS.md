# 📘 Especificaciones Técnicas y Manual de Funcionamiento - Agente BI

Este documento sirve como guía maestra para desarrolladores (humanos o IA) que deseen comprender, mantener o expandir la plataforma Agente BI.

---

## 🏗️ Arquitectura del Sistema

La plataforma sigue una arquitectura de desacoplamiento entre Frontend y Backend:

- **Frontend**: Next.js 15+ (App Router), TypeScript, Tailwind CSS. Desplegado en **Vercel**.
- **Backend**: FastAPI (Python 3.11+), SQLAlchemy. Desplegado en **Render.com**.
- **Base de Datos**: PostgreSQL (Persistencia de chats, dashboards y configuraciones).
- **IA**: Google Gemini Pro (Motor de razonamiento y generación de código).

---

## 📁 Estructura de Archivos Clave

### 💻 Cliente (Frontend)
- `src/auth.ts`: Configuración de NextAuth v5 con Google OAuth. Maneja la seguridad de entrada.
- `src/lib/api.ts`: Librería de comunicación con el backend (FastAPI).
- `src/components/Chat.tsx`: El corazón de la interfaz. Maneja el envío de preguntas y el renderizado de gráficos/Markdown.
- `src/components/Sidebar.tsx`: Gestión de fuentes de datos (Upload, SQL, GSheets) e historial.
- `src/context/DashboardContext.tsx`: Estado global de la aplicación (Mensajes activos, API Key, vistas).

### ⚙️ Servidor (Backend)
- `main.py`: Punto de entrada de la API. Define todos los endpoints ( `/analyze`, `/upload`, `/dashboard`, etc.).
- `src/engine/bi_analyst.py`: **Cerebro de la IA**. Traduce la pregunta del usuario en código Python ejecutable y genera narrativas estratégicas.
- `src/database.py`: Modelos de la base de datos (Chat, Message, DashboardItem).
- `src/utils/exporter.py`: Lógica para generar reportes en PDF y exportar gráficos PNG.

---

## 🧠 Lógica de Funcionamiento Core

### 1. El Flujo de Análisis ("The Loop")
1. El usuario sube un archivo (CSV/Excel) o conecta una DB.
2. El servidor guarda la referencia en disco/sesión (`sessions_cache`).
3. El usuario pregunta: *"¿Cuál es la tendencia de ventas?"*.
4. **Gemini** recibe el esquema de los datos y la pregunta. Genera un bloque de código Python con **Pandas** y **Plotly**.
5. El servidor ejecuta ese código en un entorno seguro (`exec()`).
6. El resultado (texto + objeto de gráfico `fig`) se envía al frontend.

### 2. Detective de Datos (Radar)
- Realiza un barrido matemático usando **Z-Score** para encontrar valores atípicos (outliers).
- Gemini interpreta esos hallazgos para dar una recomendación estratégica.

### 3. Seguridad y Multi-usuario
- El sistema usa el email de Google como `user_id`.
- Los datos están aislados: un usuario no puede cargar ni ver los chats de otro.

---

## 🚀 Guía de Despliegue y Variables de Entorno

### Backend (Render)
Variables necesarias:
- `DATABASE_URL`: Link de conexión a PostgreSQL.
- `AUTHORIZED_EMAILS`: Lista de correos (separados por coma) permitidos para entrar.

### Frontend (Vercel)
Variables necesarias:
- `NEXT_PUBLIC_API_URL`: URL del backend en Render.
- `AUTH_SECRET`: Llave de seguridad para NextAuth.
- `AUTH_GOOGLE_ID` / `AUTH_GOOGLE_SECRET`: Credenciales de Google Console.

---

## ⚡ Estrategia Render (Keep-Alive)

Para evitar que el servidor gratuito de Render se "apague" por inactividad:
1. **Frontend**: El chat muestra un aviso de "Preparando motor..." si detecta que el backend está hibernando.
2. **Ping**: Se recomienda usar [cron-job.org](https://cron-job.org/) para llamar a la URL raíz del backend cada 14 minutos. Esto lo mantendrá siempre encendido sin costo adicional.
3. **Script**: También puedes ejecutar `python keep_alive.py` desde una PC local conectada a internet.

---

## 🛠️ Cómo Editar el Proyecto

1. **Para cambiar el estilo visual de la IA**: Edita el "Prompt" en `server/src/engine/bi_analyst.py` dentro de la función `analyze_with_gemini`.
2. **Para añadir un nuevo tipo de base de datos**: Modifica la lógica de conexión en `main.py` y añade el componente en el `Sidebar.tsx`.
3. **Para cambiar el diseño del chat**: Dirígete a `client/src/components/Chat.tsx` y ajusta las clases de Tailwind.

---

> **Nota para IA**: Al editar este proyecto, prioriza siempre el renderizado de Markdown limpio y el uso de paletas de colores oscuras (`plotly_dark`) para mantener la estética premium.
