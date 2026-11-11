# Plan de Implementación — P-11: Subida Segura (Cifrado en Memoria + Zip-Bomb Temprano)

**Fecha:** 2026-11-10  
**Proyecto:** Vektra BI / Agente-BI  
**Estado:** Pendiente de aprobación  
**Autor:** Auditoría

---

## 1. Problema (según `docs/PROBLEMAS_CONOCIDOS.md`)

> **P-11** — Uploads: Original escrito en claro en `.tmp` antes de cifrar; sin mitigación de zip-bomb  
> **Estado:** 🟡 REABIERTO (2026-11-03)  
> **Evidencia:** `server/src/routers/data.py:155-183`, `is_encrypted=False` en `:204`  
> **Detalle:** El fix fue revertido en `885b3b61` (restaurar persistencia, P-57) reescribió `upload_file` y volvió a guardar el original **en claro** en disco y en nube. El test de regresión se borró en `20040e19`. El read-back **SÍ soporta cifrado** (`common.py:485-499`, `load_source_to_session`), así que re-cifrar en escritura es compatible. P-21 reconstruye los tests; el re-cifrado se reaplica con el zip-bomb temprano.

---

## 2. Análisis del Flujo Actual (`server/src/routers/data.py` - `upload_file`)

```python
# Línea 169-170: leer bytes crudos
file.file.seek(0)
raw_bytes = file.file.read()

# Línea 175: parsear SIN validación zip-bomb previa
df = load_file_data_from_bytes(raw_bytes, clean_name)

# Línea 209-212: escribir EN CLARO a disco
with open(permanent_path, 'wb') as f:
    f.write(raw_bytes)

# Línea 228: subir EN CLARO a la nube
cloud_ok = bool(upload_bytes(cloud_key, raw_bytes))

# Línea 257: registrar como NO cifrado
is_encrypted=False
```

**El guard `_reject_zip_bomb_early` existe (líneas 49-92) pero NO se invoca.**

---

## 3. Capacidad de Descifrado Ya Existente (`server/src/utils/common.py`)

```python
# Líneas 486-495: load_source_to_session YA descifra si is_encrypted=True
if is_encrypted:
    from src.utils.security import decrypt_file_to_bytes
    from src.connectors.data_connectors import load_file_data_from_bytes
    try:
        raw_bytes = decrypt_file_to_bytes(local_path)
        df = load_file_data_from_bytes(raw_bytes, source.name)
    except Exception as dec_err:
        logger.error("Error descifrando archivo %s: %s", local_path, dec_err)
        return False
```

✅ **Compatibilidad garantizada:** re-cifrar en escritura no rompe la lectura.

---

## 4. Cambios Requeridos (3 puntos quirúrgicos en `data.py:upload_file`)

### Cambio 1: Validación zip-bomb ANTES de parsear (línea ~173)
```python
# ── VALIDACIÓN TEMPRANA ZIP-BOMB (P-11) ──
_reject_zip_bomb_early(raw_bytes, clean_name)
```
**Ubicación:** Entre `raw_bytes = file.file.read()` (l.170) y `df = load_file_data_from_bytes(...)` (l.175).

### Cambio 2: Cifrar EN MEMORIA antes de escribir disco/nube (líneas ~211, ~228)
```python
# ── CIFRAR EN MEMORIA (P-11) ──
encrypted_bytes = encrypt_bytes(raw_bytes)

# Escribir disco (caché local cifrada)
with open(permanent_path, 'wb') as f:
    f.write(encrypted_bytes)

# Subir a nube (cifrado)
cloud_ok = bool(upload_bytes(cloud_key, encrypted_bytes))
```

### Cambio 3: Marcar fuente como cifrada (línea ~257)
```python
is_encrypted=True,  # Era False
```

---

## 5. Tests de Regresión (P-21: reconstruir tests borrados)

### `server/tests/test_upload_encryption.py` (nuevo)
```python
def test_upload_encrypts_at_rest(tmp_path, client, auth_headers):
    """El archivo se guarda cifrado (no legible en claro) en disco y nube."""
    # 1. Subir CSV
    csv = b"col1,col2\n1,2\n3,4\n"
    resp = client.post("/api/v1/upload", files={"file": ("test.csv", csv, "text/csv")}, headers=auth_headers)
    assert resp.status_code == 200
    source_id = resp.json()["id"]

    # 2. Verificar en BD: is_encrypted=True
    from src.database import DataSource, get_db
    db = next(get_db())
    source = db.query(DataSource).filter(DataSource.id == source_id).first()
    assert source.is_encrypted is True

    # 3. Verificar que el archivo local NO es legible en claro
    local_path = source.url  # cuando cloud falla, url = ruta local
    with open(local_path, "rb") as f:
        data = f.read()
    assert not data.startswith(b"col1")  # no está en claro
    assert data.startswith(b"gAAAA")     # token Fernet

def test_upload_rejects_zip_bomb_xlsx(tmp_path, client, auth_headers):
    """Excel con dimensiones declaradas > 2M celdas se rechaza ANTES de parsear."""
    # Crear xlsx "bomba" (solo XML de dimensiones, sin celdas reales)
    from openpyxl import Workbook
    from io import BytesIO
    wb = Workbook()
    ws = wb.active
    # Forzar dimensión declarada enorme
    ws.sheet_format.defaultRowHeight = 15
    ws._dimension = "A1:XFD1048576"  # ~17M celdas declaradas
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    resp = client.post("/api/v1/upload", files={"file": ("bomba.xlsx", buf.read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}, headers=auth_headers)
    assert resp.status_code == 400
    assert "demasiadas celdas" in resp.json()["detail"].lower()

def test_upload_rejects_zip_bomb_csv(client, auth_headers):
    """CSV con > 2M líneas se rechaza ANTES de parsear."""
    huge_csv = b"col1\n" + b"x\n" * 2_000_001
    resp = client.post("/api/v1/upload", files={"file": ("huge.csv", huge_csv, "text/csv")}, headers=auth_headers)
    assert resp.status_code == 400
    assert "demasiadas l" in resp.json()["detail"].lower()

def test_encrypted_file_roundtrip(tmp_path, client, auth_headers, db_session):
    """Archivo cifrado se descifra y parsea correctamente al recargar sesión."""
    csv = b"ventas,profit\n1000,100\n2000,200\n"
    resp = client.post("/api/v1/upload", files={"file": ("data.csv", csv, "text/csv")}, headers=auth_headers)
    assert resp.status_code == 200
    source_id = resp.json()["id"]

    # Simular reinicio: limpiar cache y recargar via ensure_user_session
    from src.utils.common import data_store, get_session_key, ensure_user_session
    user = "test@example.com"
    session_key = get_session_key(user)
    data_store.pop(session_key, None)

    session = ensure_user_session(user, db_session)
    assert session is not None
    assert "data" in session and len(session["data"]) == 1
    df = next(iter(session["data"].values()))
    assert list(df.columns) == ["ventas", "profit"]
    assert len(df) == 2
```

---

## 6. Criterios de Cierre (Verificables)

| Criterio | Comando / Test |
|----------|----------------|
| **Cifrado en reposo** | `pytest server/tests/test_upload_encryption.py::test_upload_encrypts_at_rest -xvs` → PASS |
| **Zip-bomb Excel** | `pytest server/tests/test_upload_encryption.py::test_upload_rejects_zip_bomb_xlsx -xvs` → PASS |
| **Zip-bomb CSV** | `pytest server/tests/test_upload_encryption.py::test_upload_rejects_zip_bomb_csv -xvs` → PASS |
| **Round-trip descifrado** | `pytest server/tests/test_upload_encryption.py::test_encrypted_file_roundtrip -xvs` → PASS |
| **Suite completa** | `pytest server/tests/ -x` → 332+ passed, 3 xfailed (sin regresiones) |
| **Type-check** | `cd client && npx tsc --noEmit` → limpio |
| **Build cliente** | `cd client && npm run build` → OK |

---

## 7. Archivos a Modificar

| Archivo | Cambio | Riesgo |
|---------|--------|--------|
| `server/src/routers/data.py` | 3 ediciones quirúrgicas en `upload_file` (líneas ~173, 211, 228, 257) | **Bajo**: lectura ya soporta cifrado |
| `server/tests/test_upload_encryption.py` | **NUEVO** - 4 tests de regresión | **Ninguno**: solo añade cobertura |

---

## 8. Orden de Ejecución (Incremental)

1. **Añadir test** `test_upload_encryption.py` (verifica estado actual: falla por `is_encrypted=False`)
2. **Aplicar Cambio 1** (zip-bomb early) → test zip-bomb pasa
3. **Aplicar Cambio 2** (cifrar en memoria) → test cifrado pasa
4. **Aplicar Cambio 3** (`is_encrypted=True`) → test round-trip pasa
5. **Suite completa** → verde

---

## 9. Rollback Plan

Si algo falla en producción:
```bash
git revert <commit-P11>
# El read-back ya soporta ambos formatos (cifrado y legacy sin cifrar)
# Los archivos subidos antes del fix se leen por el branch `else` (línea 496-499 common.py)
```

---

## 10. Pregunta de Aprobación

**¿Aprobamos este plan y procedo a implementar los 3 cambios quirúrgicos + tests en `data.py`?**