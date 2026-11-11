---
name: deployment-and-ci-cd-pipelines
description: Guía para configurar pipelines de integración y despliegue continuos (CI/CD) para aplicaciones web y móviles. Úsalo al configurar flujos de compilación, empaquetado, firma de artefactos y entrega automática.
---

# Deployment & CI/CD Pipelines for Web & Mobile

Define las mejores prácticas para automatizar la integración, pruebas y despliegue de las aplicaciones clientes y servidores en producción.

---

## 1. Automatización de Compilación y Calidad (CI)

* **Pipeline de Web (NPM/Yarn):**
  * Configura flujos que ejecuten en orden:
    1. Instalación de dependencias: `npm ci`
    2. Linter / Análisis estático: `npm run lint`
    3. Pruebas unitarias: `npm run test`
    4. Compilación de producción: `npm run build`
* **Pipeline de Android (Gradle):**
  * Asegura el análisis de calidad con:
    ```bash
    ./gradlew lintDebug
    ./gradlew testDebugUnitTest
    ./gradlew assembleDebug
    ```

---

## 2. Firma y Distribución de Apps Móviles (CD)

* **Firma de Releases:** NUNCA subas llaves de firma `.jks` o credenciales a repositorios públicos de Git. Almacénalas codificadas en Base64 en las variables secretas de tu entorno CI/CD y decodifícalas durante la compilación.
* **Fastlane:** Automatiza el flujo de subida de compilaciones de producción (.aab) o beta (.apk) a Google Play Console mediante Fastlane:
  ```ruby
  lane :beta do
    gradle(task: "clean assembleRelease")
    upload_to_play_store(track: "internal")
  end
  ```

---

## 3. Despliegue de Aplicaciones Web

* **Entornos Contenerizados:** Empaqueta las aplicaciones web en imágenes Docker optimizadas multi-etapa (multi-stage builds) para reducir su tamaño y acelerar su despliegue en entornos Cloud.
