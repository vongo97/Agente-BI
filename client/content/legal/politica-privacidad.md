# Política de Privacidad y Protección de Datos Personales — Vektra BI

**Versión:** 1.0 — **Fecha de vigencia:** 11 de octubre de 2026
**Responsable del Tratamiento:** [TU NOMBRE O EL PROYECTO "Vektra BI"]
**Email de contacto para derechos de datos:** [EMAIL DE CONTACTO]
**Sitio/aplicación:** https://agbi.duckdns.org y https://agente-bi.vercel.app

---

## 1. Responsable del Tratamiento

Vektra BI ("la Aplicación", "nosotros") es operada por [TU NOMBRE], persona natural, quien actúa como **Responsable del Tratamiento** de los datos personales conforme a la **Ley 1581 de 2012** (Habeas Data, Colombia), su Decreto Reglamentario 1377 de 2013, y, para usuarios en el Espacio Económico Europeo, el **Reglamento General de Protección de Datos (GDPR - UE 2016/679)**.

## 2. Datos personales que recolectamos

Recolectamos únicamente los datos mínimos necesarios para operar el servicio:

| Categoría | Datos | Finalidad | Base legal |
|---|---|---|---|
| **Cuenta** | Email y nombre (vía Google OAuth) | Autenticación, identificación de tu espacio de trabajo | Ejecución del contrato |
| **Claves API** | Tus claves de OpenAI/Gemini/Mistral/Groq | Ejecutar análisis con el proveedor de IA que tú elijas | Consentimiento |
| **Archivos de datos** | CSV, Excel, SQL que subes voluntariamente | Ejecutar análisis y visualizaciones que tú solicitas | Ejecución del contrato |
| **Contenido de interacción** | Historial de chats/consultas que realices | Historial en tu panel, continuidad de conversaciones | Interés legítimo |
| **Conexiones externas** | Cadena de conexión SQL a bases de datos tuyas (cifrada) | Conectividad a tu base de datos externa | Consentimiento |
| **Datos técnicos** | Dirección IP, logs de uso para seguridad y diagnóstico | Seguridad, prevención de fraude/abuso | Interés legítimo |

**No** recolectamos datos de categorías especiales (salud, biometría, origen racial, opiniones políticas, etc.). Te pedimos **no subir** archivos que contengan este tipo de datos.

## 3. Finalidades del tratamiento

Usamos tus datos exclusivamente para:

1. Proveer el servicio de análisis de datos con IA que tú activas
2. Autenticación y gestión de tu cuenta
3. Seguridad (prevención de abuso, protección frente a ataques)
4. Cumplir obligaciones legales (retenciones mínimas requeridas)
5. Mejora del servicio exclusivamente en forma agregada y anonimizada

**No vendemos, ni alquilamos, ni compartimos tus datos personales con fines publicitarios.** No perfilamos tu comportamiento comercial.

## 4. Terceros encargados (procesadores) y transferencias internacionales

Para operar el servicio delegamos en proveedores con estándares de seguridad reconocidos. Estas transferencias internacionales se amparan en cláusulas contractuales tipo o equivalentes al Decreto 1377 de 2012 y al GDPR:

| Proveedor | Rol | Ubicación de datos | Su política |
|---|---|---|---|
| **Google (OAuth, Gemini)** | Autenticación e IA generativa | EE.UU. / global | [policies.google.com](https://policies.google.com/privacy) |
| **Mistral AI** | IA generativa | Francia (UE) | [mistral.ai/terms](https://mistral.ai/terms) |
| **Groq** | IA generativa | EE.UU. | [groq.com/privacy-policy](https://groq.com/privacy-policy) |
| **Supabase** | Base de datos, almacenamiento | EE.UU. / opción UE | [supabase.com/privacy](https://supabase.com/privacy) |
| **Render** | Hospedaje del backend (API) | EE.UU. | [render.com/privacy](https://render.com/privacy) |
| **Vercel** | Hospedaje del frontend | Global | [vercel.com/legal/privacy-policy](https://vercel.com/legal/privacy-policy) |

**Importante sobre IA:** los datos que incluyas en tus consultas se envían al proveedor de IA que tú seleccionaste (Gemini, Mistral o Groq) para generar la respuesta. Esos proveedores procesan los datos conforme a sus propias políticas. **No incluyas en las consultas datos personales especialmente sensibles ni información confidencial empresarial crítica.**

## 5. Conservación y eliminación

- **Claves API:** las almacenamos cifradas (AES-256 con clave maestra del servidor). Eliminadas inmediatamente cuando las borras de tu configuración o eliminas tu cuenta.
- **Archivos (CSV/Excel/resultados):** cifrados en reposo. Eliminados cuando borras la fuente o tu cuenta.
- **Historial de chats:** conservado hazta que lo borres o elimines tu cuenta.
- **Logs técnicos:** máximo 90 días en rotación.

## 6. Tus derechos (Colombia - Ley 1581 y GDPR)

Tienes derecho a: conocer, consultar, acceder, rectificar y suprimir tus datos; revocar el consentimiento; oponerte; portar tus datos; y presentar quejas ante la **Superintendencia de Industria y Comercio (SIC)** en Colombia o ante tu autoridad de protección de datos europea si aplica.

**Para ejercerlos:** escribe a **[EMAIL DE CONTACTO]** con el asunto "Derechos de datos personales" y te responderemos dentro de **15 días hábiles** (máximo legal colombiano).

## 7. Seguridad

- Cifrado en tránsito (TLS/HTTPS) y en reposo (AES-256 para claves y archivos)
- Autenticación por tokens firmados (JWT con secreto robusto)
- CORS restrictivo por dominio, rate limiting anti-abuso, sandbox aislado para código generado
- Acceso a claves solo descifrado en memoria de ejecución, nunca en logs

## 8. Menores de edad

El servicio no está dirigido a menores de 14 años. Si identificamos datos de un menor, los eliminaremos inmediatamente.

## 9. Cambios en la política

Notificaremos cambios sustanciales por email con 15 días de anticipación. La versión vigente siempre estará disponible en `/legal/privacidad` de la Aplicación.

## 10. Contacto

**Responsable:** [TU NOMBRE] — **Email:** [EMAIL DE CONTACTO]
En Colombia puedes escalar ante la **SIC** (www.sic.gov.co).

---

*Documento informativo. Para casos regulatorios complejos, consulta con un asesor legal.*
