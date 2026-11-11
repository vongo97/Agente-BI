---
name: android-mobile-hardening
description: Directrices de seguridad y endurecimiento (hardening) para aplicaciones Android. Úsalo al configurar el manifiesto, el almacenamiento local seguro, las firmas de red y la ofuscación en producción.
---

# Android Mobile Hardening & Security Standards

Sigue estas directivas de seguridad para mitigar riesgos de ingeniería inversa, filtración de datos y ataques sobre la aplicación Android.

---

## 1. Almacenamiento Local Seguro

* **EncryptedSharedPreferences:** NUNCA guardes tokens de autenticación o datos sensibles del usuario en texto plano. Usa `EncryptedSharedPreferences` de la librería AndroidX Security:
  ```kotlin
  val masterKey = MasterKey.Builder(context)
      .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
      .build()

  val sharedPreferences = EncryptedSharedPreferences.create(
      context,
      "secure_prefs",
      masterKey,
      EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
      EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
  )
  ```
* **Cifrado de Base de Datos (Room):** Si la aplicación persiste bases de datos estructuradas con datos sensibles, implementa cifrado transparente a nivel de base de datos utilizando **SQLCipher**.

---

## 2. Hardening en AndroidManifest.xml

* **exported=false:** Asegúrate de que las actividades, servicios y receptores de difusión (`BroadcastReceivers`) que no necesiten ser llamados por otras aplicaciones externas tengan explícitamente `android:exported="false"` para prevenir inyecciones de intenciones no autorizadas.
* **Network Security Config:** Configura `networkSecurityConfig` para obligar al uso de HTTPS e impedir conexiones HTTP en texto plano:
  ```xml
  <network-security-config>
      <base-config cleartextTrafficPermitted="false" />
  </network-security-config>
  ```
* **Permisos Mínimos:** Solicita únicamente los permisos estrictamente necesarios en el manifiesto (`AndroidManifest.xml`). Solicita permisos peligrosos (cámara, ubicación, etc.) en tiempo de ejecución.

---

## 3. Ofuscación de Código y Compilación Segura

* **R8 / ProGuard:** Habilita la reducción de recursos y la ofuscación en el archivo `build.gradle` de producción:
  ```groovy
  buildTypes {
      release {
          minifyEnabled true
          shrinkResources true
          proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
      }
  }
  ```
* **Control de Logs:** Deshabilita los logs de depuración en producción. Evita el uso directo de `Log.d` o `Log.v` en producción; en su lugar, usa librerías como Timber que permiten deshabilitar el registro en release.
