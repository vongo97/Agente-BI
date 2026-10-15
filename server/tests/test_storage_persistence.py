"""Tests de la refactorización de persistencia (nube como fuente de verdad).

Cubre:
- is_cloud_key: discriminación clave de bucket vs ruta local (legado).
- resolve_source_path: descarga desde la nube a caché local, fallback legacy
  y fallo honesto cuando la nube no responde.
- load_source_to_session: reconstrucción de un DataFrame desde clave de nube
  (archivo cifrado en el bucket).
- ensure_user_session: reconstrucción del pool completo tras un "reinicio".
"""
import unittest
import sys
import os
import types
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Entorno determinista ANTES de importar módulos que leen env al importar
os.environ["ENVIRONMENT"] = "development"
os.environ["RENDER"] = "false"
os.environ["AUTH_SECRET"] = "test-secret"
os.environ["SUPABASE_URL"] = ""           # neutraliza la nube real (ni siquiera en dev)
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = ""

from cryptography.fernet import Fernet
os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

from src.utils import common
from src.utils.common import (
    data_store,
    DATA_SOURCES_DIR,
    is_cloud_key,
    resolve_source_path,
    load_source_to_session,
    ensure_user_session,
)
import pandas as pd

USER = "persist_test@example.com"

CSV_BYTES = b"col_a,col_b\n1,2\n3,4\n"
CLOUD_KEY = "data_sources/ab12cd34/persist_test_file.csv"


def make_source(url=CLOUD_KEY, name="persist_test_file.csv", is_encrypted=True):
    return types.SimpleNamespace(
        id=1, user_id=USER, name=name, type="file", url=url,
        columns=None, is_encrypted=is_encrypted, size_bytes=len(CSV_BYTES),
    )


class TestIsCloudKey(unittest.TestCase):
    def test_clave_de_bucket_es_cloud_key(self):
        self.assertTrue(is_cloud_key("data_sources/abc/file.csv"))
        self.assertTrue(is_cloud_key("sessions/abc.pkl"))

    def test_ruta_local_legacy_no_es_cloud_key(self):
        self.assertFalse(is_cloud_key("/data/data_sources/file.csv"))
        self.assertFalse(is_cloud_key("C:\\proj\\data_sources\\file.csv"))
        self.assertFalse(is_cloud_key("./data_sources/file.csv"))

    def test_valores_vacios(self):
        self.assertFalse(is_cloud_key(None))
        self.assertFalse(is_cloud_key(""))


class TestResolveSourcePath(unittest.TestCase):
    def setUp(self):
        data_store.clear()

    def tearDown(self):
        data_store.clear()
        cached = os.path.join(DATA_SOURCES_DIR, os.path.basename(CLOUD_KEY))
        if os.path.exists(cached):
            os.remove(cached)

    def test_ruta_local_existente_gana_legado(self):
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(CSV_BYTES)
            legacy_path = tmp.name
        try:
            src = make_source(url=legacy_path, is_encrypted=False)
            self.assertEqual(resolve_source_path(src), legacy_path)
        finally:
            if os.path.exists(legacy_path):
                os.remove(legacy_path)

    @patch('src.utils.common.download_bytes')
    def test_descarga_desde_clave_de_nube(self, mock_download):
        # Cifrar con el cipher_suite VIGENTE en runtime: otros tests pueden
        # haber recargado src.utils.security con otra clave (importlib.reload),
        # así que la referencia capturada al importar sería obsoleta.
        from src.utils.security import cipher_suite
        encrypted = cipher_suite.encrypt(CSV_BYTES)
        mock_download.return_value = encrypted

        resolved = resolve_source_path(make_source())

        self.assertIsNotNone(resolved)
        self.assertTrue(os.path.exists(resolved))
        with open(resolved, 'rb') as f:
            self.assertEqual(f.read(), encrypted)
        mock_download.assert_called_once_with(CLOUD_KEY)

    @patch('src.utils.common.download_bytes')
    def test_fallo_de_nube_devuelve_none(self, mock_download):
        mock_download.return_value = None  # bucket caído / objeto ausente
        self.assertIsNone(resolve_source_path(make_source()))

    def test_url_vacia_devuelve_none(self):
        self.assertIsNone(resolve_source_path(make_source(url=None)))


class TestSessionRebuildAfterRestart(unittest.TestCase):
    """Simula el ciclo completo: upload → reinicio (cachés vacías) → reconstrucción."""

    def setUp(self):
        data_store.clear()
        # Eliminar cualquier pickle de sesión previo para forzar arranque limpio
        import hashlib
        safe_user = hashlib.md5(USER.encode()).hexdigest()
        self.session_file = os.path.join(common.SESSIONS_DIR, f"{safe_user}.pkl")
        if os.path.exists(self.session_file):
            os.remove(self.session_file)

    def tearDown(self):
        data_store.clear()
        cached = os.path.join(DATA_SOURCES_DIR, os.path.basename(CLOUD_KEY))
        if os.path.exists(cached):
            os.remove(cached)

    @patch('src.utils.common.download_bytes')
    def test_load_source_to_session_reconstruye_desde_nube(self, mock_download):
        from src.utils.security import cipher_suite  # vigente en runtime (ver nota arriba)
        encrypted = cipher_suite.encrypt(CSV_BYTES)
        mock_download.return_value = encrypted

        ok = load_source_to_session(USER, make_source())

        self.assertTrue(ok)
        session = data_store.get(f"{USER}_active")
        self.assertIsNotNone(session)
        self.assertIn("persist_test_file", session["data"])
        df = session["data"]["persist_test_file"]
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 2)
        self.assertIn(1, session["sources"])

    @patch('src.utils.common.load_source_to_session')
    def test_ensure_user_session_reconstruye_pool_completo(self, mock_load):
        def fake_load(user_id, source, chat_id=None):
            key = f"{user_id}_active"
            data_store[key] = {"type": "file", "data": {"persist_test_file": pd.DataFrame({"a": [1]})}, "sources": [source.id]}
            return True
        mock_load.side_effect = fake_load

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [make_source()]

        # Simular contenedor recién reiniciado: ni memoria ni pickle
        session = ensure_user_session(USER, mock_db)

        self.assertIsNotNone(session)
        self.assertIn("persist_test_file", session["data"])
        mock_load.assert_called_once()

    def test_ensure_user_session_sin_fuentes_devuelve_lo_hay(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []
        self.assertIsNone(ensure_user_session(USER, mock_db))


if __name__ == '__main__':
    unittest.main()
