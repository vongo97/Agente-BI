"""Regresión P-46: /data-sources y /sources no devuelven la `url` interna.

`url` en la tabla data_sources es la clave de nube de un archivo
(`data_sources/<md5(email)>/...`), la ruta del contenedor en modo legacy o la
cadena de conexión SQL (cifrada). El backend la usa para reconectar la sesión;
no tiene valor para la UI y exponerla facilita enumerar rutas de otros
despliegues. Este test fija el contrato: la representación pública no incluye
`url`, `user_id` ni credenciales.
"""
import sys
import os
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_bi.db")

from src.database import get_db  # noqa: E402
from src.routers import data as data_router  # noqa: E402
from src.utils.limiter import limiter  # noqa: E402

URL_INTERNA = "data_sources/9f86d081884c7d65/fuentes_ventas.csv"


def _fake_source(**overrides):
    base = dict(
        id=7,
        user_id="user@example.com",
        name="ventas.csv",
        type="file",
        url=URL_INTERNA,
        columns='["fecha", "importe"]',
        is_encrypted=True,
        size_bytes=1024,
        created_at=datetime(2026, 10, 30, 12, 0, 0) - timedelta(days=1),
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class TestSourceSerialization:
    def _client(self):
        app = FastAPI()
        app.state.limiter = limiter
        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db
        app.include_router(data_router.router, prefix="/api/v1")
        self.mock_db.query.return_value.filter.return_value.count.return_value = 0
        return TestClient(app)

    @patch("src.routers.data.check_authorization")
    @patch("src.routers.data.get_authenticated_user")
    def test_get_data_sources_sin_url(self, mock_get_user, mock_authz):
        mock_get_user.return_value = "user@example.com"
        client = self._client()
        self.mock_db.query.return_value.filter.return_value.all.return_value = [_fake_source()]
        resp = client.get("/api/v1/data-sources")
        assert resp.status_code == 200
        payload = resp.json()
        assert isinstance(payload, list) and len(payload) == 1
        item = payload[0]
        assert "url" not in item, item
        assert item["id"] == 7 and item["name"] == "ventas.csv" and item["type"] == "file"

    @patch("src.routers.data.check_authorization")
    @patch("src.routers.data.get_authenticated_user")
    def test_get_sources_sin_url(self, mock_get_user, mock_authz):
        mock_get_user.return_value = "user@example.com"
        client = self._client()
        self.mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            _fake_source(type="sql", url="gAAAAA-cadena-conexion-cifrada")
        ]
        resp = client.get("/api/v1/sources")
        assert resp.status_code == 200
        payload = resp.json()
        assert isinstance(payload, list) and len(payload) == 1
        item = payload[0]
        assert "url" not in item, item
        assert "gAAAAA" not in str(item)

    @patch("src.routers.data.check_authorization")
    @patch("src.routers.data.get_authenticated_user")
    def test_post_data_sources_respuesta_sin_url(self, mock_get_user, mock_authz):
        mock_get_user.return_value = "user@example.com"
        client = self._client()
        resp = client.post("/api/v1/data-sources", data={
            "name": "ventas.csv",
            "type": "file",
            "url": URL_INTERNA,
            "columns": '["fecha"]',
        })
        assert resp.status_code == 200, resp.text
        item = resp.json()
        assert "url" not in item, item
        assert URL_INTERNA not in str(item)
