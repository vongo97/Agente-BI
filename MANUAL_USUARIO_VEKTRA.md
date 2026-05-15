# 📘 Manual de Usuario - Vektra BI

¡Bienvenido a **Vektra BI**! Esta plataforma de Inteligencia de Negocios (BI) impulsada por Inteligencia Artificial está diseñada para transformar tus datos crudos en decisiones estratégicas sin necesidad de saber programar. 

Este manual te guiará paso a paso para que aproveches al máximo todas las herramientas, desde la carga de datos hasta la generación de reportes profesionales.

---

## 1️⃣ Primeros Pasos: Conectando tus Datos

Antes de poder interactuar con el Analista AI, necesitas proporcionarle datos. Vektra te permite mantener un **Pool de Datos** activo con hasta 10 fuentes simultáneas.

Para añadir datos, dirígete a la barra lateral izquierda (Sidebar):

1. **Archivos Locales (CSV / Excel):** 
   Haz clic en el recuadro punteado que dice **"Subir Nuevo Dataset"**. Puedes seleccionar uno o varios archivos al mismo tiempo.
2. **Google Sheets:**
   Haz clic en la opción **"Google Sheets"**, pega la URL de tu hoja de cálculo (asegúrate de que sea pública o tenga los permisos necesarios) y haz clic en **Conectar**.
3. **Base de Datos SQL:**
   Haz clic en **"Base de Datos SQL"**, ingresa tu URL de conexión (ej. `postgresql://usuario:pass@host/db`) y haz clic en **Conectar**.

> **💡 Tip:** Puedes ver cuántas columnas tiene cada archivo cargado y eliminar fuentes individuales haciendo clic en la "X", o limpiar todo el pool de una vez con el botón **Limpiar Todo**.

---

## 2️⃣ Explorando la Interfaz (Menú Principal)

En la barra lateral izquierda encontrarás el menú principal para navegar entre las diferentes vistas de Vektra:

- 💬 **Chat:** La pantalla principal donde interactúas con la IA, haces preguntas y visualizas gráficos.
- 📊 **Panel (Dashboard):** Aquí se guardan los gráficos que decides "Anclar" (Pin) para tener una vista ejecutiva de tus métricas clave.
- 🧠 **Simulador:** Un entorno de debate donde agentes de IA (Ej. Estratega, Analista) discuten hipótesis sobre tus datos.
- ⚙️ **Config:** Configuración general y gestión de tus API Keys (Gemini, Mistral).

---

## 3️⃣ El Chat: Tu Analista AI Personal

Una vez que tengas datos cargados, puedes empezar a hacer preguntas estratégicas en la barra inferior del Chat.

### ¿Cómo hacer preguntas?
No necesitas ser técnico. Simplemente pregunta en lenguaje natural:
- *"¿Cuál ha sido la tendencia de ventas en los últimos 6 meses?"*
- *"Muéstrame los productos con mayor margen de ganancia."*
- *"¿Hay alguna correlación entre el gasto en marketing y los nuevos clientes?"*

### Selección de Motor de IA (Arriba a la derecha)
Puedes elegir el "Cerebro" que procesará tus datos:
- ⚡ **Gemini 2.5 Flash:** Rápido y excelente para generar código y gráficos precisos.
- 🟣 **Mistral Large:** Ideal para redacciones estratégicas complejas.
- 🌌 **Cerebro Dual (Híbrido):** Combina la potencia de Gemini para analizar y extraer datos, con Mistral para refinar las conclusiones estratégicas.

### Detective de Datos (Alertas de Anomalías)
Mientras trabajas, la IA está auditando silenciosamente tus datos. Si detecta valores atípicos (outliers) graves, el mensaje aparecerá resaltado con un **borde naranja y un ícono de alerta (⚠️)**. Lee estas advertencias con atención, ya que pueden indicar errores en los datos o eventos críticos de negocio.

---

## 4️⃣ Herramientas Automáticas de 1-Clic

En la parte superior de la pantalla del Chat, verás botones rápidos que ejecutan acciones complejas de forma automática:

- ✨ **Magic Clean (Limpieza con IA):** 
  ¿Tus datos tienen nulos, formatos incorrectos o duplicados? Haz clic aquí y la IA limpiará el dataset automáticamente, mostrándote un resumen de lo que arregló y la nueva cantidad de filas/columnas.
  
- 🎨 **Auto Dash (Dashboard Automático):** 
  Si no sabes por dónde empezar, haz clic aquí. La IA analizará la estructura de tu tabla y generará instantáneamente las métricas clave y los gráficos más relevantes de forma automática.

---

## 5️⃣ Gestión de Gráficos y Reportes

Cuando la IA te devuelve un gráfico interactivo, tienes varias opciones al pasar el ratón sobre la visualización:

1. 📌 **Anclar al Panel (Pin):** Haz clic en el ícono del pin para guardar ese gráfico específico en tu **Panel (Dashboard)**.
2. ⬇️ **Descargar PNG:** Guarda la imagen del gráfico en tu computadora para usarla en tus propias presentaciones.

### Generación de Reportes Completos
En la parte superior del chat tienes opciones para llevarte el análisis:
- **Generar Reporte Pro:** Abre un constructor de reportes donde puedes compilar toda la conversación en un documento avanzado (PDF o presentación PPTX).
- **PDF Simple:** Descarga rápidamente la conversación actual en formato PDF.

---

## 6️⃣ Consejos de Oro para Mejores Resultados

1. **Contexto claro:** Al hacer una pregunta, sé específico. Ej. *"Calcula el total de ventas agrupado por región, pero solo para el año 2025"*.
2. **Aprovecha las sugerencias:** Si no estás seguro de qué preguntar, haz clic en el botón de **"Sugerir análisis estratégico"** (o mira las sugerencias iniciales) para que la IA te proponga preguntas basadas en tus columnas reales.
3. **Revisa las llaves API:** Si experimentas errores de conexión, verifica en **Configuración** que tus API Keys de Gemini y/o Mistral estén correctamente ingresadas y validadas (aparecerán en verde).

¡Disfruta tomando decisiones más inteligentes con **Vektra BI**!
