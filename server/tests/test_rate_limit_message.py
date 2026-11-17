"""P-76 · El 429 debe explicar qué hacer, no soltar el detalle crudo de slowapi.

El manejador por defecto de slowapi devuelve ``{"detail": "5 per 1 minute"}``.
Ese texto llega tal cual al cliente y, durante las pruebas manuales (subir
varios archivos seguidos), el usuario ve un error sin explicación que parece
un fallo del servidor.

Este test fija que la respuesta 429:
  - sea accionable (dice cuánto esperar),
  - incluya la cabecera ``Retry-After``,
  - y no exponga el detalle crudo como único contenido.
"""
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ["ENVIRONMENT"] = "development"
os.environ["RENDER"] = "false"
os.environ["AUTH_SECRET"] = "test-secret"

pkce_mod = types.ModuleType("src.utils.pkce_storage_factory")
pkce_mod.PKCEStorageFactory = MagicMock
sys.modules.setdefault("src.utils.pkce_storage_factory", pkce_mod)
pkce_mid = types.ModuleType("src.utils.pkce_middleware")
pkce_mid.PKCEAuthMiddleware = MagicMock
sys.modules.setdefault("src.utils.pkce_middleware", pkce_mid)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402

from src.utils.limiter import limiter  # noqa: E402


class TestRateLimitMessage(unittest.TestCase):
    """La respuesta 429 es accionable."""

    def setUp(self):
        limiter.reset()

    def _app(self):
        # Import diferido: main.py importa los routers y arranca la DB.
        import main

        app = FastAPI()
        app.state.limiter = limiter

        @app.exception_handler(RateLimitExceeded)
        async def _handler(request, exc):
            return await main._rate_limit_handler(request, exc)

        @app.get("/probe")
        async def _probe():
            return {"ok": True}

        return app

    def _trigger(self):
        from fastapi import Request

        app = self._app()
        client = TestClient(app)
        # Se dispara el límite real contra un endpoint protegido.
        @app.get("/limited")
        @limiter.limit("2/minute")
        async def _limited(request: Request):
            return {"ok": True}

        respuestas = []
        for _ in range(4):
            respuestas.append(client.get("/limited"))
        return respuestas

    def test_429_dice_cuanto_esperar(self):
        respuestas = self._trigger()
        limitada = [r for r in respuestas if r.status_code == 429]
        self.assertTrue(limitada, "se esperaba al menos un 429 con límite 2/minute")

        cuerpo = limitada[0].json()
        self.assertIn("detail", cuerpo)
        detalle = cuerpo["detail"]
        self.assertNotEqual(
            detalle,
            "2 per 1 minute",
            "el detalle crudo de slowapi no debe llegar al usuario tal cual",
        )
        self.assertIn("Demasiadas peticiones seguidas", detalle)
        self.assertIn("segundos", detalle.lower())
        self.assertIn("inténtalo de nuevo", detalle.lower())

    def test_429_lleva_cabecera_retry_after(self):
        respuestas = self._trigger()
        limitada = [r for r in respuestas if r.status_code == 429]
        self.assertTrue(limitada)

        retry_after = limitada[0].headers.get("Retry-After")
        self.assertIsNotNone(retry_after, "falta la cabecera Retry-After")
        self.assertGreater(int(retry_after), 0)


if __name__ == "__main__":
    unittest.main()
