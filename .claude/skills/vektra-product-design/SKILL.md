---
name: vektra-product-design
description: Aplica los estándares de diseño de producto y sistema visual de Vektra BI. Úsalo al diseñar o implementar componentes frontend, layouts de dashboard, chats de analista IA, simulaciones, gráficos interactivos, tablas, configuraciones, estados de carga y animaciones.
---

# Vektra Product Design & Advanced Visual System

Diseña Vektra como un espacio de trabajo analítico de inteligencia de negocios (BI) serio y premium con un asistente de IA, no como una landing page de marketing ni un chatbot genérico.

---

## 1. Dirección Visual y Layouts

* **Layouts de Producto de Alta Densidad:** Utiliza estructuras de paneles, barras laterales (`sidebar`), barras de herramientas (`toolbar`), tablas de datos, gráficos limpios y split-views.
* **Diseño Limpio y Minimalista:** Evita héroes gigantescos, degradados estridentes en fondos principales, blobs flotantes o copias de marketing ruidosas.
* **Bordes y Radio:** Mantener un radio de borde consistente de `6-8px` (`rounded-md` o `rounded-lg`).
* **Profundidad y Elevación:** Utiliza sombras muy sutiles (`shadow-sm`) y bordes suaves de `1px` (`border-bi-border`) para separar zonas lógicas. Deja que el espaciado y la jerarquía realicen la mayor parte del trabajo.
* **Consistencia de Ilustraciones:** Las ilustraciones SVG de soporte para estados vacíos o errores deben mantener un estilo minimalista, de líneas finas, utilizando exclusivamente colores del tema.

---

## 2. Paleta de Colores y Temas (globals.css)

El sistema soporta modo oscuro por defecto y modo claro mediante la clase `[data-theme="light"]`.

* **Base:** Fondo lienzo (`--bi-canvas`), paneles secundarios (`--bi-surface-0`), tarjetas y elementos dinámicos (`--bi-surface-1`), estados hover (`--bi-surface-2`).
* **Primario (Teal / Restrained Blue-Green):** `#2dd4bf` (Dark) / `#0d9488` (Light). Se usa para acciones principales, badges de éxito y focos tácticos.
* **Acentos (Electric Blue):** `#60a5fa` (Dark) / `#2563eb` (Light). Utilizado para enlaces, gráficos y elementos de interacción de datos.
* **Módulo Simulación (Purple):** `#a855f7` (Dark) / `#8b5cf6` (Light). Utilizado para denotar flujos del simulador y estados de debate.
* **Semántica:** Éxito (Verde `--bi-green`), Alerta (Ámbar `--bi-amber`), Peligro/Error (Rojo `--bi-red`).
* **Mitigación de Parpadeo de Temas (FOUC):** Asegurar que Next.js inyecte un script inline de tema en el `<head>` antes de montar la UI del cliente, evitando parpadeos de luz blanca repentinos al cargar en modo oscuro.

---

## 3. Efectos Visuales Avanzados (Estética Premium)

Para que el sistema se sienta premium, utiliza los siguientes efectos dinámicos en Tailwind v4 o CSS:

* **Glassmorphism Inteligente (Frosted Glass):** 
  * Aplica un fondo translúcido y desenfoque de fondo en elementos flotantes, overlays móviles y menús contextuales:
    ```css
    backdrop-blur-md bg-bi-s0/80 border border-white/10
    ```
* **Resplandor de Actividad (Activity Glow):**
  * Al procesar tareas, debatir o cuando la IA está analizando, añade un brillo difuso perimetral sutil para enfocar la atención del usuario:
    ```css
    box-shadow: 0 0 12px 1px rgba(45, 212, 191, 0.15); /* Usar variable de color correspondiente */
    ```
* **Efecto Shimmer (Luz en Barrido):**
  * En los estados de carga de tablas o gráficos, utiliza esqueletos de carga animados con un barrido de luz lateral en lugar de spinners molestos.
* **Speaker Highlight (Foco en Simulación):**
  * En el visor de debate de agentes, resalta dinámicamente al agente que tiene el turno de palabra usando un borde de acento pulsante y un fondo ligeramente más claro.
* **Arrastre en Grid (Drag & Drop UI):**
  * Al mover widgets en el dashboard, la tarjeta seleccionada debe volverse translúcida (`opacity-60`) con bordes discontinuos, y la celda destino (`drop-zone`) debe mostrar un resplandor teal/azul suave en sus bordes para indicar la ubicación final.

---

## 4. Sincronización de Gráficos (Plotly Theme Engine)

Los gráficos interactivos generados por el backend (Plotly/SVG) deben alinearse exactamente al tema y colores de Vektra:

* **Fondo de Gráfico Transparente:** Forzar `paper_bgcolor: 'rgba(0,0,0,0)'` y `plot_bgcolor: 'rgba(0,0,0,0)'`.
* **Colores de Grid:** Utilizar el color de borde de Vektra (`var(--bi-border)`) para las líneas divisorias de los ejes X/Y.
* **Tipografía del Gráfico:** Usar la fuente del sistema: `family: 'Inter, sans-serif'`.
* **Colores de Texto:** Sincronizar el color de títulos y etiquetas con `--bi-text-2` (`#9da3af` en dark / `#475569` en light).
* **Paleta de Datos Coherente:** Mapear los colores de barras, líneas y sectores usando los acentos de Vektra (`--bi-teal`, `--bi-blue`, `--bi-green`, `--bi-amber`, `--bi-red`).

---

## 5. Diseño de Información Tabular y Datos

* **Alineación de Datos:** 
  * Alinear siempre a la **derecha** los datos numéricos, financieros, porcentajes y fechas.
  * Alinear a la **izquierda** textos, nombres, IDs de transacciones y etiquetas.
  * Alinear las cabeceras de las columnas exactamente con la orientación de sus datos.
* **Tipografía de Datos:** Utilizar fuentes monoespaciadas (`font-mono` / `var(--font-mono)`) para cifras numéricas en tablas para que los dígitos se alineen perfectamente entre filas, facilitando la comparación visual rápida.
* **Bordes y Scroll:** Las tablas extensas deben tener cabeceras fijas (`sticky top-0`) y un scroll perimetral sutil (`custom-scrollbar`).

---

## 6. Feedback Visual e Interacciones de Estado

* **Prohibición de `alert()` Nativo:** Bajo ninguna circunstancia uses el comando nativo `alert()` de Javascript. Rompe el flujo y el diseño. Usa notificaciones contextuales elegantes (Toasts), banners de alerta integrados o ventanas de confirmación modales basadas en componentes.
* **Loaders de Acción Directa y Barras Segmentadas (Steppers):**
  * Cuando un botón o formulario esté procesando datos, cambia el estado del elemento para mostrar un mini-spinner inline.
  * Para operaciones asíncronas de larga duración (ej: entrenar un simulador), implementa un indicador visual de progreso paso a paso (Stepper) para informar al usuario de la etapa actual (Ej: "Paso 1: Extrayendo ➔ Paso 2: Ejecutando").
* **Estados Vacíos Contextuales (Empty States):**
  * Si un panel, gráfico o tabla no cuenta con datos, muestra un estado vacío con:
    1. Un icono explicativo sutil.
    2. Un mensaje directo de la causa (ej. "No hay fuentes de datos activas").
    3. Un botón de acción inmediata (ej. "Subir archivo CSV").

---

## 7. Accesibilidad, Legibilidad y Fatiga Visual

* **Ancho de Lectura (Fatiga Visual):** Restringir el ancho máximo de los textos de análisis generados por la IA a `max-w-prose` (aprox. 70 caracteres por línea) con un alto de línea más amplio (`leading-relaxed`), evitando líneas infinitas en pantallas ultra-panorámicas.
* **Tooltips en Portales React:** Todos los globos informativos y hover cards deben ser inyectados usando Portales (`React Portals` / `@radix-ui/react-tooltip`) para evitar que queden recortados por contenedores con `overflow-hidden`.
* **Estados de Foco Activo (`:focus-visible`):** No ocultes el anillo de enfoque. Asegura que los elementos interactivos tengan un contorno claro (`ring-2 ring-bi-teal ring-offset-2`) cuando se navega mediante el teclado.
* **Navegación por Teclado:** Asegúrate de que todos los menús desplegables, pestañas y modales puedan abrirse, cerrarse y navegarse con `Tab`, `Enter` y `Escape`.
* **Contraste de Texto:** Mantener relaciones de contraste que cumplan con la norma WCAG AA para asegurar la legibilidad del texto en cualquier tema.

---

## 8. Verificación Visual de Cambios

Antes de dar por completado un cambio en la interfaz:
1. Inspecciona la vista tanto en escritorio como en dimensiones móviles (breakpoints responsivos).
2. Comprueba que el modo claro y modo oscuro rendericen correctamente los bordes y textos sin contrastes ilegibles.
3. Asegúrate de que las animaciones de `framer-motion` utilicen transiciones rápidas (`duration: 0.2` o `0.3` con curvas `easeOut` o `spring`) para evitar la sensación de lag o lentitud.
4. Valida que no queden remanentes de alertas nativas o comportamientos bloqueantes.
