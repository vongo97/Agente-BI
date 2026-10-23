import unittest
import sys
import os
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
from src.utils.common import data_store, SESSIONS_DIR
from src.routers import analysis as analysis_router
from src.utils.limiter import limiter
import hashlib
import pandas as pd

# Pickle de sesión que otros tests (upload/analyze) dejan en disco para este
# usuario. Sin limpiarlo, `ensure_user_session` lo recoge y tests como
# `test_analyze_no_data_source` fallan según el orden de ejecución.
_TEST_USER_SAFE = hashlib.md5(b"test_user_persistence@example.com").hexdigest()


def _clean_session_pickles():
    import glob
    for path in glob.glob(os.path.join(SESSIONS_DIR, f"{_TEST_USER_SAFE}*.pkl")):
        try:
            os.remove(path)
        except OSError:
            pass


class TestAnalysisRouter(unittest.TestCase):
    """Tests de integración para el router de análisis (/api/v1/analyze)."""

    def setUp(self):
        app = FastAPI()
        app.state.limiter = limiter

        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db
        app.include_router(analysis_router.router, prefix="/api/v1")

        self.client = TestClient(app)

        # Limpiar data_store antes de cada test
        data_store.clear()
        _clean_session_pickles()

        # Mock del query de Chat/DataSource para que no falle
        self.mock_db.query.return_value.filter.return_value.first.return_value = None

    def tearDown(self):
        data_store.clear()
        _clean_session_pickles()

    @patch('src.routers.analysis.get_authenticated_user')
    @patch('src.routers.analysis.check_authorization')
    def test_analyze_requires_api_key(self, mock_authz, mock_get_user):
        """Test que POST /api/v1/analyze retorna error 400 con api_key inválida."""
        mock_get_user.return_value = "test_user_persistence@example.com"
        response = self.client.post("/api/v1/analyze", data={
            "query": "analiza las ventas",
            "api_key": "short",
            "provider": "gemini"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("clave", response.json()["detail"].lower())

    @patch('src.routers.analysis.get_authenticated_user')
    @patch('src.routers.analysis.check_authorization')
    def test_analyze_missing_query(self, mock_authz, mock_get_user):
        """Test que POST /api/v1/analyze retorna 422 si falta el campo query."""
        mock_get_user.return_value = "test_user_persistence@example.com"
        response = self.client.post("/api/v1/analyze", data={
            "api_key": "fake_key_12345"
        })
        self.assertEqual(response.status_code, 422)

    @patch('src.routers.analysis.get_authenticated_user')
    @patch('src.routers.analysis.check_authorization')
    @patch('src.routers.analysis.validate_data_quality')
    @patch('src.routers.analysis.get_user_data')
    @patch('src.routers.analysis.analyze_data')
    def test_analyze_successful_flow(self, mock_analyze, mock_get_data,
                                     mock_quality, mock_authz, mock_get_user):
        """Test que valida el flujo exitoso de /api/v1/analyze con datos mock."""
        mock_get_user.return_value = "test_user_persistence@example.com"
        mock_get_data.return_value = {
            "type": "file",
            "data": {"dataset": pd.DataFrame({"x": [1, 2]})}
        }
        mock_quality.return_value = (True, "OK")

        # Simular respuesta del analizador
        mock_fig = MagicMock()
        mock_fig.to_json.return_value = '{"data": []}'
        mock_analyze.return_value = (
            "Informe estratégico basado en los datos.",
            mock_fig,
            "```python\nprint('done')\n```"
        )

        response = self.client.post("/api/v1/analyze", data={
            "query": "analiza las ventas por producto",
            "api_key": "fake_gemini_key_valid",
            "provider": "gemini"
        })

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("analysis", body)
        self.assertIn("Informe estratégico", body["analysis"])

    @patch('src.routers.analysis.get_authenticated_user')
    @patch('src.routers.analysis.check_authorization')
    @patch('src.routers.analysis.get_user_data')
    def test_analyze_no_data_source(self, mock_get_data, mock_authz, mock_get_user):
        """Test que POST /api/v1/analyze retorna 400 si no hay datos cargados."""
        mock_get_user.return_value = "test_user_persistence@example.com"
        mock_get_data.return_value = None

        response = self.client.post("/api/v1/analyze", data={
            "query": "analiza las ventas",
            "api_key": "fake_gemini_key_valid",
            "provider": "gemini"
        })

        self.assertEqual(response.status_code, 400)
        self.assertIn("datos cargados", response.json()["detail"].lower())


if __name__ == '__main__':
    unittest.main()
