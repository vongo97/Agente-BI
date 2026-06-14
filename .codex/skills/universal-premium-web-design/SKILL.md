---
name: universal-premium-web-design
description: Define los estándares de diseño de interfaces web modernas y de alta fidelidad. Úsalo al implementar componentes web, estructuras de diseño responsivas (layouts), variables de color, animaciones y flujos visuales premium.
---

# Universal Premium Web Design Standards

Aplica estas directrices visuales para asegurar que cualquier desarrollo web sea estéticamente espectacular, moderno y con un rendimiento visual de primer nivel.

---

## 1. Diseño Visual y Layouts Web

* **Layouts de Alta Densidad Analítica:** Prioriza el uso de paneles deslizantes, barras laterales flotantes o semi-acopladas, y cuadrículas adaptativas. Evita el espacio vacío desperdiciado y las secciones gigantescas estilo "landing page" a menos que sea necesario.
* **Consistencia de Bordes:** Los componentes deben usar un radio de borde constante de `6px` a `8px` (`rounded-md` o `rounded-lg`). Los bordes deben ser extremadamente sutiles (`1px border border-white/5` en modo oscuro o `border-black/5` en modo claro).
* **Elevación Sutil:** Utiliza sombras suaves y compuestas en lugar de sombras negras opacas. Ejemplo en CSS:
  ```css
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  ```

---

## 2. Tipografía y Jerarquía Visual

* **Tipografía Limpia:** Usa fuentes geométricas modernas (e.g., *Inter*, *Outfit* o *Roboto*) y evita fuentes serif en interfaces de usuario funcionales.
* **Estructura Semántica de Encabezados:** Respeta la jerarquía HTML (`h1`, `h2`, `h3`). Solo debe haber un `h1` por vista o página.
* **Alineación de Datos en Tablas:**
  * Números y datos monetarios: siempre alineados a la **derecha** con fuentes monoespaciadas (`font-mono`) para garantizar alineación decimal exacta.
  * Texto, nombres e IDs: siempre alineados a la **izquierda**.

---

## 3. Efectos Visuales Premium (Wow Factor)

* **Glassmorphism (Frosted Glass):** 
  * Usa fondos translúcidos y desenfoque difuso en barras de navegación, menús desplegables y modales:
    ```css
    background: rgba(255, 255, 255, 0.05); /* En modo oscuro */
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    ```
* **Shimmer Effect (Barrido de Luz):**
  * Para las pantallas de carga, utiliza esqueletos Shimmer (estructuras de esqueleto de carga con animación de barrido de color gradual) en lugar de molestos spinners estáticos.
* **Micro-animaciones de Interacción:**
  * Todas las interacciones de hover, foco y click deben tener transiciones de velocidad rápida (`duration: 0.2s` o `200ms`) con curvas suaves (`ease-out` o `cubic-bezier(0.16, 1, 0.3, 1)`):
    ```css
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    ```

---

## 4. Accesibilidad y Responsividad

* **Diseño Responsive:** Los layouts deben soportar breakpoints estándar (`sm`, `md`, `lg`, `xl`). Ningún componente o panel debe desbordarse horizontalmente en resoluciones móviles.
* **Sin Alertas Nativas:** NUNCA utilices `alert()`, `confirm()` o `prompt()` nativos del navegador. Utiliza Toasts contextuales elegantes para notificaciones cortas y Modales del sistema para confirmaciones críticas.
* **Estados de Foco Activo:** No elimines el esquema del foco por defecto sin proporcionar una alternativa accesible y altamente visible (e.g., bordes de color brillante y anillos con offset).
