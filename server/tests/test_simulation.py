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

from src.database import get_db, Simulation, SimulationAgent, SimulationMessage
from src.utils.common import data_store
from src.routers import simulation as sim_router
from src.utils.limiter import limiter


class TestSimulationRouter(unittest.TestCase):
    """Tests de integración para el router de simulación (/api/v1/simulation)."""

    def setUp(self):
        app = FastAPI()
        app.state.limiter = limiter

        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db
        app.include_router(sim_router.router, prefix="/api/v1")

        self.client = TestClient(app)
        data_store.clear()

        # Mock base de consultas a DB
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        self.mock_db.query.return_value.filter.return_value.all.return_value = []
        self.mock_db.query.return_value.filter.return_value.count.return_value = 0
        self.mock_db.query.return_value.order_by.return_value.all.return_value = []

    def tearDown(self):
        data_store.clear()

    @patch('src.routers.simulation.get_authenticated_user')
    @patch('src.routers.simulation.check_authorization')
    @patch('src.routers.simulation.process_simulation')
    def test_create_simulation_valid(self, mock_process, mock_authz, mock_get_user):
        """Test que POST /api/v1/simulation crea una simulación con datos válidos."""
        mock_get_user.return_value = "test_user_persistence@example.com"

        def fake_refresh(obj):
            if hasattr(obj, 'id') and not getattr(obj, 'id', None):
                obj.id = 1

        self.mock_db.add.side_effect = None
        self.mock_db.refresh.side_effect = fake_refresh

        payload = {
            "title": "Simulación de Mercado",
            "hypothesis": "¿Qué pasa si las ventas caen un 20%?",
            "selectedIds": [1],
            "apiKey": "fake_key_valid_123",
            "provider": "gemini",
            "numRounds": 3
        }

        response = self.client.post(
            "/api/v1/simulation",
            json=payload
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "started")
        self.assertIn("simulation_id", body)

    @patch('src.routers.simulation.get_authenticated_user')
    @patch('src.routers.simulation.check_authorization')
    def test_create_simulation_missing_title(self, mock_authz, mock_get_user):
        """Test que POST /api/v1/simulation retorna 422 si falta el campo title."""
        mock_get_user.return_value = "test_user_persistence@example.com"

        payload = {
            "hypothesis": "Impacto de inflación",
            "selectedIds": [1],
            "apiKey": "fake_key"
        }

        response = self.client.post(
            "/api/v1/simulation",
            json=payload
        )

        self.assertEqual(response.status_code, 422)

    @patch('src.routers.simulation.get_authenticated_user')
    @patch('src.routers.simulation.check_authorization')
    def test_list_simulations(self, mock_authz, mock_get_user):
        """Test que GET /api/v1/simulation retorna la lista de simulaciones."""
        mock_get_user.return_value = "test_user_persistence@example.com"

        mock_sim = MagicMock(spec=Simulation)
        mock_sim.id = 1
        mock_sim.title = "Test Sim"
        mock_sim.hypothesis = "Test hipótesis"
        mock_sim.status = "completed"
        mock_sim.provider = "gemini"
        mock_sim.current_round = 3
        mock_sim.result_report = "OK"
        mock_sim.created_at = None

        self.mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_sim]

        response = self.client.get("/api/v1/simulation")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    @patch('src.routers.simulation.get_authenticated_user')
    @patch('src.routers.simulation.check_authorization')
    def test_get_simulation_not_found(self, mock_authz, mock_get_user):
        """Test que GET /api/v1/simulation/999 retorna 404 si no existe."""
        mock_get_user.return_value = "test_user_persistence@example.com"
        self.mock_db.query.return_value.filter.return_value.first.return_value = None

        response = self.client.get("/api/v1/simulation/999")
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
