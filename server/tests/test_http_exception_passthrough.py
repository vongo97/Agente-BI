"""Tests de regresion para P-43: los errores accionables no se convierten en 500.

Los endpoints de simulacion envuelven todo el cuerpo en `try/except Exception` y
devolvian 500 "Error interno" incluso cuando la negativa era deliberada (400 por
falta de clave, 404, etc.). El cliente nunca veia el motivo real.

Regla: `except HTTPException: raise` SIEMPRE antes del `except Exception`.
"""
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.routers import simulation  # noqa: E402

ROUTER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "src", "routers", "simulation.py")
)


class _FakeQuery:
    """Sustituye a SQLAlchemy: no hay filas en el escenario probado."""

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return []

    def first(self):
        return None


class _FakeDB:
    def query(self, *args, **kwargs):
        return _FakeQuery()


class HttpExceptionNoSeEnmascaraTest(unittest.IsolatedAsyncioTestCase):
    async def test_generate_agents_sin_clave_devuelve_400_no_500(self):
        req = SimpleNamespace(
            selected_ids=[1],
            hypothesis="Hipotesis de prueba",
            provider="openai",
            api_key="",
            mistral_key=None,
        )
        # slowapi exige un Request real (el endpoint esta decorado con @limiter.limit)
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/api/v1/simulation/generate-agents",
                "headers": [],
                "client": ("127.0.0.1", 50000),
                "server": ("testserver", 80),
                "scheme": "http",
                "query_string": b"",
            }
        )
        with patch.object(simulation, "get_authenticated_user", return_value="test@example.com"), \
             patch.object(simulation, "check_authorization", return_value=None):
            with self.assertRaises(HTTPException) as ctx:
                await simulation.generate_agents_endpoint(
                    request=request, req=req, db=_FakeDB()
                )

        self.assertEqual(
            ctx.exception.status_code,
            400,
            "P-43: una clave ausente es un 400 accionable, no un 500 interno",
        )
        self.assertIn("OpenAI", ctx.exception.detail)
        self.assertNotIn("Error interno", ctx.exception.detail)


class SimulacionReLanzaHttpExceptionTest(unittest.TestCase):
    """Guardia estatica: los cuatro endpoints deben re-lanzar HTTPException."""

    def setUp(self):
        with open(ROUTER, "r", encoding="utf-8") as fh:
            self.fuente = fh.read()

    def test_cada_endpoint_tiene_except_http_exception(self):
        self.assertGreaterEqual(
            self.fuente.count("except HTTPException:"),
            4,
            "P-43: create_simulation, suggestions, ontology y generate-agents "
            "deben re-lanzar HTTPException antes del except generico",
        )

    def test_no_se_loguea_solo_el_tipo_en_generate_agents(self):
        self.assertNotIn(
            'logger.error("[Sim-agents] Error al generar agentes: %s", type(e).__name__)',
            self.fuente,
            "P-43: el log debe incluir un mensaje saneado, no solo el tipo",
        )


if __name__ == "__main__":
    unittest.main()
