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

from src.database import get_db, Chat, Message, DashboardItem
from src.utils.common import data_store
from src.routers import dashboard as dashboard_router
from src.utils.limiter import limiter


class TestDashboardRouter(unittest.TestCase):
    """Tests de integración para el router de dashboard (/api/v1/dashboard)."""

    def setUp(self):
        app = FastAPI()
        app.state.limiter = limiter

        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db
        app.include_router(dashboard_router.router, prefix="/api/v1")

        self.client = TestClient(app)
        data_store.clear()

        # Mock base de consultas a DB
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        self.mock_db.query.return_value.filter.return_value.all.return_value = []

    def tearDown(self):
        data_store.clear()

    @patch('src.routers.dashboard.get_authenticated_user')
    @patch('src.routers.dashboard.check_authorization')
    def test_pin_to_dashboard(self, mock_authz, mock_get_user):
        """Test que POST /api/v1/dashboard/pin ancla un mensaje al dashboard."""
        mock_get_user.return_value = "test_user_persistence@example.com"

        mock_chat = MagicMock(spec=Chat)
        mock_chat.id = 1
        mock_chat.user_id = "test_user_persistence@example.com"
        mock_chat.title = "Test Chat"

        mock_message = MagicMock(spec=Message)
        mock_message.id = 1
        mock_message.chat_id = 1
        mock_message.content = "Análisis de ventas"
        mock_message.figure_json = None
        mock_message.analysis_code = None

        def filter_side_effect(*args, **kwargs):
            result = MagicMock()
            if len(args) > 0:
                model_class = args[0]
                if model_class == Chat:
                    result.first.return_value = mock_chat
                elif model_class == Message:
                    result.first.return_value = mock_message
                elif model_class == DashboardItem:
                    result.first.return_value = None
                else:
                    result.first.return_value = None
            return result

        self.mock_db.query.side_effect = filter_side_effect

        response = self.client.post("/api/v1/dashboard/pin", data={
            "chat_id": 1,
            "message_id": 1
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn("Anclado", response.json()["message"])

    @patch('src.routers.dashboard.get_authenticated_user')
    @patch('src.routers.dashboard.check_authorization')
    def test_get_dashboard_list(self, mock_authz, mock_get_user):
        """Test que GET /api/v1/dashboard retorna la lista de items anclados."""
        mock_get_user.return_value = "test_user_persistence@example.com"

        mock_item = MagicMock(spec=DashboardItem)
        mock_item.id = 1

        mock_chat = MagicMock()
        mock_chat.title = "Chat de prueba"

        mock_message = MagicMock()
        mock_message.content = "Contenido del análisis"
        mock_message.figure_json = None

        mock_item.chat = mock_chat
        mock_item.message = mock_message
        mock_item.pinned_at = None

        self.mock_db.query.return_value.filter.return_value.all.return_value = [mock_item]

        response = self.client.get("/api/v1/dashboard")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIsInstance(body, list)
        self.assertGreater(len(body), 0)
        self.assertIn("chat_title", body[0])

    @patch('src.routers.dashboard.get_authenticated_user')
    @patch('src.routers.dashboard.check_authorization')
    def test_delete_dashboard_item(self, mock_authz, mock_get_user):
        """Test que DELETE /api/v1/dashboard/{item_id} elimina un item del dashboard."""
        mock_get_user.return_value = "test_user_persistence@example.com"

        mock_item = MagicMock(spec=DashboardItem)
        mock_item.id = 1
        mock_item.user_id = "test_user_persistence@example.com"

        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_item

        response = self.client.delete("/api/v1/dashboard/1")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Eliminado", response.json()["message"])

    @patch('src.routers.dashboard.get_authenticated_user')
    @patch('src.routers.dashboard.check_authorization')
    def test_delete_dashboard_item_not_found(self, mock_authz, mock_get_user):
        """Test que DELETE /api/v1/dashboard/{item_id} retorna 404 si no existe."""
        mock_get_user.return_value = "test_user_persistence@example.com"
        self.mock_db.query.return_value.filter.return_value.first.return_value = None

        response = self.client.delete("/api/v1/dashboard/999")
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
