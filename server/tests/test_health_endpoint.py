"""Regresión P-22: /health no puede bloquear el event loop ni exponer el bucket.

Render sondea ``/live`` cada ~30 s; si ``/health`` ejecuta la sonda de Supabase y
la inspección de esquema dentro de la corrutina, esas I/O síncronas bloquean el
event loop (y con él ``/live``), que es la causa de los reinicios de P-56.

Este test comprueba que el event loop sigue vivo mientras /health espera las
sondas (se ejecutan en el threadpool) y que la respuesta pública no filtra el
nombre del bucket ni credenciales.
"""
import asyncio
import os
import sys
import threading
import time
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_bi.db")
os.environ.setdefault("ENVIRONMENT", "development")

import main  # noqa: E402


def _slow_probe(name, calls, delay=0.15):
    def probe():
        calls.append(name)
        assert threading.current_thread().name != threading.main_thread().name
        time.sleep(delay)
        if name == "schema":
            return {"upload_schema_ready": True}
        return {"cloud": True, "connected": True, "bucket": "data_sources", "reason": None}

    return probe


def test_health_ejecuta_las_sondas_fuera_del_event_loop():
    calls = []

    async def run():
        ticks = 0
        stop = False

        async def ticker():
            nonlocal ticks
            while not stop:
                ticks += 1
                await asyncio.sleep(0.01)

        ticker_task = asyncio.create_task(ticker())
        try:
            with patch("src.database.db_schema_diagnostic", _slow_probe("schema", calls)), \
                 patch("src.utils.supabase_storage.storage_diagnostic", _slow_probe("storage", calls)):
                resp = await main.root()
        finally:
            stop = True
            await ticker_task
        return resp, ticks

    resp, ticks = asyncio.run(run())

    assert resp["status"] == "online"
    assert calls == ["schema", "storage"]
    # Si las sondas bloquearan la corrutina (2 x 0.15 s), el ticker no avanzaría.
    assert ticks > 3, ticks


def test_health_no_expone_bucket_ni_credenciales():
    calls = []

    async def run():
        with patch("src.database.db_schema_diagnostic", _slow_probe("schema", calls)), \
             patch("src.utils.supabase_storage.storage_diagnostic", _slow_probe("storage", calls)):
            return await main.root()

    resp = asyncio.run(run())

    assert "bucket" not in resp["storage"], resp["storage"]
    texto = str(resp)
    assert "supabase.co" not in texto
    assert "sb_secret_" not in texto
    assert "SUPABASE_SERVICE_ROLE_KEY" not in texto
