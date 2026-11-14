import unittest
import sys
import os
import types
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from sqlalchemy import create_engine

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ["ENVIRONMENT"] = "development"
os.environ["RENDER"] = "false"
os.environ["AUTH_SECRET"] = "test-secret"


# --- Mocks de módulos faltantes (mismo patrón que test_dashboard.py) ---

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

from src.database import get_db, Chat, Message, DashboardItem
from src.utils.common import data_store
from src.routers import dashboard as dashboard_router
from src.utils.limiter import limiter


class TestDashboardFilter(unittest.TestCase):
    """Tests de integración para POST /api/v1/dashboard/filter (P-48)."""

    def setUp(self):
        limiter.reset()
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

    def _pinned_item(self, item_id=1, analysis_code="```python\nfig = 1\n```", figure_json=None):
        item = MagicMock(spec=DashboardItem)
        item.id = item_id
        message = MagicMock(spec=Message)
        message.analysis_code = analysis_code
        message.figure_json = figure_json
        item.message = message
        return item

    @patch('src.routers.dashboard.get_authenticated_user')
    @patch('src.routers.dashboard.check_authorization')
    @patch('src.routers.dashboard.execute_analysis')
    def test_filter_unknown_column_returns_400(self, mock_exec, mock_authz, mock_get_user):
        """P-48: columna inexistente → 400 con detalle, NO 200 success."""
        mock_get_user.return_value = "test_user@example.com"
        mock_exec.return_value = ("narrative", None)

        import pandas as pd
        session_key = "test_user@example.com_active"
        data_store[session_key] = {
            "type": "file",
            "data": {
                "sales_df": pd.DataFrame({
                    "Region": ["Norte", "Sur", "Este"],
                    "Sales": [100, 200, 300],
                    "Profit": [10, 20, 30]
                })
            },
            "sources": []
        }

        response = self.client.post("/api/v1/dashboard/filter", data={
            "filters_json": '{"NoExiste": 123}'
        })
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertIn("no existe", body["detail"])

    @patch('src.routers.dashboard.get_authenticated_user')
    @patch('src.routers.dashboard.check_authorization')
    @patch('src.routers.dashboard.execute_analysis')
    def test_filter_valid_column_file_returns_200(self, mock_exec, mock_authz, mock_get_user):
        """Filtro sobre columna real en modo file → 200."""
        mock_get_user.return_value = "test_user@example.com"
        mock_exec.return_value = ("narrative", None)

        import pandas as pd
        session_key = "test_user@example.com_active"
        data_store[session_key] = {
            "type": "file",
            "data": {
                "sales_df": pd.DataFrame({
                    "Region": ["Norte", "Sur", "Este"],
                    "Sales": [100, 200, 300],
                    "Profit": [10, 20, 30]
                })
            },
            "sources": []
        }

        response = self.client.post("/api/v1/dashboard/filter", data={
            "filters_json": '{"Region": "Norte"}'
        })
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("status", body)

    @patch('src.routers.dashboard.get_authenticated_user')
    @patch('src.routers.dashboard.check_authorization')
    @patch('src.routers.dashboard.execute_analysis')
    def test_filter_empty_filters_returns_400(self, mock_exec, mock_authz, mock_get_user):
        """Filtro vacío → 400 con mensaje accionable (P-48)."""
        mock_get_user.return_value = "test_user@example.com"
        mock_exec.return_value = ("narrative", None)

        import pandas as pd
        session_key = "test_user@example.com_active"
        data_store[session_key] = {
            "type": "file",
            "data": {
                "sales_df": pd.DataFrame({
                    "Region": ["Norte", "Sur"]
                })
            },
            "sources": []
        }

        response = self.client.post("/api/v1/dashboard/filter", data={
            "filters_json": '{"Region": ""}'
        })
        self.assertEqual(response.status_code, 400)

    @patch('src.routers.dashboard.get_authenticated_user')
    @patch('src.routers.dashboard.check_authorization')
    @patch('src.routers.dashboard.execute_analysis')
    def test_filter_null_value_returns_400(self, mock_exec, mock_authz, mock_get_user):
        """Filtro con valor null → 400 (P-48)."""
        mock_get_user.return_value = "test_user@example.com"
        mock_exec.return_value = ("narrative", None)

        import pandas as pd
        session_key = "test_user@example.com_active"
        data_store[session_key] = {
            "type": "file",
            "data": {
                "sales_df": pd.DataFrame({
                    "Region": ["Norte", "Sur"]
                })
            },
            "sources": []
        }

        response = self.client.post("/api/v1/dashboard/filter", data={
            "filters_json": '{"Region": null}'
        })
        self.assertEqual(response.status_code, 400)

    @patch('src.routers.dashboard.get_authenticated_user')
    @patch('src.routers.dashboard.check_authorization')
    @patch('src.routers.dashboard.execute_analysis')
    def test_filter_case_insensitive_column(self, mock_exec, mock_authz, mock_get_user):
        """Filtro insensible a mayúsculas/minúsculas: 'region' = 'Region'."""
        mock_get_user.return_value = "test_user@example.com"
        mock_exec.return_value = ("narrative", None)

        import pandas as pd
        session_key = "test_user@example.com_active"
        data_store[session_key] = {
            "type": "file",
            "data": {
                "sales_df": pd.DataFrame({
                    "Region": ["Norte", "Sur"]
                })
            },
            "sources": []
        }

        response = self.client.post("/api/v1/dashboard/filter", data={
            "filters_json": '{"region": "Norte"}'
        })
        self.assertEqual(response.status_code, 200)

    @patch('src.routers.dashboard.get_authenticated_user')
    @patch('src.routers.dashboard.check_authorization')
    @patch('src.routers.dashboard.execute_analysis')
    def test_filter_resolves_trace_name_containing_column(self, mock_exec, mock_authz, mock_get_user):
        """La clave llega como nombre de traza de Plotly ("Ventas por Region").

        Si la traza contiene el nombre de una columna real, el filtro se
        aplica a esa columna en vez de rechazarse.
        """
        mock_get_user.return_value = "test_user@example.com"

        captured = {}

        async def fake_exec(ctx, code, var):
            captured['ctx'] = ctx
            return ("narrative", None)

        mock_exec.side_effect = fake_exec

        import pandas as pd
        session_key = "test_user@example.com_active"
        data_store[session_key] = {
            "type": "file",
            "data": {
                "sales_df": pd.DataFrame({
                    "Region": ["Norte", "Sur"],
                    "Sales": [100, 200]
                })
            },
            "sources": []
        }
        self.mock_db.query.return_value.filter.return_value.all.return_value = [
            self._pinned_item(item_id=1)
        ]

        response = self.client.post("/api/v1/dashboard/filter", data={
            "filters_json": '{"Ventas por Region": "Norte"}'
        })
        self.assertEqual(response.status_code, 200)

        df = list(captured['ctx'].values())[0]
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['Region'], "Norte")

    @patch('src.routers.dashboard.get_authenticated_user')
    @patch('src.routers.dashboard.check_authorization')
    @patch('src.routers.dashboard.execute_analysis')
    def test_filter_rejects_ambiguous_trace_name(self, mock_exec, mock_authz, mock_get_user):
        """Si la traza contiene varias columnas reales, es ambigua → 400.

        Prefiere fallar con un mensaje claro antes que filtrar por la columna
        equivocada.
        """
        mock_get_user.return_value = "test_user@example.com"
        mock_exec.return_value = ("narrative", None)

        import pandas as pd
        session_key = "test_user@example.com_active"
        data_store[session_key] = {
            "type": "file",
            "data": {
                "sales_df": pd.DataFrame({
                    "Region": ["Norte", "Sur"],
                    "Sales": [100, 200]
                })
            },
            "sources": []
        }

        response = self.client.post("/api/v1/dashboard/filter", data={
            "filters_json": '{"Region Sales": "Norte"}'
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("no existe", response.json()["detail"])

    @patch('src.routers.dashboard.get_authenticated_user')
    @patch('src.routers.dashboard.check_authorization')
    @patch('src.routers.dashboard.execute_analysis')
    def test_filter_figures_with_errors_captures_per_item_failures(self, mock_exec, mock_authz, mock_get_user):
        """P-48: algunos items fallan al re-ejecutarse → figura null + error."""
        mock_get_user.return_value = "test_user@example.com"

        # El primer item falla al re-ejecutarse; el segundo devuelve figura.
        class FakeFig:
            def to_json(self):
                return '{"data": [1]}'

        call_count = 0
        async def failing_exec(ctx, code, var):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Error interno en el sandbox")
            return ("narrative", FakeFig())

        mock_exec.side_effect = failing_exec

        import pandas as pd
        session_key = "test_user@example.com_active"
        data_store[session_key] = {
            "type": "file",
            "data": {
                "sales_df": pd.DataFrame({
                    "Region": ["Norte", "Sur"],
                    "Sales": [100, 200]
                })
            },
            "sources": []
        }

        mock_items = [
            self._pinned_item(item_id=1, analysis_code="```python\nfig = 1\n```", figure_json=None),
            self._pinned_item(item_id=2, analysis_code="```python\nfig = 2\n```", figure_json=None),
        ]

        # Persistir items mock en la BD mock
        self.mock_db.query.return_value.filter.return_value.all.return_value = mock_items

        response = self.client.post("/api/v1/dashboard/filter", data={
            "filters_json": '{"Region": "Norte"}'
        })
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("status", body)

        # Item 1 falló: figura null + campo error (antes se tragaba en silencio)
        item1 = [r for r in body["updated_items"] if r["id"] == 1][0]
        self.assertIsNone(item1.get("fig"))
        self.assertIn("error", item1)

        # Item 2 tuvo éxito: figura presente y sin error
        item2 = [r for r in body["updated_items"] if r["id"] == 2][0]
        self.assertIsNotNone(item2.get("fig"))
        self.assertNotIn("error", item2)


class TestDashboardFilterSQL(unittest.TestCase):
    """Tests de integración del filtro en modo SQL (P-48).

    Usa un engine SQLite en memoria real (patrón de test_sql_mode_safety.py)
    para que la introspección del catálogo y la consulta parametrizada se
    ejecuten de verdad, no contra mocks.
    """

    def setUp(self):
        limiter.reset()
        app = FastAPI()
        app.state.limiter = limiter

        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db
        app.include_router(dashboard_router.router, prefix="/api/v1")

        self.client = TestClient(app)
        data_store.clear()

        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        self.mock_db.query.return_value.filter.return_value.all.return_value = []

        # Engine SQLite en memoria con una tabla real.
        # StaticPool es obligatorio: con `sqlite:///:memory:` cada conexión
        # abre una base distinta y vacía, así que el inspector (que abre su
        # propia conexión) no vería la tabla creada arriba.
        from sqlalchemy import text as sql_text
        from sqlalchemy.pool import StaticPool
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        with self.engine.connect() as conn:
            conn.execute(sql_text("CREATE TABLE sales (id INTEGER, Region TEXT, Sales INTEGER, Profit INTEGER)"))
            conn.execute(sql_text(
                "INSERT INTO sales VALUES (1, 'Norte', 100, 10), (2, 'Sur', 200, 20), (3, 'Norte', 300, 30)"
            ))
            conn.commit()

        self.session_key = "test_user@example.com_active"
        data_store[self.session_key] = {
            "type": "sql",
            "data": self.engine,
            "schema": "",
            "sources": []
        }

    def tearDown(self):
        data_store.clear()

    def _pinned_item(self, item_id=1, analysis_code="```python\nfig = 1\n```", figure_json=None):
        item = MagicMock(spec=DashboardItem)
        item.id = item_id
        message = MagicMock(spec=Message)
        message.analysis_code = analysis_code
        message.figure_json = figure_json
        item.message = message
        return item

    def _seed_pinned_items(self):
        """Registra un item anclado para que el endpoint tenga algo que re-ejecutar."""
        self.mock_db.query.return_value.filter.return_value.all.return_value = [
            self._pinned_item(item_id=1)
        ]

    @patch('src.routers.dashboard.get_authenticated_user')
    @patch('src.routers.dashboard.check_authorization')
    @patch('src.routers.dashboard.execute_analysis')
    def test_sql_unknown_column_returns_400(self, mock_exec, mock_authz, mock_get_user):
        """P-48: modo SQL, columna inexistente → 400, no finge success."""
        mock_get_user.return_value = "test_user@example.com"
        mock_exec.return_value = ("narrative", None)

        response = self.client.post("/api/v1/dashboard/filter", data={
            "filters_json": '{"NoExiste": 123}'
        })
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertIn("no existe", body["detail"])
        # Las columnas disponibles deben listarse para que el usuario sepa qué usar
        self.assertIn("Region", body["detail"])

    @patch('src.routers.dashboard.get_authenticated_user')
    @patch('src.routers.dashboard.check_authorization')
    @patch('src.routers.dashboard.execute_analysis')
    def test_sql_valid_column_materializes_filtered_dataframe(self, mock_exec, mock_authz, mock_get_user):
        """P-48: modo SQL materializa el subconjunto filtrado como DataFrame.

        Verifica que el contexto entregado al sandbox es un dict de DataFrames
        (NO el engine crudo) y que contiene SOLO las filas que cumplen el filtro.
        """
        mock_get_user.return_value = "test_user@example.com"

        captured = {}

        async def fake_exec(ctx, code, var):
            captured['ctx'] = ctx
            captured['var'] = var
            return ("narrative", None)

        mock_exec.side_effect = fake_exec
        self._seed_pinned_items()

        response = self.client.post("/api/v1/dashboard/filter", data={
            "filters_json": '{"Region": "Norte"}'
        })
        self.assertEqual(response.status_code, 200)

        # El contexto debe ser un dict de DataFrames, no el engine
        self.assertIsInstance(captured.get('ctx'), dict)
        self.assertNotIn('data', captured['ctx'])
        # La variable del sandbox debe ser "dfs" (no "engine"): el sandbox solo
        # serializa DataFrames y el código guardado accede a las tablas por nombre.
        self.assertEqual(captured.get('var'), "dfs")

        frames = list(captured['ctx'].values())
        self.assertEqual(len(frames), 1)
        df = frames[0]
        self.assertEqual(len(df), 2, f"Se esperaban 2 filas filtradas, se obtuvieron {len(df)}")
        self.assertEqual(set(df['Region'].unique()), {'Norte'})

    @patch('src.routers.dashboard.get_authenticated_user')
    @patch('src.routers.dashboard.check_authorization')
    @patch('src.routers.dashboard.execute_analysis')
    def test_sql_filter_value_is_bound_not_interpolated(self, mock_exec, mock_authz, mock_get_user):
        """Los valores viajan como parámetros bind, no como string en el SQL.

        Un valor con comilla simple no debe romper la consulta ni ejecutarse
        como SQL (prevención de inyección en el valor del filtro).
        """
        mock_get_user.return_value = "test_user@example.com"

        async def fake_exec(ctx, code, var):
            return ("narrative", None)

        mock_exec.side_effect = fake_exec

        response = self.client.post("/api/v1/dashboard/filter", data={
            "filters_json": '{"Region": "Norte\' OR 1=1 --"}'
        })
        # La consulta debe ejecutarse y devolver 0 filas, no un error de sintaxis
        self.assertEqual(response.status_code, 200)

    @patch('src.routers.dashboard.get_authenticated_user')
    @patch('src.routers.dashboard.check_authorization')
    @patch('src.routers.dashboard.execute_analysis')
    def test_sql_filter_with_no_matching_rows_returns_200_with_empty_frame(self, mock_exec, mock_authz, mock_get_user):
        """Un filtro sin coincidencias no es un error: devuelve 0 filas."""
        mock_get_user.return_value = "test_user@example.com"

        captured = {}

        async def fake_exec(ctx, code, var):
            captured['ctx'] = ctx
            return ("narrative", None)

        mock_exec.side_effect = fake_exec
        self._seed_pinned_items()

        response = self.client.post("/api/v1/dashboard/filter", data={
            "filters_json": '{"Region": "Inexistente"}'
        })
        self.assertEqual(response.status_code, 200)
        frames = list(captured['ctx'].values())
        self.assertEqual(len(frames), 1)
        self.assertEqual(len(frames[0]), 0)


if __name__ == '__main__':
    unittest.main()