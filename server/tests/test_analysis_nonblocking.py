"""Regresión: /analyze no puede bloquear el event loop con llamadas al LLM.

Render reinicia el servicio si su health check no responde. Las llamadas a los
proveedores son síncronas (requests/SDK); si se ejecutan dentro de la corrutina
de /analyze, bloquean también /live y /health. Este test comprueba que el
análisis cede el control mientras espera al proveedor.
"""
import asyncio
import threading
import time

import pandas as pd
from unittest.mock import patch

from src.engine import bi_analyst


def test_analyze_data_offloads_provider_calls_and_keeps_event_loop_alive():
    call_threads = []
    responses = ["plan", "print('ok')", '{"status": "success"}', "narrative"]

    def fake_generate_ai_content(*args, **kwargs):
        call_threads.append(threading.current_thread().name)
        time.sleep(0.12)
        return responses.pop(0)

    async def fake_execute_analysis(*args, **kwargs):
        return "resultado de prueba", None

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
            with patch.object(bi_analyst, "generate_ai_content", fake_generate_ai_content), \
                 patch.object(bi_analyst.executor, "execute_analysis", fake_execute_analysis):
                result = await bi_analyst.analyze_data(
                    pd.DataFrame({"sales": [1, 2], "profit": [1, 2]}),
                    "¿Cuál es la tendencia?",
                    "test-key",
                    provider="openai",
                )
        finally:
            stop = True
            await ticker_task
        return result, ticks

    result, ticks = asyncio.run(run())

    assert result[0] == "narrative"
    assert len(call_threads) == 4
    assert all(name != threading.main_thread().name for name in call_threads), call_threads
    # Si el event loop se hubiera bloqueado durante los 4 * 0.12 s de espera,
    # el ticker no habría avanzado.
    assert ticks > 3
