import unittest
import sys
import os
import types
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ["ENVIRONMENT"] = "development"
os.environ["RENDER"] = "false"
os.environ["AUTH_SECRET"] = "test-secret"

# --- Mocks de módulos opcionales (mismo patrón que test_dashboard.py) ---

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

# --- End setup ---

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.database import get_db, DataSource
from src.routers import reports as reports_router
from src.utils.common import data_store
from src.utils.limiter import limiter


class TestReportKpiSummary(unittest.TestCase):
    """P-23: el router de reports estaba implementado pero NUNCA se montaba
    en main.py, así que el endpoint /report/kpi-summary no existía y sus
    consumidores (KpiCards, AnomalyAlert) quedaban sin datos.

    Estos tests fijan el contrato del endpoint ya montado.
    """

    def setUp(self):
        limiter.reset()
        app = FastAPI()
        app.state.limiter = limiter

        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db
        app.include_router(reports_router.router, prefix="/api/v1")

        self.client = TestClient(app)
        data_store.clear()

        self.source = MagicMock(spec=DataSource)
        self.source.id = 7
        self.source.name = "ventas.csv"
        self.source.user_id = "test_user@example.com"

        self.mock_db.query.return_value.filter.return_value.first.return_value = self.source

    def tearDown(self):
        data_store.clear()

    def _seed_session(self):
        import pandas as pd
        # 20 filas: el Z-Score necesita muestra suficiente para que un único
        # valor extremo supere las 3σ (reports.py:71). Con 5 filas el propio
        # atípico infla la desviación estándar y su Z queda por debajo del
        # umbral — es una propiedad del método, no un fallo del endpoint.
        sales = [100, 110, 120, 130, 140, 150, 160, 170, 180, 190,
                 200, 210, 220, 230, 240, 250, 260, 270, 280, 5000]
        regions = ["Norte", "Sur", "Este", "Oeste"] * 5
        df = pd.DataFrame({
            "Region": regions,
            "Sales": sales,
            "Profit": [v / 10 for v in sales],
        })
        data_store["test_user@example.com_active"] = {
            "type": "file",
            "data": {"ventas": df},
            "sources": [],
        }

    @patch('src.routers.reports.get_authenticated_user')
    @patch('src.routers.reports.check_authorization')
    @patch('src.utils.common.ensure_user_session')
    def test_kpi_summary_returns_profile(self, mock_session, mock_authz, mock_get_user):
        """El endpoint devuelve el perfil del dataset con el contrato de KpiCards."""
        mock_get_user.return_value = "test_user@example.com"
        self._seed_session()
        mock_session.return_value = data_store["test_user@example.com_active"]

        response = self.client.post("/api/v1/report/kpi-summary", data={
            "data_source_id": "7"
        })
        self.assertEqual(response.status_code, 200)
        body = response.json()

        # Contrato exacto que consume KpiCards (client/src/components/KpiCards.tsx).
        for key in ("dataset", "columnas", "saturacion", "nicho_top",
                    "confianza", "completitud", "anomalias", "correlaciones_fuertes"):
            self.assertIn(key, body, f"Falta la clave '{key}' en la respuesta")

        self.assertEqual(body["dataset"]["nombre"], "ventas.csv")
        self.assertEqual(body["dataset"]["filas"], 20)
        self.assertEqual(body["dataset"]["columnas"], 3)
        self.assertEqual(body["columnas"]["numericas"], 2)
        self.assertEqual(body["columnas"]["categoricas"], 1)
        self.assertEqual(body["completitud"], 100.0)
        self.assertIn("ventas", body["dataset"]["nombre"].lower() + "ventas")

    @patch('src.routers.reports.get_authenticated_user')
    @patch('src.routers.reports.check_authorization')
    @patch('src.utils.common.ensure_user_session')
    def test_kpi_summary_detects_outlier(self, mock_session, mock_authz, mock_get_user):
        """El valor atípico (5000) se reporta en `anomalias` con su Z-Score.

        Ese array es lo que consume AnomalyAlert.
        """
        mock_get_user.return_value = "test_user@example.com"
        self._seed_session()
        mock_session.return_value = data_store["test_user@example.com_active"]

        response = self.client.post("/api/v1/report/kpi-summary", data={
            "data_source_id": "7"
        })
        self.assertEqual(response.status_code, 200)
        anomalias = response.json()["anomalias"]
        self.assertTrue(len(anomalias) > 0, "Se esperaba al menos una anomalía")
        self.assertEqual(anomalias[0]["columna"], "Sales")
        self.assertEqual(anomalias[0]["valor"], 5000)
        self.assertIn("severidad", anomalias[0])

    @patch('src.routers.reports.get_authenticated_user')
    @patch('src.routers.reports.check_authorization')
    def test_kpi_summary_unknown_source_returns_404(self, mock_authz, mock_get_user):
        """Una fuente que no es del usuario → 404 (no se filtra información)."""
        mock_get_user.return_value = "test_user@example.com"
        self.mock_db.query.return_value.filter.return_value.first.return_value = None

        response = self.client.post("/api/v1/report/kpi-summary", data={
            "data_source_id": "999"
        })
        self.assertEqual(response.status_code, 404)

    @patch('src.routers.reports.get_authenticated_user')
    @patch('src.routers.reports.check_authorization')
    @patch('src.utils.common.ensure_user_session')
    def test_kpi_summary_without_session_returns_400(self, mock_session, mock_authz, mock_get_user):
        """Sin datos en la sesión → 400 con mensaje accionable, no un 500."""
        mock_get_user.return_value = "test_user@example.com"
        mock_session.return_value = None

        response = self.client.post("/api/v1/report/kpi-summary", data={
            "data_source_id": "7"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("datos", response.json()["detail"].lower())


if __name__ == '__main__':
    unittest.main()
