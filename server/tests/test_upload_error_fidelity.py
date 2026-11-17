"""P-76 · El error de /upload no puede culpar al archivo de un fallo del servidor.

Reproducción del bug reportado en pruebas manuales: al subir un CSV válido el
servidor devolvía

    HTTP 500 {"detail": "Error en el servidor al procesar el archivo. Por favor
                          verifica que el formato sea válido."}

Ese mensaje es una **mentira** cuando el fallo no es del archivo: el `except
Exception` genérico de `upload_file` se comía el fallo real de la base de datos
(`db.commit()`) y lo reportaba como "formato inválido". El usuario reformateaba
un CSV correcto una y otra vez mientras el servidor era el que estaba roto.

Este test fija tres cosas:

1. Un fallo de la BD devuelve **503** y dice que el archivo es válido.
2. Un fallo inesperado que no sea de la BD tampoco culpa al formato.
3. La BD se hace rollback (si no, la sesión de SQLAlchemy queda envenenada y el
   siguiente request hereda el fallo con ``PendingRollbackError``).
"""
import os
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ["ENVIRONMENT"] = "development"
os.environ["RENDER"] = "false"
os.environ["AUTH_SECRET"] = "test-secret"

# Evitar dependencias opcionales del arranque (mismo patrón que test_upload_encryption).
pkce_mod = types.ModuleType("src.utils.pkce_storage_factory")
pkce_mod.PKCEStorageFactory = MagicMock
sys.modules.setdefault("src.utils.pkce_storage_factory", pkce_mod)
pkce_mid = types.ModuleType("src.utils.pkce_middleware")
pkce_mid.PKCEAuthMiddleware = MagicMock
sys.modules.setdefault("src.utils.pkce_middleware", pkce_mid)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import src.utils.common as common  # noqa: E402
from src.database import get_db  # noqa: E402
from src.routers import data as data_router  # noqa: E402
from src.utils.limiter import limiter  # noqa: E402

_CSV = b"col_a,col_b\n1,2\n3,4\n5,6\n"


class FakeSession:
    """Sesión de BD falsa que puede fallar al hacer commit."""

    def __init__(self, commit_error=None):
        self.added = []
        self.rolled_back = 0
        self._commit_error = commit_error

    def query(self, *args, **kwargs):
        query = MagicMock()
        query.filter.return_value.count.return_value = 0
        query.filter.return_value.all.return_value = []
        query.filter.return_value.first.return_value = None
        return query

    def add(self, obj):
        self.added.append(obj)
        obj.id = 1

    def commit(self):
        if self._commit_error is not None:
            raise self._commit_error

    def rollback(self):
        self.rolled_back += 1

    def refresh(self, obj):
        if not getattr(obj, "id", None):
            obj.id = 1


class TestUploadErrorFidelity(unittest.TestCase):
    """/upload distingue "tu archivo está mal" de "el servidor está roto"."""

    def setUp(self):
        limiter.reset()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

        patches = [
            patch.object(data_router, "DATA_SOURCES_DIR", self._tmp.name),
            patch.object(common, "SESSIONS_DIR", self._tmp.name),
            patch.object(common, "sync_cloud_to_local", lambda *a, **k: False),
            patch.object(common, "upload_file_to_cloud", lambda *a, **k: True),
            patch.object(data_router, "upload_bytes", lambda *a, **k: True),
            patch.object(data_router, "delete_object", lambda *a, **k: True),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)

        common.data_store.clear()
        self.addCleanup(common.data_store.clear)

    def _client(self, db):
        app = FastAPI()
        app.state.limiter = limiter
        app.dependency_overrides[get_db] = lambda: db
        app.include_router(data_router.router, prefix="/api/v1")
        return TestClient(app)

    def _upload(self, db, filename="datos.csv", content=_CSV):
        client = self._client(db)
        return client.post(
            "/api/v1/upload",
            files={"file": (filename, content, "text/csv")},
            data={"user_id": "test_user_persistence@example.com"},
        )

    # ------------------------------------------------------------------

    def test_db_failure_returns_503_and_does_not_blame_the_file(self):
        """La BD caída no se reporta como "formato inválido"."""
        db = FakeSession(commit_error=Exception('relation "data_sources" does not exist'))
        response = self._upload(db)

        self.assertEqual(response.status_code, 503, response.text)
        detail = response.json()["detail"]
        self.assertNotIn("formato sea válido", detail)
        self.assertIn("válido", detail.lower())

    def test_db_failure_rolls_back_the_session(self):
        """Sin rollback la sesión queda envenenada: el request siguiente revienta."""
        db = FakeSession(commit_error=Exception("connection reset"))
        self._upload(db)

        self.assertEqual(db.rolled_back, 1, "la BD debe deshacer la transacción fallida")

    def test_db_failure_does_not_leave_an_orphan_file_on_disk(self):
        """El archivo se escribe antes de la BD; sin fila no es recuperable."""
        db = FakeSession(commit_error=Exception("connection reset"))
        self._upload(db)

        leftovers = [n for n in os.listdir(self._tmp.name) if n.endswith(".csv")]
        self.assertEqual([], leftovers, f"archivos huérfanos sin fila en la BD: {leftovers}")

    def test_generic_server_failure_does_not_blame_the_file(self):
        """El último recurso tampoco puede culpar al formato del archivo.

        Se fuerza el fallo en `get_user_data`, que el router importa **por
        valor** (`from src.utils.common import get_user_data`), así que el
        parche alcanza de verdad al `except Exception` genérico.
        """
        db = FakeSession()
        with patch.object(data_router, "get_user_data", side_effect=RuntimeError("boom")):
            response = self._upload(db)

        self.assertEqual(response.status_code, 500, response.text)
        detail = response.json()["detail"]
        # El mensaje histórico ("verifica que el formato sea válido") queda
        # prohibido: es la causa de que el usuario reformateara un CSV
        # correcto. Y el nuevo debe decir explícitamente que el archivo
        # superó las validaciones.
        self.assertNotIn("formato sea válido", detail)
        self.assertIn("superó las validaciones", detail)
        self.assertIn("servidor", detail.lower())

    def test_valid_upload_still_succeeds(self):
        """Control: el camino feliz no se ha roto con el cambio."""
        db = FakeSession()
        response = self._upload(db)

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["rows"], 3)
        self.assertTrue(body["persisted"])


if __name__ == "__main__":
    unittest.main()
