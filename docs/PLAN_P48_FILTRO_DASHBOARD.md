# Plan de Implementación — P-48: `/dashboard/filter` responde 200 aunque columna no exista

> **Estado: IMPLEMENTADO Y VERIFICADO (2026-11-14).** P-48 cerrado con evidencia.
> Ver [Resultado de la implementación](#resultado-de-la-implementación) al final del documento.

## Contexto

El endpoint `POST /api/v1/dashboard/filter` (`server/src/routers/dashboard.py:268-344`) presenta tres defectos críticos registrados bajo **P-48** en `docs/PROBLEMAS_CONOCIDOS.md:121`:

1. **Silencio en columnas desconocidas** (`dashboard.py:298`): `if col in new_df.columns and ...` omite columnas que no existen y devuelve `200 success` con datos sin filtrar. Evidencia en tiempo real: `POST /dashboard/filter {"NoExiste":123} → 200 success`.
2. **Modo SQL roto** (`dashboard.py:304-306`): un `TODO` — `filtered_context = context` devuelve el motor SQLAlchemy `engine` en lugar de un DataFrame, por lo que `execute_analysis` nunca materializa datos y las figuras fallan en silencio.
3. **Fallo invisible por item** (`dashboard.py:333-336`): los items que fallan al re-ejecutarse se `continue`n, y el endpoint sigue informando `"status": "success"`. El cliente no distingue figura filtrada de figura obsoleta.

El patrón de diseño es crítico: en SQL mode, `DashboardItem.message.analysis_code` guarda **código Python/pandas** que referencia la variable `df` o `dfs`, **no** una sentencia SQL persistente (ver `analysis.py:495` y `bi_analyst.py:318,323`). Por eso `dashboard.py:289` usa `var_name = "dfs"` para archivo y `"engine"` para SQL, pero `execute_analysis` serializa solo `pd.DataFrame` — una `engine` resulta en `tables_to_save` vacío → error `NameError: name 'df' is not defined`. **La corrección SQL-mode no inyecta WHERE en SQL; materializa un DataFrame filtrado y ejecuta el código Python guardado contra él.**

## Enfoque recomendado

### 1. Columna desconocida → HTTP 400 (rechaza en ambos modos)

Agregar validación antes de filtrar: comprobación del esquema vivo para nombres de tabla y columna. Esto resuelve P-48 en ambas ramas (archivo y SQL) y elimina el "éxito falso".

### 2. Modo archivo: validación del esquema DataFrame + reporte de columnas ausentes

Usar `inspect(df).columns` o `.columns` directamente, comparar los filtros contra las columnas reales.

### 3. Modo SQL: materializar un DataFrame filtrado antes de re-ejecutar

- Inspeccionar el engine con `sqlalchemy.inspect(engine).get_table_names()` y `get_columns(table)`
- Construir una consulta `SELECT * FROM <tabla> WHERE <col> = :valor` (con bound parameters, sin interpolación de string)
- Ejecutar la consulta con `execute_sql_with_params()` (nueva función), obtener un `pd.DataFrame`
- Pasar el DataFrame al contexto de ejecución como `{nombre_tabla: df}`, establecer `var_name = "dfs"` (para que el sandbox serialice y el código Python guardado sobre `df` o `dfs` funcione)
- Si la tabla/columna no existe → 400 con detalle

### 4. Fallos por item: marcar con error

Cambiar el bloque `try/except` en cada item (línea 324-336) para incluir `"fig": null` y un campo `"error"` con el motivo. El cliente puede entonces distinguir figura filtrada de figura que falló.

## Cambios planeados

### A. `server/src/routers/dashboard.py` — modificaciones principales

1. **Importar `inspect` desde `sqlalchemy`** (línea 3, ya está en `dashboard.py` línea 3). Añadir `from sqlalchemy import inspect`.

2. **Añadir `execute_sql_with_params` a la importación** desde `executor.py`:
   ```python
   from src.engine.executor import execute_analysis, execute_sql_with_params
   ```

3. **Crear una función auxiliar `_introspect_engine(engine)`** que devuelva `[{"table": name, "columns": [col['name'] for col in columns]}]` usando `sqlalchemy.inspect`. Esto se reutiliza tanto para validación como para construcción de WHERE.

4. **Modificar la rama `data_type == "file"`** (línea 292-303):
   - Parsing estricto del JSON `filters` (actualmente `json.loads(filters_json)` con `except:` bare → 400).
   - Validar cada clave de filtro contra `df.columns` real.
   - Si alguna clave no existe: lanzar `HTTPException(400, detail="La columna '{col}' no existe en los datos. Columnas disponibles: Region, Sales, Profit")`.
   - Si todas existen: filtrado como hoy (`new_df = new_df[new_df[col] == val]`), pero con validación previa.

5. **Modificar la rama `else` (modo SQL)** (línea 304-306):
   - En lugar de `filtered_context = context`:
   a. Inspeccionar el engine: `inspector = inspect(engine)`, `tables = inspector.get_table_names()`.
   b. Para cada tabla en `session_data["schema"]` (formato `Table: X, Columns: [...]`), extraer el nombre de tabla y la lista de columnas con `ast.literal_eval` del string de columnas (el formato de `get_db_schema()` es Python `list` repr, no JSON).
   b. Validar cada clave de filtro: la tabla debe existir en `tables` y la columna debe estar en su lista de columnas.
   c. Si alguna clave es desconocida: lanzar `HTTPException(400, detail="La columna '{col}' no existe en los datos. Columnas disponibles: {cols_available}")`.
   d. **Construir consulta parametrizada**: `SELECT * FROM <tabla> WHERE <col> = :valor`. NOTA: column names cannot be parameterized in SQL; they must be validated against the catalog (see §5 of the agent report). Values are bound via `params={"valor": val}`.
   e. Ejecutar con `execute_sql_with_params(engine, sql, params)`.
   f. El resultado es un `pd.DataFrame`. Empaquetarlo en el contexto: `filtered_context = {table_name: df_result}`.
   g. **Establecer `var_name = "dfs"`** en lugar de `"engine"`, para que `execute_analysis` serialice el DataFrame y el código Python guardado sobre `df`/`dfs` funcione correctamente.

6. **Modificar el bucle de re-ejecutado** (línea 324-336):
   - Capturar `Exception` y, en lugar de `continue`, incluir el item con `"fig": null` y `"error": safe_error_message(e)`.
   - El resultado final incluirá esta bandera para que el cliente sepa que la figura no se pudo re-ejecutar.

### B. `server/src/engine/executor.py` — nueva función auxiliar

Añadir después de `execute_sql_safe` (línea 935):

```python
def execute_sql_with_params(engine, sql: str, params: Optional[dict] = None):
    """Ejecuta una consulta SQL de solo lectura con bound parameters."""
    from sqlalchemy import text
    try:
        validate_sql_safety(sql)  # Reutiliza la validación existente
        with engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            df_result = pd.DataFrame(result.fetchall(), columns=list(result.keys()))
        return f"Resultados ({len(df_result)} filas):\n{df_result.to_string()}", df_result, sql
    except Exception as e:
        return f"### ⚠️ Error SQL\n{e}", None, sql
```

- **No modifica `execute_sql_safe`** — la guardia estática `test_sql_mode_safety.py:100` depende de que `"execute_sql_safe" in analysis.py` sea verdadera. `execute_sql_with_params` es un nuevo nombre, no un reemplazo.

### C. Verificación y testing

1. **Tests unitarios** en `server/tests/test_dashboard.py` (estilo `unittest.TestCase` existente):
   - `test_filter_unknown_column` → POST /dashboard/filter con JSON para una columna que no existe → HTTP 400.
   - `test_filter_valid_column_file` → POST /dashboard/filter con filtro sobre columna real en modo archivo → 200, figura re-ejecutada.
   - `test_filter_valid_column_sql` → POST /dashboard/filter con filtro sobre tabla SQL existente → 200, DataFrame materializado y figuras re-ejecutadas (mock engine SQLite via `create_engine`).
   - `test_filter_figures_with_errors` → algunos items fallan al re-ejecutarse → figura `null` + error en la respuesta.

2. **Tests de integración** (con `create_engine("sqlite:///:memory:")`):
   - Crear una tabla SQLite de prueba, insertar datos, conectar vía `get_sql_engine`.
   - Verificar que el filtro construya `SELECT * FROM tabla WHERE col = :valor` y devuelva exactamente las filas que coinciden.
   - Verificar que una columna desconocida provoque 400.

3. **End-to-end manual** (usando el entorno real):
   - Levantar el backend con datos cargados (archivo CSV o SQL).
   - Desde el frontend, hacer clic en una barra de gráfico para filtrar.
   - Verificar que el filtro se aplique efectivamente a las figuras (los datos cambian, no solo el "éxito").
   - Probar con una columna que no existe → ver mensaje de error claro.

## Verificación

### Tests locales que deben pasar

```powershell
# Backend
cd server; .\.venv-codex\Scripts\python.exe -m pytest tests/test_dashboard.py -q

# Frontend
cd client; npm run lint; npm run build
```

### Checklist de autoverificación (antes de responder "listo")

- [ ] Leí `docs/PROBLEMAS_CONOCIDOS.md` y cité P-48.
- [ ] Si cerré algún P-XX existente, anoté evidencia de cierre.
- [ ] No introduje ninguno de los 10 anti-patrones de la sección 2 del registro.
- [ ] Ejecuté `pytest tests/test_dashboard.py -q` y todos los tests pasaron (incluyendo los nuevos).
- [ ] Actualicé el historial del registro con la fecha y el cambio.

## Riesgos y consideraciones

- **Columnas dinámicas desde Plotly**: las claves de filtro llegan desde el frontend como nombres de trazas de Plotly (evento `plotly_hover` o `plotly_click`). No siempre coinciden con nombres de columna reales. La validación contra el esquema vivo resuelve esto: si la clave no está en `df.columns` (archivo) o en la lista de columnas de la tabla (SQL), se rechaza con 400.
- **Modo SQL y WHERE dinámico**: se evita inyectar sentencias SQL arbitrarias validando nombres de tabla y columna contra el catálogo vivo (`inspect(engine)`). Los valores se pasan como bound parameters (`:valor`), lo que evita inyección por valores también. Los nombres de columna nunca llegan al string SQL; solo aparecen en la sentencia `SELECT * FROM tabla WHERE`, y la validación de catálogo garantiza que esa tabla y columna existen.
- **`DataSource.columns` truncado a 500 chars**: no se confía en este campo; siempre se introspecciona el engine vivo.
- **Performance**: cada filtro re-ejecuta el código Python del item en un subprocess de sandbox. Con filtros activos, esto es costoso pero el comportamiento actual ya es el mismo (el TODO P-48 no empeora la performance, solo hace el éxito falso). La validación previa evita viajes al sandbox para filtros inválidos.
- **Compatibilidad con items de auditoría**: items cuyo `analysis_code` empieza con `AUDIT_MARKER` se mantienen inalterados — se conserva la figura original tal como viene del paquete determinista.

---

## Resultado de la implementación

### Archivos tocados

| Archivo | Cambio |
|---|---|
| `server/src/routers/dashboard.py` | Reescritura de `filter_dashboard` + 3 helpers: `_resolve_filter_columns`, `_filter_file_context`, `_filter_sql_context` |
| `server/src/engine/executor.py` | Nueva función `execute_sql_with_params(engine, sql, params)` (función **nueva**, no sustituye a `execute_sql_safe`: la guardia estática de `test_sql_mode_safety.py:100` depende de ese nombre) |
| `server/src/connectors/data_connectors.py` | Nueva función `get_db_schema_structured(engine)` → `[{"table": str, "columns": [str]}]` vía `sqlalchemy.inspect` |
| `client/src/components/DashboardView.tsx` | `applyRemoteFilters` muestra el `detail` del 400 y el `error` por item con `addToast` |
| `client/src/types/shared.ts` | `DashboardItem.error?: string` |
| `server/tests/test_dashboard_filter.py` | **NUEVO** — 12 tests de regresión |
| `docs/PROBLEMAS_CONOCIDOS.md` | P-48 → CERRADO (resumen, ficha, historial, matriz de pruebas) |

### Decisiones que se desviaron del plan original

1. **La resolución de columnas tiene un paso más**: además de la coincidencia exacta (sin distinguir mayúsculas/minúsculas ni espacios), se acepta el caso en que la **traza de Plotly contiene** el nombre de una columna real (`"Ventas por Region"` → `"Region"`), y solo si la coincidencia es **única**: si hay varias, es ambiguo y se rechaza con 400. Sin este paso, un clic en un gráfico con nombre de traza no-real habría producido un 400 en cada clic.

2. **El esquema SQL se lee del engine vivo, no del texto guardado**: `get_db_schema_structured()` usa `sqlalchemy.inspect(engine)`, no `session_data["schema"]` (que es una foto y puede quedarse obsoleta). El `schema` guardado viene del formato `Table: X, Columns: [...]`, que además es un `list` repr de Python y no JSON.

3. **Los valores del filtro viajan como parámetros bind** (`:p0`), nunca interpolados. Los **nombres** de tabla y columna sí aparecen en el string SQL, pero se validan contra el catálogo antes de construir la consulta — un identificador no se puede parameterizar.

4. **Los items de auditoría (`AUDIT_MARKER`) no se re-ejecutan**: la auditoría es una foto determinista del dataset; filtrarla dejaría los hechos fuera de contexto. Se conserva la figura original.

### Verificación ejecutada

```powershell
cd server; .\.venv-codex\Scripts\python.exe -m pytest tests/test_dashboard_filter.py -q
# → 12 passed

cd server; .\.venv-codex\Scripts\python.exe -m pytest tests/ -q
# → 349 passed, 3 xfailed, 9 subtests passed   (baseline: 339 passed → +12, 0 regresiones)

cd client; npm run build
# → ✓ Compiled successfully · ✓ Finished TypeScript

cd client; npx eslint src/components/DashboardView.tsx src/types/shared.ts
# → 2 errors (react-hooks/set-state-in-effect) — IDÉNTICOS al baseline (verificado con git stash)
```

> Nota de entorno: `server\.venv` está roto en esta máquina (`pyvenv.cfg` apunta a un stub de Microsoft Store). Se usó `server\.venv-codex\Scripts\python.exe` (Python 3.12.14, pytest 9.1.1, fastapi 0.133.0).

### Detalle no obvio descubierto durante los tests

`sqlite:///:memory:` **no sirve** para probar el modo SQL: cada conexión abre una base distinta y vacía, así que el inspector (que abre su propia conexión) no ve la tabla creada por otra conexión. Los tests usan `poolclass=StaticPool` + `connect_args={"check_same_thread": False}` para que todas las conexiones compartan la misma base en memoria.

### Lo que queda pendiente (fuera del alcance de P-48)

- El frontend sigue enviando el **nombre de la traza de Plotly** como clave de filtro. Con la resolución por contenido, la mayoría de los clics funcionan; los que no, devuelven 400 con las columnas disponibles, que es preferible al silencio anterior.
- `DashboardView.tsx` mantiene 2 errores de lint preexistentes (`react-hooks/set-state-in-effect`) **no relacionados** con este cambio; no se tocaron para no mezclar alcances.