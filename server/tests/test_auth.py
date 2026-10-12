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

from src.database import get_db, UserConfig
from src.utils.common import data_store
from src.routers import auth as auth_router
from src.utils.limiter import limiter


class TestAuthRouter(unittest.TestCase):
    """Tests de integración para el router de autenticación y configuración (/api/v1/auth)."""

    def setUp(self):
        app = FastAPI()
        app.state.limiter = limiter

        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db
        app.include_router(auth_router.router, prefix="/api/v1")

        self.client = TestClient(app)
        data_store.clear()

        # Mock base de consultas a DB
        self.mock_db.query.return_value.filter.return_value.first.return_value = None

    def tearDown(self):
        data_store.clear()

    @patch('src.routers.auth.get_authenticated_user')
    @patch('src.routers.auth.check_authorization')
    @patch('src.routers.auth.validate_api_key')
    def test_validate_key_valid(self, mock_validate, mock_authz, mock_get_user):
        """POST /api/v1/validate-key devuelve valid=True cuando el proveedor acepta."""
        mock_get_user.return_value = "test_user_persistence@example.com"
        mock_validate.return_value = (True, None)

        response = self.client.post("/api/v1/validate-key", data={
            "api_key": "AIzaSyTestValidKey123",
            "provider": "gemini"
        })

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["valid"])
        self.assertIsNone(body["error"])

    @patch('src.routers.auth.get_authenticated_user')
    @patch('src.routers.auth.check_authorization')
    @patch('src.routers.auth.validate_api_key')
    def test_validate_key_invalid(self, mock_validate, mock_authz, mock_get_user):
        """POST /api/v1/validate-key devuelve valid=False y explica el motivo."""
        mock_get_user.return_value = "test_user_persistence@example.com"
        mock_validate.return_value = (False, "API key invalida")

        response = self.client.post("/api/v1/validate-key", data={
            "api_key": "key_invalida",
            "provider": "gemini"
        })

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["valid"])
        self.assertTrue(body["error"])

    def test_validate_key_detecta_otro_proveedor(self):
        """Una clave de OpenAI pegada en el campo de Gemini debe avisar del mismatch."""
        from src.engine.providers import detect_provider
        self.assertEqual(detect_provider("sk-proj-abc123def456ghi789"), "openai")

    @patch('src.routers.auth.get_authenticated_user')
    @patch('src.routers.auth.check_authorization')
    def test_set_user_config(self, mock_authz, mock_get_user):
        """Test que POST /api/v1/user-config guarda la configuración del usuario."""
        mock_get_user.return_value = "test_user_persistence@example.com"

        mock_user_config = MagicMock(spec=UserConfig)
        mock_user_config.user_id = "test_user_persistence@example.com"
        mock_user_config.gemini_key = None
        mock_user_config.mistral_key = None
        mock_user_config.gamma_key = None
        mock_user_config.groq_key = None
        mock_user_config.preferred_provider = "gemini"
        mock_user_config.temperature = 0.2
        mock_user_config.anomaly_sensitivity = 2.5
        mock_user_config.magic_clean_strategy = "remove"
        mock_user_config.currency_format = "USD"
        mock_user_config.date_format = "DD/MM/YYYY"
        mock_user_config.brand_color = "#2dd4bf"
        mock_user_config.brand_logo_url = ""
        mock_user_config.report_org_name = "VEKTRA BI"
        mock_user_config.report_footer_text = "Confidencial - Solo uso interno"
        mock_user_config.pdf_orientation = "portrait"
        mock_user_config.pdf_include_data_table = True
        mock_user_config.chart_theme = "neon"

        self.mock_db.query.return_value.filter.return_value.first.return_value = None

        response = self.client.post("/api/v1/user-config", data={
            "preferred_provider": "mistral",
            "temperature": 0.5
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn("guardada", response.json()["message"].lower())

    @patch('src.routers.auth.get_authenticated_user')
    @patch('src.routers.auth.check_authorization')
    @patch('src.routers.auth.decrypt_key')
    def test_get_user_config_with_encrypted_key(self, mock_decrypt, mock_authz, mock_get_user):
        """Test que GET /api/v1/user-config retorna la llave cifrada enmascarada."""
        mock_get_user.return_value = "test_user_persistence@example.com"

        mock_config = MagicMock(spec=UserConfig)
        mock_config.user_id = "test_user_persistence@example.com"
        mock_config.gemini_key = "gAAAAAB_TEST_ENCRYPTED_KEY"
        mock_config.mistral_key = None
        mock_config.gamma_key = None
        mock_config.groq_key = None
        mock_config.preferred_provider = "gemini"
        mock_config.temperature = 0.3
        mock_config.anomaly_sensitivity = 2.5
        mock_config.magic_clean_strategy = "remove"
        mock_config.currency_format = "USD"
        mock_config.date_format = "DD/MM/YYYY"
        mock_config.brand_color = "#2dd4bf"
        mock_config.brand_logo_url = ""
        mock_config.report_org_name = "VEKTRA BI"
        mock_config.report_footer_text = "Confidencial - Solo uso interno"
        mock_config.pdf_orientation = "portrait"
        mock_config.pdf_include_data_table = True
        mock_config.chart_theme = "neon"

        mock_decrypt.return_value = "AIzaSyRealDecryptedKey123"

        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_config

        response = self.client.get("/api/v1/user-config")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("gemini_key", body)
        # El key debería estar enmascarado (xxxx...xxxx)
        self.assertNotIn("AIzaSyRealDecryptedKey123", body["gemini_key"])


if __name__ == '__main__':
    unittest.main()
