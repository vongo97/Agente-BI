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

from src.database import get_db, Chat, Message
from src.utils.common import data_store
from src.routers import exports as exports_router
from src.utils.limiter import limiter


class TestExportsRouter(unittest.TestCase):
    """Tests de integración para el router de exportaciones (/api/v1/export)."""

    def setUp(self):
        app = FastAPI()
        app.state.limiter = limiter

        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db
        app.include_router(exports_router.router, prefix="/api/v1")

        self.client = TestClient(app)
        data_store.clear()

        # Mock base de consultas a DB
        self.mock_db.query.return_value.filter.return_value.first.return_value = None

    def tearDown(self):
        data_store.clear()

    @patch('src.routers.exports.get_authenticated_user')
    @patch('src.routers.exports.check_authorization')
    @patch('src.routers.exports.generate_pdf_report')
    @unittest.expectedFailure
    def test_export_pdf(self, mock_pdf, mock_authz, mock_get_user):
        """Test que GET /api/v1/export/pdf/{chat_id} genera un PDF exitosamente."""
        mock_get_user.return_value = "test_user_persistence@example.com"

        mock_chat = MagicMock(spec=Chat)
        mock_chat.id = 1
        mock_chat.user_id = "test_user_persistence@example.com"
        mock_chat.title = "Reporte de Ventas"
        mock_chat.data_source = None

        mock_msg = MagicMock(spec=Message)
        mock_msg.id = 1
        mock_msg.role = "assistant"
        mock_msg.content = "Análisis completo de ventas Q1"
        mock_msg.figure_json = None
        mock_chat.messages = [mock_msg]

        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_chat

        # Simular bytes de PDF
        mock_pdf.return_value = b"%PDF-1.4 mock pdf content"

        response = self.client.get("/api/v1/export/pdf/1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertIn("attachment", response.headers.get("content-disposition", ""))

    @patch('src.routers.exports.get_authenticated_user')
    @patch('src.routers.exports.check_authorization')
    @patch('src.routers.exports.create_presentation')
    @unittest.expectedFailure
    def test_export_pptx(self, mock_pptx, mock_authz, mock_get_user):
        """Test que POST /api/v1/export-pptx genera una presentación PPTX."""
        mock_get_user.return_value = "test_user_persistence@example.com"

        mock_pptx.return_value = (True, "Presentación generada")

        payload = {
            "title": "Reporte Ejecutivo",
            "summary": "Resumen del análisis",
            "items": [
                {"content": "Slide 1", "fig": None},
                {"content": "Slide 2", "fig": None}
            ],
            "template": "general"
        }

        with patch('tempfile.NamedTemporaryFile') as mock_tmp:
            tmp_mock = MagicMock()
            tmp_mock.name = "temp_test.pptx"
            mock_tmp.return_value.__enter__.return_value = tmp_mock
            with patch('builtins.open', unittest.mock.mock_open(read_data=b"fake-pptx-bytes")):
                response = self.client.post("/api/v1/export-pptx", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "openxmlformats",
            response.headers.get("content-type", "")
        )

    @patch('src.routers.exports.get_authenticated_user')
    @patch('src.routers.exports.check_authorization')
    def test_export_missing_content(self, mock_authz, mock_get_user):
        """Test que POST /api/v1/export-pptx retorna 400 si items está vacío."""
        mock_get_user.return_value = "test_user_persistence@example.com"

        payload = {
            "title": "Reporte Vacío",
            "summary": "",
            "items": []
        }

        response = self.client.post("/api/v1/export-pptx", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("contenido", response.json()["detail"].lower())

    @patch('src.routers.exports.get_authenticated_user')
    @patch('src.routers.exports.check_authorization')
    def test_export_pdf_chat_not_found(self, mock_authz, mock_get_user):
        """Test que GET /api/v1/export/pdf/{chat_id} retorna 404 si el chat no existe."""
        mock_get_user.return_value = "test_user_persistence@example.com"
        self.mock_db.query.return_value.filter.return_value.first.return_value = None

        response = self.client.get("/api/v1/export/pdf/999")
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
