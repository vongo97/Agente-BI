# Bitácora de trabajo — Vektra BI

**Fecha:** 7 de noviembre de 2026  
**Proyecto:** Vektra BI / Agente-BI  
**Propósito:** dejar constancia de la auditoría inicial, las oportunidades de mejora, la ruta sugerida y las preguntas abiertas para definir el futuro del producto.

## 1. Alcance de la sesión

El trabajo de hoy tuvo dos partes:

1. Una revisión estática del repositorio y del registro `docs/PROBLEMAS_CONOCIDOS.md` para identificar riesgos de código, mantenimiento y escalabilidad.
2. Una conversación de orientación para explorar hasta dónde podría llegar Vektra, qué problema resolvería y qué decisiones de producto aún faltan.

La revisión fue de solo lectura. No se modificó código, no se ejecutaron pruebas y no se verificó el estado actual de producción. Los cambios que ya existían en el árbol de trabajo se conservaron sin alterarlos.

## 2. Resumen ejecutivo

Vektra nació como una solución para una prueba de empleo y se ha convertido en un proyecto con capacidades de producto: carga de datos, análisis con IA, auditoría de cifras, visualizaciones, reportes y conexiones a distintas fuentes.

La oportunidad que mejor se distingue hoy es ayudar a personas o equipos que trabajan con archivos de datos a entender qué ocurre y qué podrían revisar, con cifras trazables y explicaciones comprensibles. Esto es una **hipótesis de producto**, no una validación de mercado. Todavía falta elegir un usuario inicial, un problema frecuente y una señal concreta de que la solución tiene valor.

La prioridad técnica más urgente que se observó es **P-11**: las cargas siguen escribiéndose sin cifrar y el guard anti zip-bomb agregado en el archivo local no está conectado al flujo de carga. Después conviene endurecer la persistencia y las migraciones, ordenar el registro de problemas y definir una ruta gradual para escalar el estado y los análisis largos.

## 3. Hallazgos técnicos principales

### 3.1 Carga de archivos — P-11

El flujo vigente de `/upload` escribe los bytes del archivo en disco y los envía a la nube sin cifrarlos; la fila `DataSource` se crea con `is_encrypted=False`. En el cambio local de `server/src/routers/data.py` existe `_reject_zip_bomb_early(...)`, pero no se encontró una llamada a esta función en el recorrido de `/upload` antes de `load_file_data_from_bytes(...)`. Por tanto, el control está definido pero no aplicado al flujo activo.

**Implicación:** se mantienen los riesgos ya asociados a P-11: datos originales en claro en almacenamiento y protección temprana contra archivos comprimidos maliciosos pendiente de quedar conectada.

**Siguiente mejora:** cifrar los bytes antes de persistirlos, invocar el guard antes de parsear y definir la limpieza o compensación si falla una etapa intermedia de la carga.

### 3.2 Base de datos y migraciones — P-19 y P-47

`server/src/database.py` define SQLite como valor por defecto y, si falla la creación del motor, cambia a SQLite. `init_db()` también captura errores de inicialización y los registra. Esto puede ocultar una configuración inválida o un esquema incompleto hasta que una operación de usuario falle.

**Siguiente mejora:** hacer que producción falle al arrancar si la base configurada no está disponible o no es válida; organizar los cambios de esquema con migraciones reproducibles y definir cómo se recupera el servicio si una migración falla.

### 3.3 Estado del registro de problemas

El registro ofrece una base valiosa, pero tiene discrepancias entre resumen, secciones históricas y evidencias:

- P-03 aparece cerrado en el resumen y abierto en una sección anterior.
- P-55 aparece cerrado y también parcial en otra sección.
- P-54 se muestra parcial, mientras P-71 documenta como cerrada la narrativa natural con verificación de cifras.
- P-49 conserva el contexto de un bloqueo de subidas sin nube aunque el flujo actual documenta un modo local temporal.
- El resumen reconoce IDs que faltan y recuentos que deben reconciliarse.

**Siguiente mejora:** consolidar los estados vigentes y dejar las explicaciones históricas como historial, claramente separadas de la lista operativa.

### 3.4 Escalabilidad del estado y de las cargas

El estado temporal se almacena en un `data_store` en memoria del proceso. Las sesiones también se serializan con pickle cifrado, y la caché de archivos puede depender del disco local. Aunque haya límites de memoria, un estado local por proceso hace más difícil distribuir el tráfico entre varias instancias y recuperar una sesión en otra.

El nombre de archivo persistente se forma con usuario, tiempo en segundos y nombre saneado. Dos cargas concurrentes del mismo usuario con el mismo nombre pueden generar una ruta coincidente.

**Siguiente mejora:** antes de añadir instancias, definir almacenamiento compartido y claves únicas para fuentes; después, trasladar los análisis largos a trabajos recuperables si las mediciones demuestran que hace falta.

### 3.5 Contratos y funcionamiento del dashboard — P-48

El registro identifica que `/dashboard/filter` puede responder como si hubiera tenido éxito si el nombre de columna no existe, y el camino SQL tiene un TODO para implementar el filtrado.

**Siguiente mejora:** validar filtros de manera explícita y acordar un contrato coherente para los modos de archivo y SQL; no indicar éxito cuando no se aplicó el filtro solicitado.

### 3.6 Verificación operativa

El registro documenta una CI que ejecuta verificaciones de backend y cliente. También deja P-56 pendiente de evidencia de producción durante un análisis largo.

**Siguiente mejora:** capturar tiempos, errores y uso de recursos por petición y por trabajo, con un identificador de correlación y sin registrar datos privados. Esto permitiría priorizar las optimizaciones con medidas reales.

### 3.7 Documentación de proyecto

`EVALUACION_PROYECTO.md` describe versiones y deuda que no coinciden con el estado posterior registrado en `docs/PROBLEMAS_CONOCIDOS.md`.

**Siguiente mejora:** actualizar la evaluación después de reconciliar el registro, y mantener un documento corto de arquitectura y objetivos vigente.

## 4. Ruta sugerida por hitos

| Orden | Hito | Resultado buscado | Opciones para abordarlo |
|---|---|---|---|
| 0 | Línea base confiable | Registro y documentos representan el estado real del proyecto. | Reconciliar los estados/evidencias de P-03, P-11, P-19, P-47, P-49, P-54 y P-55; definir una lista priorizada con responsable y criterio verificable. |
| 1 | Carga segura | Archivos protegidos y validaciones efectivas antes del parseo. | Corrección mínima: cifrar en memoria y llamar al guard temprano. Ampliación: incluir compensación ante fallos y detección de archivos huérfanos. |
| 2 | Persistencia y migraciones | Producción usa la base prevista y los cambios de esquema se aplican de forma controlada. | Endurecer arranque primero; evolucionar gradualmente hacia migraciones Alembic con comprobaciones en CI. |
| 3 | Barreras de regresión | Los riesgos críticos tienen verificaciones que detectan una recaída. | Empezar por auth, propiedad de datos, cifrado, cargas y migraciones; ampliar después a contratos y casos de análisis. |
| 4 | Medición y objetivos | Saber qué carga soportar y dónde están los cuellos de botella. | Definir metas iniciales de concurrencia, tamaño y tiempos; instrumentar las rutas clave sin datos sensibles. |
| 5 | Recuperación y consistencia | Poder recuperar datos y detectar operaciones incompletas. | Definir respaldos y ensayo de restauración; añadir limpieza/reconciliación de fuentes y sesiones inconsistentes. |
| 6 | Escalado gradual | Varios procesos pueden atender usuarios y los análisis largos sobreviven a desconexiones. | Primero almacenamiento compartido para fuentes/sesiones; luego trabajos persistentes y workers si la medición lo justifica. |
| 7 | Contratos y deuda | Comportamientos pendientes son explícitos y los cambios son más pequeños. | Resolver P-48; después dividir módulos grandes y retirar código muerto en cambios acotados. |

**Orden recomendado:** primero seguridad de datos y persistencia; luego pruebas y medición; finalmente escalar infraestructura de forma guiada por evidencia. No empezar por una reescritura ni por multiplicar servicios sin objetivos medibles.

## 5. Apreciación de producto

La visión inicial que se planteó para validar es:

> Vektra podría ser una herramienta de análisis para equipos pequeños que dependen de hojas de cálculo y no tienen un analista disponible. Les permitiría preguntar sobre sus datos y obtener hallazgos comprensibles, cifras trazables y orientación sobre qué revisar o decidir.

La parte diferenciadora potencial no sería solo “chatear con un archivo”. Sería combinar facilidad de uso con cálculos comprobables, explicación de límites y contexto para una decisión real.

Esto aún no prueba que haya un mercado. La decisión importante pendiente es quién sufre el problema con frecuencia, cómo lo resuelve hoy, qué valor recibe de Vektra y quién tendría presupuesto para pagar.

## 6. Preguntas pendientes para definir la meta

El usuario indicó que responderá estas preguntas más adelante. No se tomó ninguna respuesta ni decisión de producto en esta sesión.

### Objetivo personal

1. Si Vektra sale bien, ¿qué te gustaría que fuera para ti en tres años: negocio que dé ingresos, empresa con equipo, producto secundario, oportunidad laboral u otra cosa?
2. ¿Cuánto tiempo puedes dedicarle por semana durante los próximos seis meses?
3. ¿Estás dispuesto a invertir dinero para validarlo? ¿Qué cantidad podrías arriesgar sin afectar tus obligaciones?
4. ¿Qué sería un resultado valioso dentro de 12 meses, aunque el proyecto todavía no sea grande?

### Usuarios y problema

5. ¿Qué persona concreta imaginas usando Vektra primero: dueño de negocio, contador, economista, consultor, analista u otra?
6. ¿Qué decisión le cuesta tomar hoy por no entender sus datos?
7. ¿Cómo resuelve actualmente ese problema y qué pierde cuando no lo resuelve bien?
8. ¿Con qué frecuencia aparece el problema?
9. ¿Alguien ha usado Vektra con datos propios? ¿Qué valor o frustración mostró?

### Primer producto

10. Si Vektra resolviera un solo trabajo al principio, ¿cuál sería?
11. ¿Qué resultado debería recibir el usuario para que sienta que valió la pena?
12. ¿Qué parte de Vektra no quitarías del primer producto?
13. ¿Qué capacidades podrían esperar para simplificar la primera experiencia?

### Confianza y negocio

14. ¿Qué pruebas necesita ver el usuario para confiar en una cifra o recomendación?
15. ¿Qué decisión no debería dejarse en manos de Vektra?
16. Si los datos son ambiguos, ¿Vektra debe preguntar o responder con advertencias?
17. ¿Te imaginas cobrando a cada usuario, vendiendo a empresas, trabajando con consultores o aún no lo sabes?
18. ¿Quién tendría presupuesto y autoridad para pagar?
19. ¿Qué señal demostraría que hay una oportunidad real: usuarios que vuelven, piloto pagado, venta u otra?
20. ¿Quieres construir una empresa desde ahora o validar primero un producto útil y rentable?

Para iniciar la siguiente conversación sin tener que resolver todo, se propusieron cinco preguntas semilla: **1, 5, 6, 10 y 19**. “No lo sé” también es una respuesta válida: ayuda a identificar qué se debe investigar.

## 7. Límites y estado de la evidencia

- Auditoría estática, no revisión exhaustiva de cada archivo.
- No se ejecutaron pruebas, build, escaneo de dependencias ni pruebas de producción.
- No se hicieron cambios de código ni se cerraron problemas del registro.
- Los estados de P-XX se citan como aparecen en el registro y deben reconciliarse con el código y la evidencia vigente antes de dar cualquier problema por cerrado.
- Las hipótesis de mercado y la visión descrita son propuestas para conversar, no decisiones aprobadas.

## 8. Próximo paso sugerido

Cuando el usuario quiera retomar la definición de rumbo, responder las cinco preguntas semilla permitirá convertir la hipótesis en una meta más concreta: perfil de usuario inicial, problema prioritario, primer resultado del producto y señal de validación. En paralelo, el primer hito técnico recomendado es cerrar P-11 y reconciliar los estados del registro.
