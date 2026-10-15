import unittest
import sys
import os
import io
import types
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ["ENVIRONMENT"] = "development"
os.environ["RENDER"] = "false"
os.environ["AUTH_SECRET"] = "test-secret"

# Mock módulos faltantes antes de importar routers
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

from src.database import get_db
from src.utils.common import data_store, DATA_SOURCES_DIR
from src.routers import data as data_router
from src.utils.limiter import limiter
import hashlib
import pandas as pd

# Pickle de sesión que este router persiste en disco para el usuario de prueba.
# Sin limpieza, contamina a test_analysis en la misma máquina (el archivo vive
# entre invocaciones de pytest y get_user_data lo recoge).
_TEST_USER_SAFE = hashlib.md5(b"test_user_persistence@example.com").hexdigest()

def _clean_test_user_pickle():
    import src.utils.common as _common
    pkl = os.path.join(_common.SESSIONS_DIR, f"{_TEST_USER_SAFE}.pkl")
    if os.path.exists(pkl):
        os.remove(pkl)


class TestDataRouter(unittest.TestCase):
    """Tests de integración para el router de datos (/api/v1/upload y /api/v1/connect-gsheets)."""

    def setUp(self):
        app = FastAPI()
        app.state.limiter = limiter

        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db
        app.include_router(data_router.router, prefix="/api/v1")

        self.client = TestClient(app)
        data_store.clear()
        _clean_test_user_pickle()

        # Mock base de consultas a DB
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        self.mock_db.query.return_value.filter.return_value.count.return_value = 0
        self.mock_db.query.return_value.filter.return_value.all.return_value = []

    def tearDown(self):
        data_store.clear()
        _clean_test_user_pickle()

    @patch('src.routers.data.get_authenticated_user')
    @patch('src.routers.data.check_authorization')
    def test_upload_requires_file(self, mock_authz, mock_get_user):
        """Test que POST /api/v1/upload retorna 422 si no se envía archivo."""
        mock_get_user.return_value = "test_user_persistence@example.com"
        response = self.client.post("/api/v1/upload")
        self.assertEqual(response.status_code, 422)

    @patch('src.routers.data.get_authenticated_user')
    @patch('src.routers.data.check_authorization')
    def test_upload_invalid_extension(self, mock_authz, mock_get_user):
        """Test que POST /api/v1/upload rechaza archivos con extensión no permitida."""
        mock_get_user.return_value = "test_user_persistence@example.com"
        response = self.client.post(
            "/api/v1/upload",
            files={"file": ("test.txt", io.BytesIO(b"datos"), "text/plain")}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("extensión", response.json()["detail"].lower())

    @patch('src.routers.data.upload_bytes')
    @patch('src.routers.data.get_authenticated_user')
    @patch('src.routers.data.check_authorization')
    @patch('src.routers.data.load_file_data')
    def test_upload_valid_csv(self, mock_load, mock_authz, mock_get_user, mock_upload):
        """Test que POST /api/v1/upload acepta un CSV válido y lo persiste en la nube."""
        mock_get_user.return_value = "test_user_persistence@example.com"
        mock_upload.return_value = True  # nube disponible: fuente de verdad OK

        df = pd.DataFrame({"producto": ["A", "B"], "ventas": [100, 200]})
        mock_load.return_value = df

        # Mock para DataSource que se crea en BD
        mock_source = MagicMock()
        mock_source.id = 1
        mock_source.name = "test.csv"
        mock_source.type = "file"
        mock_source.url = os.path.join(DATA_SOURCES_DIR, "test_user.csv")

        def fake_add(obj):
            if hasattr(obj, 'id') and obj.id is None:
                obj.id = 1
            return obj

        self.mock_db.add.side_effect = fake_add
        self.mock_db.refresh.side_effect = lambda obj: setattr(obj, 'id', 1)

        csv_bytes = b"producto,ventas\nA,100\nB,200\n"
        response = self.client.post(
            "/api/v1/upload",
            files={"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")}
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("filename", body)
        self.assertIn("columns", body)
        self.assertEqual(body["rows"], 2)
        self.assertTrue(body["persisted"])
        # El objeto se subió a la nube (fuente de verdad) antes de guardar la fila
        mock_upload.assert_called_once()

    @patch('src.routers.data.upload_bytes')
    @patch('src.routers.data.get_authenticated_user')
    @patch('src.routers.data.check_authorization')
    @patch('src.routers.data.load_file_data')
    def test_upload_aborts_without_cloud(self, mock_load, mock_authz, mock_get_user, mock_upload):
        """Sin nube disponible la subida debe abortar con 503: nunca guardar una
        fuente que se perdería en el próximo reinicio (éxito falso prohibido)."""
        mock_get_user.return_value = "test_user_persistence@example.com"
        mock_upload.return_value = False  # bucket no configurado / caído

        df = pd.DataFrame({"producto": ["A"], "ventas": [100]})
        mock_load.return_value = df

        response = self.client.post(
            "/api/v1/upload",
            files={"file": ("test.csv", io.BytesIO(b"producto,ventas\nA,100\n"), "text/csv")}
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("no fue guardado", response.json()["detail"].lower())
        # No debe crearse ninguna fila DataSource (fuente fantasma prohibida)
        self.mock_db.add.assert_not_called()

    @patch('src.routers.data.get_authenticated_user')
    @patch('src.routers.data.check_authorization')
    @patch('src.routers.data.load_gsheets_data')
    def test_connect_gsheets_invalid_url(self, mock_gsheets, mock_authz, mock_get_user):
        """Test que POST /api/v1/connect-gsheets retorna 400 con URL inválida."""
        mock_get_user.return_value = "test_user_persistence@example.com"
        mock_gsheets.side_effect = Exception("No se pudo conectar")

        response = self.client.post("/api/v1/connect-gsheets", data={
            "url": "https://docs.google.com/spreadsheets/d/invalido"
        })
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
