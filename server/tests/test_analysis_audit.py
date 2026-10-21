import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ["ENVIRONMENT"] = "development"
os.environ["RENDER"] = "false"
os.environ["AUTH_SECRET"] = "test-secret"

# Igual que test_analysis.py: evitar dependencias opcionales del arranque.
pkce_mod = types.ModuleType("src.utils.pkce_storage_factory")
pkce_mod.PKCEStorageFactory = MagicMock
sys.modules.setdefault("src.utils.pkce_storage_factory", pkce_mod)
pkce_mid = types.ModuleType("src.utils.pkce_middleware")
pkce_mid.PKCEAuthMiddleware = MagicMock
sys.modules.setdefault("src.utils.pkce_middleware", pkce_mid)

from src.database import get_db
from src.engine.insight_auditor import AUDIT_MARKER, AuditError
from src.routers import analysis as analysis_router
from src.utils.common import data_store
from src.utils.limiter import limiter


class FakeSession:
    def __init__(self):
        self.added = []
        self._chat_id = 10
        self._message_id = 11

    def query(self, *args, **kwargs):
        query = MagicMock()
        query.filter.return_value.first.return_value = None
        return query

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        return None

    def rollback(self):
        return None

    def refresh(self, obj):
        if obj.__class__.__name__ == "Chat":
            obj.id = self._chat_id
        else:
            obj.id = self._message_id


class TestAuditEndpoint(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.state.limiter = limiter
        self.db = FakeSession()
        app.dependency_overrides[get_db] = lambda: self.db
        app.include_router(analysis_router.router, prefix="/api/v1")
        self.client = TestClient(app)
        data_store.clear()

    def tearDown(self):
        data_store.clear()

    def _data(self):
        return {
            "type": "file",
            "data": pd.DataFrame(
                {
                    "order_id": [f"O{i}" for i in range(12)],
                    "sales": [100.0] * 12,
                    "profit": [10.0] * 6 + [-20.0] * 6,
                    "discount": [0.0] * 6 + [0.4] * 6,
                    "region": ["Norte"] * 6 + ["Sur"] * 6,
                    "customer": ["Ana"] * 6 + ["Bob"] * 6,
                }
            ),
        }

    @patch("src.routers.analysis.get_authenticated_user")
    @patch("src.routers.analysis.check_authorization")
    @patch("src.routers.analysis.get_user_data")
    def test_audit_does_not_require_api_key(self, mock_get_data, mock_authz, mock_get_user):
        mock_get_user.return_value = "test_user_persistence@example.com"
        mock_get_data.return_value = self._data()

        with patch("src.utils.common.promote_active_session"):
            response = self.client.post("/api/v1/analyze/audit")

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertIn("analysis", body)
        self.assertIn("audit", body)
        self.assertGreaterEqual(len(body["audit"]["insights"]), 1)
        self.assertIn("profile", body["audit"])
        self.assertTrue(body["figure"])
        self.assertEqual(body["chat_id"], 10)
        self.assertEqual(body["message_id"], 11)

        message = next(obj for obj in self.db.added if obj.__class__.__name__ == "Message")
        self.assertTrue(message.analysis_code.startswith(AUDIT_MARKER))

    @patch("src.routers.analysis.get_authenticated_user")
    @patch("src.routers.analysis.check_authorization")
    @patch("src.routers.analysis.get_user_data")
    def test_audit_rejects_sql_mode(self, mock_get_data, mock_authz, mock_get_user):
        mock_get_user.return_value = "test_user_persistence@example.com"
        mock_get_data.return_value = {"type": "sql", "data": object()}

        response = self.client.post("/api/v1/analyze/audit")

        self.assertEqual(response.status_code, 400)
        self.assertIn("SQL", response.json()["detail"])

    @patch("src.routers.analysis.get_authenticated_user")
    @patch("src.routers.analysis.check_authorization")
    @patch("src.routers.analysis.get_user_data")
    def test_audit_returns_actionable_error_for_bad_data(self, mock_get_data, mock_authz, mock_get_user):
        mock_get_user.return_value = "test_user_persistence@example.com"
        mock_get_data.return_value = self._data()

        with patch("src.routers.analysis.build_audit", side_effect=AuditError("Faltan ventas utilizables.")):
            response = self.client.post("/api/v1/analyze/audit")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Faltan ventas utilizables.")

    @patch("src.routers.analysis.get_authenticated_user")
    @patch("src.routers.analysis.check_authorization")
    @patch("src.routers.analysis.get_user_data")
    def test_audit_requires_loaded_data(self, mock_get_data, mock_authz, mock_get_user):
        mock_get_user.return_value = "test_user_persistence@example.com"
        mock_get_data.return_value = None

        with patch("src.routers.analysis.ensure_user_session", return_value=None):
            response = self.client.post("/api/v1/analyze/audit")

        self.assertEqual(response.status_code, 400)
        self.assertIn("datos cargados", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
