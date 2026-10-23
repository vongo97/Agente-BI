# Manual de verificación — Ajustes en producción (2026-10-23)

**Entorno:** `https://agente-bi-client-5nx4.onrender.com` (backend: `agente-bi-server-7nav-zifr.onrender.com`)
**Archivo de prueba:** `superstore_2019_2022.csv`
**Cifras de referencia (auditoría manual previa):** $2.30M ventas · $286.4K profit · 12.5% margen · umbral descuento 30% · tramo ≥30%: -$135.4K · 9,994 líneas · 5,009 órdenes.

> Antes de empezar: recarga forzada **Ctrl+Shift+R** y deja abierto F12 (pestañas **Console** y **Network**).
> Si algo falla, captura: screenshot + F12 → Network → clic en la petición roja → pestaña **Response** (cuerpo del error).

---

## Ruta rápida (10 min) — lo crítico

| # | Prueba | Esperado |
|---|---|---|
| 1 | Subir `superstore_2019_2022.csv` | Mensaje "Archivo … añadido con éxito" · HTTP 200 · fuente visible en la lista |
| 2 | Tras subir, esperar ~5 s | Tarjetas de auditoría verificada aparecen **una sola vez** (auto-auditoría al subir) |
| 3 | Pregunta general: *"Resume las ventas por región y año"* | Respuesta del LLM + sección "**Hechos verificados (pandas, sin LLM):**" (hasta 5 cifras) · sin 500 |
| 4 | Botón **Auditoría** | Tarjetas con cifras coincidentes con las de referencia · figura de paneles · badge verificado |
| 5 | Cambiar a otro chat y volver al de auditoría | Las tarjetas **NO** vuelven a aparecer al reabrir; el texto del análisis sí se conserva |

Si estos 5 pasan, lo crítico está verificado. El resto es la pasada completa.

---

## 1. Subida de archivos — P-57 (CRÍTICO)

**Qué se arregló:** `/upload` devolvía 500 (bloque de persistencia borrado) y los mensajes llegaban con caracteres corruptos (`Ã³`, `Ã±`).

| # | Pasos | Esperado |
|---|---|---|
| 1.1 | Subir `superstore_2019_2022.csv` | 200 · mensaje "**añadido con éxito**" con acentos correctos (sin `Ã©`, `Ã³`) |
| 1.2 | F12 → Network → `upload` | Estado **200**; en Response: `id`, `columns`, `rows: 9994`, `persisted: true` |
| 1.3 | Lista de fuentes de datos | El archivo aparece; al analizarlo responde con sus columnas |
| 1.4 | Subir un `.txt` | 400 "Extensión de archivo no permitida…" |
| 1.5 | Subir un archivo > 25 MB | 400 "El archivo excede el tamaño máximo…" |
| 1.6 | Subir un CSV vacío o corrupto | 400 con mensaje claro, **no** 500 |
| 1.7 | (Solo si aplica) Subir cuando Supabase esté caído | 200 con `persisted: false` — el archivo sigue usable en la sesión |

**Nota de seguridad conocida (P-11):** mientras tanto, la copia local del archivo se escribe **sin cifrado** (revertido). La sesión sí viaja cifrada (Fernet). Pendiente re-implementar cifrado en reposo con tests. No es fallo de esta pasada.

---

## 2. Análisis general `/analyze` — P-58 + P-54 (CRÍTICO)

**Qué se arregló:** cualquier pregunta normal terminaba en 500 (`source_name` sin definir). Además, ahora el flujo general adjunta hechos verificados.

| # | Pasos | Esperado |
|---|---|---|
| 2.1 | Pregunta normal: *"¿Cuál es la tendencia de ventas por año?"* | 200 · narrativa del LLM completa · **sin** "Error interno del servidor al procesar el análisis" |
| 2.2 | Revisar el final de la respuesta | Bloque "**Hechos verificados (pandas, sin LLM):**" con hasta 5 cifras con título |
| 2.3 | Pregunta sobre el mismo chat, fuente seleccionada | Las cifras corresponden a la fuente activa, no a otro chat (aislamiento P-34) |
| 2.4 | Dataset sin columnas auditables (p. ej. solo texto) | El análisis responde igual, solo que **sin** bloque de hechos verificados (degradación limpia) |

---

## 3. Auditoría verificada — P-54

| # | Pasos | Esperado |
|---|---|---|
| 3.1 | Botón **Auditoría** (o "audita márgenes y descuentos") | Tarjetas con: $2.30M ventas, $286.4K profit, 12.5% margen, umbral 30%, -$135.4K tramo ≥30% |
| 3.2 | Revisar cada tarjeta | Cada cifra tiene **título + definición** ("cómo se calculó") |
| 3.3 | Badge de modo de narración | Visible y coherente ("sin LLM" o "narración IA con cifras inyectadas") |
| 3.4 | Figura generada | Se muestra el gráfico de paneles junto a las tarjetas |

---

## 4. Tarjetas solo una vez — historial (`d8a897a5`)

**Qué se arregló:** al reabrir una conversación vieja, las tarjetas de auditoría se volvían a renderizar en cada mensaje.

| # | Pasos | Esperado |
|---|---|---|
| 4.1 | Abrir el chat donde salió la auto-auditoría tras subir | Tarjetas visibles **solo en vivo** (en el momento de la subida) |
| 4.2 | Salir a otro chat y regresar desde la barra lateral | Las tarjetas **no** reaparecen; el texto del análisis y la figura del historial se conservan |
| 4.3 | Recargar la página (F5) con el chat abierto | Mismo comportamiento: texto sí, tarjetas no re-renderizadas |

---

## 5. Ajustes (proveedores y modelos) — P-14, P-26, P-41

| # | Pasos | Esperado |
|---|---|---|
| 5.1 | Abrir Ajustes | El selector de modelo muestra los **modelos reales** del proveedor con su etiqueta (no un nombre falso) |
| 5.2 | Cambiar modelo/proveedor y **Guardar** | Toast de éxito |
| 5.3 | Recargar la página (F5) | Lo guardado **persiste** (antes se perdía al recargar) |
| 5.4 | Ejecutar un análisis con un proveedor sin API key | 400 con mensaje **accionable** ("falta la clave de X"), nunca un stack trace ni detalles internos |

## 6. Simulación — P-12, P-38, P-39

| # | Pasos | Esperado |
|---|---|---|
| 6.1 | Sandbox de simulación con error (p. ej. sin clave / inputs inválidos) | Mensaje genérico y accionable; **sin** `str(e)` ni rutas internas en el texto |
| 6.2 | Ontología/agentes con layout inválido | Rechazado con aviso de validación (antes se aceptaba cualquier estructura) |
| 6.3 | Estados de tareas | "Pendiente" en español (antes "pending") |

## 7. Dashboard — P-37, P-13

| # | Pasos | Esperado |
|---|---|---|
| 7.1 | Generar dashboard automático sobre el superstore | KPIs **calculados con pandas** sobre los datos reales (ventas, profit, margen coherentes con §3) y gráfico plotly renderizado |
| 7.2 | Comparar cifras del dashboard con las tarjetas de auditoría | Mismos totales ($2.30M / $286.4K / 12.5%); si difieren, reportar |

## 8. UI/UX — P-40

| # | Pasos | Esperado |
|---|---|---|
| 8.1 | Inspeccionar textos pequeños (etiquetas, badges, KPIs) | Ningún texto < 12px (antes había de 8px ilegibles) |
| 8.2 | Reducir la ventana a ~768 px y luego a móvil (devtools) | Sidebars colapsan a su ancho responsive (`w-72→md:w-80`, `w-56→md:w-60`) sin tapar contenido |

## 9. Seguridad y red — P-08, P-15, P-46, P-07

| # | Pasos | Esperado |
|---|---|---|
| 9.1 | F12 → Network → `data-sources` → Response | **Sin** campo `url` interna (solo metadatos públicos) |
| 9.2 | Intentar login con una cuenta de Google NO autorizada | Rechazado por allowlist del cliente |
| 9.3 | Navegación general | Ningún error CSP en consola; la página **no** se queda en "Cargando workspace…" (P-07 quedó permissiva a propósito hasta implementar nonces) |
| 9.4 | (Opcional) Con el token expirado: cualquier acción | Redirección automática al login (401/403 → signOut), no quedarse colgado |
| 9.5 | (Opcional) Cortar la red durante una petición | Aborta a los ~30 s con 2 reintentos previos; no se congela la UI |

## 10. Sesiones y cuotas — P-34, P-35

| # | Pasos | Esperado |
|---|---|---|
| 10.1 | Chat A con archivo X; crear chat B y preguntar | B no mezcla los datos de A salvo que selecciones la fuente |
| 10.2 | Subir ~3 archivos y alternar preguntas entre chats | Cada chat responde según su fuente/session, sin "sangrado" de datos entre chats |

*P-35 (límites de memoria del store: 100 entradas / TTL 1 h / LRU) está cubierto por tests unitarios; no tiene prueba manual práctica.*

---

## Cómo reportar un fallo

Para cada fallo manda:
1. **Screenshot** de la pantalla con el error.
2. F12 → **Network** → clic en la petición en rojo → pestaña **Response** (cuerpo JSON del error).
3. Pasos exactos para reproducirlo y en qué chat/fuente.
4. Hora aproximada (para cruzar con logs del deploy).

## Cobertura conocida / pendiente

- **P-07 (CSP):** permissiva a propósito; endurecer con nonces es tarea aparte.
- **P-11 (cifrado en reposo):** revertido; re-implementar con tests **después** de confirmar la subida estable.
- **Multi-archivo por chat:** limitado por `Chat.data_source_id` (FK única); restaurarlo requiere tabla `ChatSource`.
- **P-54:** marcado PARCIAL en el registro hasta verificar en producción los puntos 2 y 3 de este manual.
