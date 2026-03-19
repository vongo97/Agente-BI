# 🛠️ Guía de Desarrollo Local - Agente BI

Esta guía contiene los pasos esenciales para mantener tu entorno de ejecución estable y solucionar errores comunes de forma rápida.

---

## 🚀 1. El "Kit de Rescate" (Comandazos)

Si el servidor no arranca o te da errores extraños, usa estas herramientas:

### A. Si el puerto 8000 está ocupado (Error 10048)
Esto pasa si cerraste la terminal pero el proceso siguió vivo.
**PowerShell:**
```powershell
# Encontrar el proceso que molesta
netstat -ano | findstr :8000
# Matarlo (Sustituye PID por el número que te salga al final)
taskkill /F /PID [EL_NÚMERO_AQUÍ]
```

### B. Si la base de datos se desincroniza
Si agregamos nuevas funciones y te sale un error de `OperationalError` (columna no encontrada), ejecuta:
```bash
python server/src/utils/migrate_db.py
```

---

## 📁 2. Configuración de Entorno (`.env`)

Asegúrate de tener un archivo `.env` en la carpeta `server` basado en el `.env.example`:
- `DATABASE_URL=sqlite:///./test_bi.db` (Recomendado para pruebas limpias)
- `AUTHORIZED_EMAILS=invitado@agente-bi.local` (Permítete entrar sin login real)
- `PORT=8000`

---

## 🧹 3. Limpieza de Memoria
Si los datos se ven "mezclados" o quieres empezar de cero:
1. **Borra la caché**: Elimina todo el contenido de la carpeta `server/sessions_cache/`.
2. **Borra la DB** (Opcional): Si no te importa el historial, puedes borrar `test_bi.db` y se volverá a crear automáticamente al iniciar el servidor.

---

## 🏎️ 4. Flujo de Trabajo Recomendado

1. **Backend**: Siempre inicia el backend primero (`cd server && python main.py`).
2. **Frontend**: Inicia el frontend en otra terminal (`cd client && npm run dev`).
3. **Logs**: Si ves un error en la interfaz, **mira siempre la terminal del backend**, ahí está el detalle real del problema.

---

**Tip**: Mantén esta guía a mano para no perder tiempo reiniciando todo el PC cuando un puerto se quede colgado.
