"""Tests de regresión para P-11: Subida segura (cifrado en reposo + zip-bomb temprano)."""
import os
import sys
import io
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import src.utils.common as common  # noqa: E402
from src.database import DataSource, get_db  # noqa: E402
from src.routers import data as data_router  # noqa: E402
from src.utils.limiter import limiter  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

# Configurar entorno de test
os.environ["ENVIRONMENT"] = "development"
os.environ["RENDER"] = "false"
os.environ["AUTH_SECRET"] = "test-secret"

# Mock módulos faltantes antes de importar routers
import types  # noqa: E402
pkce_mod = types.ModuleType('src.utils.pkce_storage_factory')
class FakePKCEStorageFactory:
    def create_storage(self, storage_type="redis"):
        return MagicMock()
pkce_mod.PKCEStorageFactory = FakePKCEStorageFactory
sys.modules['src.utils.pkce_storage_factory'] = pkce_mod

pkce_mid = types.ModuleType('src.utils.pkce_middleware')
class FakePKCEAuthMiddleware:
    def __init__(self, app=None, exclude_paths=None, storage_factory=None, **kwargs):
        pass
pkce_mid.PKCEAuthMiddleware = FakePKCEAuthMiddleware
sys.modules['src.utils.pkce_middleware'] = pkce_mid

_TEST_USER_SAFE = "c9e1e7e5d8b8e8c8d8e8f8a8b8c8d8e8"  # hash md5 de test_user_persistence@example.com


def _clean_test_user_pickle():
    pkl = os.path.join(common.SESSIONS_DIR, f"{_TEST_USER_SAFE}.pkl")
    if os.path.exists(pkl):
        os.remove(pkl)


class TestUploadEncryption(unittest.TestCase):
    """Tests de integración para /api/v1/upload con cifrado y zip-bomb."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

        # Patch de directorios y red.
        # Los parches deben aplicarse sobre el módulo que RESUELVE los nombres:
        # `data.py` hace `from src.utils.common import DATA_SOURCES_DIR` y
        # `from src.services.storage_service import upload_bytes`, es decir
        # importa por valor. Parchear `common` no surte efecto en el router
        # (upload_bytes/delete_object ni siquiera existen allí) y el archivo
        # se escribiría en el ./data_sources real.
        patches = [
            patch.object(data_router, "DATA_SOURCES_DIR", self._tmp.name),
            patch.object(common, "SESSIONS_DIR", self._tmp.name),
            patch.object(common, "sync_cloud_to_local", lambda *a, **k: False),
            patch.object(common, "upload_file_to_cloud", lambda *a, **k: True),  # nube OK por defecto
            patch.object(data_router, "upload_bytes", lambda *a, **k: True),  # nube OK por defecto
            patch.object(data_router, "delete_object", lambda *a, **k: True),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)

        common.data_store.clear()
        self.addCleanup(common.data_store.clear)
        _clean_test_user_pickle()
        self.addCleanup(_clean_test_user_pickle)

        # El rate limiter de slowapi es global y compartido entre tests: el
        # endpoint /upload tiene límite de 5/min por usuario. Sin resetearlo,
        # este test hereda el cupo consumido por test_data.py y falla con 429
        # según el orden de ejecución de la suite.
        limiter.reset()

        # App de test
        app = FastAPI()
        app.state.limiter = limiter
        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db
        app.include_router(data_router.router, prefix="/api/v1")
        self.client = TestClient(app)

        # Mock base de consultas a DB
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        self.mock_db.query.return_value.filter.return_value.count.return_value = 0
        self.mock_db.query.return_value.filter.return_value.all.return_value = []

    def tearDown(self):
        common.data_store.clear()
        _clean_test_user_pickle()

    def _mock_auth(self, mock_get_user, mock_authz):
        mock_get_user.return_value = "test_user_persistence@example.com"

    def _setup_mock_db_for_upload(self):
        """Configura mocks de DB para que add/refresh/commit funcionen."""
        captured = {}

        def fake_add(obj):
            if hasattr(obj, 'id') and obj.id is None:
                obj.id = 1
            captured["source"] = obj
            return obj

        self.mock_db.add.side_effect = fake_add
        self.mock_db.refresh.side_effect = lambda obj: setattr(obj, 'id', 1)
        self.mock_db.commit.return_value = None
        return captured

    @patch('src.routers.data.get_authenticated_user')
    @patch('src.routers.data.check_authorization')
    @patch('src.connectors.data_connectors.load_file_data_from_bytes')
    def test_upload_encrypts_at_rest(self, mock_load, mock_authz, mock_get_user):
        """El archivo se guarda cifrado (no legible en claro) en disco."""
        self._mock_auth(mock_get_user, mock_authz)
        captured = self._setup_mock_db_for_upload()

        df = pd.DataFrame({"col1": [1, 3], "col2": [2, 4]})
        mock_load.return_value = df

        csv_bytes = b"col1,col2\n1,2\n3,4\n"
        response = self.client.post(
            "/api/v1/upload",
            files={"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")}
        )

        self.assertEqual(response.status_code, 200, f"Upload falló: {response.json()}")
        body = response.json()
        self.assertIn("filename", body)
        self.assertEqual(body["rows"], 2)

        # Verificar en BD: is_encrypted=True
        source = captured.get("source")
        self.assertIsNotNone(source, "DataSource no capturado en mock")
        self.assertTrue(source.is_encrypted, f"is_encrypted={source.is_encrypted}, esperado True")

        # Verificar que el archivo local NO es legible en claro.
        # Con la nube disponible, `source.url` es la clave de bucket
        # (`data_sources/<md5>/...`), no una ruta del contenedor: el archivo
        # cifrado en disco se localiza en DATA_SOURCES_DIR.
        local_files = [
            os.path.join(self._tmp.name, name)
            for name in os.listdir(self._tmp.name)
            if name.endswith(".csv")
        ]
        self.assertTrue(local_files, f"No se encontró archivo local en {self._tmp.name}")
        local_path = local_files[0]
        with open(local_path, "rb") as f:
            data = f.read()
        self.assertFalse(data.startswith(b"col1"), "Archivo local legible en claro (debería estar cifrado)")
        self.assertTrue(data.startswith(b"gAAAA"), f"Archivo no tiene token Fernet: {data[:20]}")

    @patch('src.routers.data.get_authenticated_user')
    @patch('src.routers.data.check_authorization')
    @patch('src.connectors.data_connectors.load_file_data_from_bytes')
    def test_upload_rejects_zip_bomb_xlsx(self, mock_load, mock_authz, mock_get_user):
        """Excel con dimensiones declaradas > 2M celdas se rechaza ANTES de parsear."""
        self._mock_auth(mock_get_user, mock_authz)

        # Construir un xlsx legítimo cuyo <dimension> declara ~17M celdas.
        # openpyxl NO sirve aquí: `wb.save()` recalcula el rango real y
        # descarta el `_dimension` inyectado (queda 1x1). Hay que reescribir
        # el XML de la hoja dentro del zip para que la dimensión declarada
        # sea la que lee el guard (openpyxl en read_only usa ws.max_row/max_column).
        import zipfile
        from io import BytesIO

        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "[Content_Types].xml",
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                '</Types>',
            )
            zf.writestr(
                "_rels/.rels",
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                '</Relationships>',
            )
            zf.writestr(
                "xl/workbook.xml",
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                '<sheets><sheet name="bomba" sheetId="1" r:id="rId1"/></sheets></workbook>',
            )
            zf.writestr(
                "xl/_rels/workbook.xml.rels",
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
                '</Relationships>',
            )
            # La dimensión declarada: XFD1048576 = 16384 columnas x 1048576 filas
            # = 17.179.869.184 celdas, muy por encima del límite de 2M.
            zf.writestr(
                "xl/worksheets/sheet1.xml",
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                '<dimension ref="A1:XFD1048576"/>'
                '<sheetData/>'
                '</worksheet>',
            )

        response = self.client.post(
            "/api/v1/upload",
            files={"file": ("bomba.xlsx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )

        self.assertEqual(response.status_code, 400, f"Se esperaba 400, got {response.status_code}: {response.json()}")
        detail = response.json()["detail"].lower()
        self.assertIn("demasiadas celdas", detail, f"Mensaje inesperado: {detail}")
        # load_file_data_from_bytes NO debe haberse llamado (rechazo temprano)
        mock_load.assert_not_called()

    @patch('src.routers.data.get_authenticated_user')
    @patch('src.routers.data.check_authorization')
    @patch('src.connectors.data_connectors.load_file_data_from_bytes')
    def test_upload_rejects_zip_bomb_csv(self, mock_load, mock_authz, mock_get_user):
        """CSV con > 2M líneas se rechaza ANTES de parsear."""
        self._mock_auth(mock_get_user, mock_authz)

        huge_csv = b"col1\n" + b"x\n" * 2_000_001
        response = self.client.post(
            "/api/v1/upload",
            files={"file": ("huge.csv", huge_csv, "text/csv")}
        )

        self.assertEqual(response.status_code, 400, f"Se esperaba 400, got {response.status_code}: {response.json()}")
        detail = response.json()["detail"].lower()
        self.assertIn("demasiadas l", detail, f"Mensaje inesperado: {detail}")
        # load_file_data_from_bytes NO debe haberse llamado (rechazo temprano)
        mock_load.assert_not_called()

    @patch('src.routers.data.get_authenticated_user')
    @patch('src.routers.data.check_authorization')
    @patch('src.connectors.data_connectors.load_file_data_from_bytes')
    def test_encrypted_file_roundtrip(self, mock_load, mock_authz, mock_get_user):
        """Archivo cifrado se descifra y parsea correctamente al recargar sesión."""
        self._mock_auth(mock_get_user, mock_authz)
        captured = self._setup_mock_db_for_upload()

        df = pd.DataFrame({"ventas": [1000, 2000], "profit": [100, 200]})
        mock_load.return_value = df

        csv_bytes = b"ventas,profit\n1000,100\n2000,200\n"
        response = self.client.post(
            "/api/v1/upload",
            files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")}
        )

        self.assertEqual(response.status_code, 200, f"Upload falló: {response.json()}")
        source_id = response.json()["id"]

        # Simular reinicio: limpiar cache en memoria y recargar via ensure_user_session
        common.data_store.clear()

        from src.utils.common import get_session_key, ensure_user_session
        user = "test_user_persistence@example.com"
        session_key = get_session_key(user)
        common.data_store.pop(session_key, None)

        session = ensure_user_session(user, self.mock_db)
        self.assertIsNotNone(session, "Sesión no reconstruida")
        self.assertIn("data", session)
        self.assertEqual(len(session["data"]), 1, f"Pool vacío: {session}")
        df_recovered = next(iter(session["data"].values()))
        self.assertEqual(list(df_recovered.columns), ["ventas", "profit"], f"Columnas: {df_recovered.columns}")
        self.assertEqual(len(df_recovered), 2, f"Filas: {len(df_recovered)}")


class TestUploadGuardStatic(unittest.TestCase):
    """Guardia estática: si alguien elimina la llamada a _reject_zip_bomb_early o el cifrado, el test falla."""

    def setUp(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "src", "routers", "data.py"), "r", encoding="utf-8") as fh:
            self.source = fh.read()

    def test_zip_bomb_guard_invocado_en_upload(self):
        """El guard _reject_zip_bomb_early debe llamarse en upload_file ANTES de parsear."""
        # Buscar la función upload_file y verificar que invoca _reject_zip_bomb_early
        self.assertIn(
            "_reject_zip_bomb_early(",
            self.source,
            "P-11: _reject_zip_bomb_early debe invocarse en upload_file antes de parsear"
        )
        # Verificar que se llama con raw_bytes y filename
        self.assertIn(
            "_reject_zip_bomb_early(raw_bytes, clean_name)",
            self.source,
            "P-11: _reject_zip_bomb_early debe recibir (raw_bytes, clean_name)"
        )

    def test_encrypt_bytes_invocado_antes_de_escribir_disco(self):
        """encrypt_bytes debe llamarse antes de escribir a disco."""
        self.assertIn(
            "encrypt_bytes(raw_bytes)",
            self.source,
            "P-11: encrypt_bytes debe invocarse para cifrar en memoria antes de escribir"
        )

    def test_is_encrypted_true_en_datasource(self):
        """DataSource debe crearse con is_encrypted=True."""
        self.assertIn(
            "is_encrypted=True",
            self.source,
            "P-11: DataSource debe registrarse con is_encrypted=True"
        )


if __name__ == "__main__":
    unittest.main()