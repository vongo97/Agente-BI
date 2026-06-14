---
name: vektra-frontend-state-management
description: Guía de arquitectura de estado y refactorización para el frontend (React/Next.js/Zustand) y clientes nativos (Android Compose). Úsalo cuando modifiques flujos de estado, componentes UI grandes o persistencia local.
---

# Universal Frontend & Client State Management

Establece las directrices para la refactorización, persistencia y mantenimiento del estado en las capas cliente (Web y Android).

---

## 1. Descomposición de Componentes Monolíticos (Web)

1. **Aislamiento de Componentes de Presentación:**
   - Evita que archivos como `Chat.tsx` o vistas complejas superen las 30KB. Deben descomponerse en subcomponentes aislados (ej. `MessageList.tsx`, `InputArea.tsx`, `ChartContainer.tsx`).
2. **Propagación del Estado y Props:**
   - Mantén el estado de sincronización (tokens de autenticación, llaves API activas, datos en caché) en stores globales (Zustand) o contextos raíz, minimizando el acoplamiento directo de props en cascada.

---

## 2. Directrices para Gráficos Interactivos (Plotly.js + React)

1. **Ciclo de Vida de Gráficos:**
   - Usar contenedores con alturas y anchos definidos en CSS responsivo para evitar saltos bruscos en la UI (Layout Shifts).
   - Asegurarse de destruir o limpiar las referencias de los contenedores de Plotly al desmontar componentes de chat para evitar fugas de memoria en el navegador.
2. **Gestión de Gráficos Vacíos:**
   - Proveer un estado visual explícito de "Cargando gráfico..." o "Gráfico no disponible" cuando los datos del backend estén incompletos o en proceso de descarga.

---

## 3. Gestión de Estado Móvil Reactivo (Android Jetpack Compose)

1. **ViewModels como Retentores de Estado:**
   - Toda la lógica de negocio y llamadas de datos debe vivir en el `ViewModel`. La UI de Compose solo observa el estado expuesto a través de `StateFlow` o `LiveData`.
2. **Sincronización y Caché Offline:**
   - Utiliza una estrategia de "Offline-First". El repositorio primero guarda los datos de la red en la base de datos local (Room) y luego emite los datos actualizados desde la base de datos hacia la UI. Esto asegura que la app funcione sin conexión.
3. **Flujo de Eventos Único (UDF):**
   - El estado fluye hacia abajo (del ViewModel a Compose) y los eventos fluyen hacia arriba (de Compose al ViewModel). Esto facilita las pruebas unitarias de la UI.
