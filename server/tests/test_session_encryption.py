"""Tests de regresion para P-02: persistencia de sesiones siempre cifrada.

Regla del registro (docs/PROBLEMAS_CONOCIDOS.md):
prohibido `pd.to_pickle`, `to_csv` u `open(..., "w")` directo en routers.
Toda persistencia pasa por `save_user_data()`, que cifra con Fernet antes de
escribir a disco y subir a la nube.
"""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import src.utils.common as common  # noqa: E402

DATA_ROUTER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "src", "routers", "data.py")
)


class SessionEncryptionTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

        patches = [
            patch.object(common, "SESSIONS_DIR", self._tmp.name),
            # Evitar red: la nube no participa en estos tests
            patch.object(common, "sync_cloud_to_local", lambda *a, **k: False),
            patch.object(common, "upload_file_to_cloud", lambda *a, **k: None),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)

        common.data_store.clear()
        self.addCleanup(common.data_store.clear)

        self.payload = {
            "type": "file",
            "data": {"dataset_1": pd.DataFrame({"columna_secreta": [1, 2, 3]})},
            "sources": [42],
        }

    def _write(self, user: str = "user@example.com") -> str:
        common.save_user_data(user, self.payload)
        path = common.get_session_file(user)
        self.assertTrue(os.path.exists(path), "save_user_data no creo el archivo de sesion")
        return path

    def test_archivo_empieza_con_token_fernet(self):
        path = self._write()
        with open(path, "rb") as fh:
            raw = fh.read()
        self.assertTrue(raw.startswith(b"gAAA"), "El archivo no esta cifrado con Fernet")

    def test_no_hay_datos_en_claro_en_el_disco(self):
        path = self._write()
        with open(path, "rb") as fh:
            raw = fh.read()
        self.assertNotIn(b"columna_secreta", raw, "Se filtro el nombre de una columna en claro")
        self.assertNotIn(b"pandas", raw, "Se filtro metadata del DataFrame en claro")

    def test_roundtrip_descifra_y_recupera_datos(self):
        user = "user@example.com"
        self._write(user)
        common.data_store.clear()  # forzar lectura desde disco

        recovered = common.get_user_data(user)

        self.assertIsNotNone(recovered)
        self.assertEqual(recovered["type"], "file")
        self.assertEqual(recovered["sources"], [42])
        df = recovered["data"]["dataset_1"]
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(list(df.columns), ["columna_secreta"])
        self.assertEqual(df["columna_secreta"].tolist(), [1, 2, 3])


class DataRouterNoPlaintextTest(unittest.TestCase):
    """Guardia estatica: si alguien vuelve a escribir en claro, el test falla."""

    def setUp(self):
        with open(DATA_ROUTER, "r", encoding="utf-8") as fh:
            self.source = fh.read()

    def test_no_usa_pd_to_pickle(self):
        self.assertNotIn(
            "pd.to_pickle(",
            self.source,
            "P-02: prohibido pd.to_pickle en routers; usa save_user_data()",
        )

    def test_persiste_con_save_user_data(self):
        self.assertGreaterEqual(
            self.source.count("save_user_data(authenticated_user, session_data)"),
            2,
            "P-02: los dos flujos (Google Sheets y limpieza IA) deben usar save_user_data",
        )


if __name__ == "__main__":
    unittest.main()
