---
name: android-material3-compose
description: Guía de diseño de interfaces nativas en Android usando Jetpack Compose y Material Design 3. Úsalo al desarrollar pantallas Compose, temas dinámicos, navegación y estados reactivos en la UI móvil.
---

# Android Material Design 3 & Jetpack Compose Standards

Garantiza que la UI y UX de cualquier aplicación móvil Android siga los patrones de Material Design 3, ofreciendo una experiencia responsiva, fluida y nativa.

---

## 1. Temas y Sistema de Color Dinámico

* **Material Theme:** Toda la aplicación debe estar envuelta en un componente `MaterialTheme` personalizado. Define colores primarios, secundarios, terciarios y superficies tanto para el tema claro (`lightColorScheme`) como oscuro (`darkColorScheme`).
* **Soporte de Dynamic Color (Android 12+):**
  * Si el dispositivo lo soporta, utiliza el color dinámico del sistema para adaptar la app al fondo de pantalla del usuario:
    ```kotlin
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES = Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }
    ```

---

## 2. Layouts y Estructuras Comunes (Scaffolding)

* **Scaffold:** Utiliza siempre el componente `Scaffold` para estructurar pantallas principales. Proporciona slots integrados para `topBar` (`TopAppBar`), `bottomBar` (`NavigationBar`), y `floatingActionButton` (`FloatingActionButton`).
* **Estructura de Contenido Adaptativo:**
  * Usa `LazyColumn` para listas verticales y `LazyVerticalGrid` para colecciones de datos, asegurando que se libere memoria de los ítems fuera de pantalla.
  * Para pantallas con scroll simple, envuelve el `Column` con un modificador `.verticalScroll(rememberScrollState())`.

---

## 3. Estados Reactivos en la UI (State Hoisting)

* **State Hoisting (Elevación de Estado):** Separa la lógica de presentación de la UI. Los elementos composables de UI deben recibir estados por parámetro y emitir eventos mediante callbacks (lambdas):
  ```kotlin
  @Composable
  fun UserProfile(
      uiState: UserUiState,
      onEditClick: () -> Unit
  ) { ... }
  ```
* **rememberSaveable:** Usa `rememberSaveable` en lugar de un simple `remember` para preservar el estado de la UI durante la recreación de actividades (por ejemplo, al rotar el dispositivo).

---

## 4. Transiciones y Animaciones en Compose

* **AnimatedVisibility:** Usa `AnimatedVisibility` para mostrar u ocultar componentes dinámicamente en pantalla de forma suave.
* **Transiciones de Navegación:** Configura transiciones personalizadas en el gráfico de navegación (`NavHost`) para deslizar o desvanecer vistas:
  ```kotlin
  composable(
      route = "home",
      enterTransition = { slideInHorizontally(initialOffsetX = { 1000 }) },
      exitTransition = { slideOutHorizontally(targetOffsetX = { -1000 }) }
  ) { ... }
  ```
