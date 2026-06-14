# 🚨 REGLAS ESTRICTAS PARA AGENTES DE IA (AI_RULES.md) 🚨

Este documento contiene las reglas INQUEBRANTABLES que todo agente de IA (como yo o cualquier versión futura) debe leer y obedecer ciegamente al trabajar en este proyecto.

## REGLA #1: EL MODELO DE GEMINI ES INTOCABLE (FAMILIA 3.X) 💎
- **NUNCA, BAJO NINGUNA CIRCUNSTANCIA**, debes cambiar el modelo de Google Gemini a versiones inferiores (como la familia 1.x o 2.x).
- **ÚNICA VERSIÓN ACEPTADA**: Familia `3.x` (ejemplo: `gemini-3.0-flash` o `gemini-3.1-pro`).
- **MOTIVO**: Las APIs actuales de Google en este entorno rechazan los modelos anteriores o generan bloqueos de cliente y errores extraños (`Client has been closed`). Si el sistema se rompe, la culpa es tuya por tocar el modelo.
- ¡Si vas a sugerir cambios en `bi_analyst.py`, aléjate del diccionario `MODELS["GEMINI"]` a menos que sea para actualizarlo a una versión `3.x` superior!

## REGLA #2: Aislar los Clientes de IA de Funciones Asíncronas 🧵
- La librería `google-genai` usa clientes HTTP síncronos bajo el capó.
- **NUNCA** invoques métodos del cliente de Gemini (como `.models.list()` o `.models.generate_content()`) directamente en el event loop principal de FastAPI (`async def`). 
- **SIEMPRE** envuelve esas rutas o llamadas en funciones `def` normales (síncronas) para que FastAPI las mande a un threadpool seguro. Si no lo haces, el cliente morirá con el error `CANNOT SEND A REQUEST, AS THE CLIENT HAS BEEN CLOSED`.

## REGLA #3: El Validador de Llaves debe ser Flexible 🔑
- Si una API Key responde con errores de cuota (429, quota, limit), **LA LLAVE ES VÁLIDA**. El validador en `bi_analyst.py` debe permitir que la llave se guarde para que el usuario pueda usar otros proveedores (como Mistral) mientras tanto. No bloquees la interfaz de usuario con errores rígidos.

## REGLA #4: CARGA OBLIGATORIA DEL PROTOCOLO DE INTERACCIÓN 🤝
- **SIEMPRE**, en el primer turno de una conversación o al abordar un nuevo requerimiento, debes leer el archivo de la skill `.codex/skills/user-interaction-protocol/SKILL.md`.
- **MOTIVO**: Esta regla asegura que apliques los criterios de aceptación 10/10 del usuario, prevengas reprocesos y te mantengas estrictamente en el alcance estipulado. Ignorar este paso se considerará una violación grave de las reglas del proyecto.

---
*He leído y entendido estas reglas.*


