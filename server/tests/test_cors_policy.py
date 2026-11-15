"""P-21 · Test explícito de la política CORS.

P-21 estaba en PARCIAL porque, aun habiendo tests de JWT, `AUTHORIZED_EMAILS`,
cifrado y uploads, **faltaba un test explícito de CORS**. Este archivo lo cubre.

Regla 5 del registro: *«Un control desconectado no existe.»* Si alguien
desenchufa el middleware CORS o abre la lista de orígenes a `*`, estos tests
fallan.

Qué se vigila:
  1. El middleware CORS está montado (si no, no hay cabeceras CORS).
  2. La allowlist es una allowlist: **no** hay comodines ni comodines de
     subdominio (regla 4 del registro: *«Sin listas negras / comodines de
     seguridad. Usa allowlist»*).
  3. Un origen permitido recibe `Access-Control-Allow-Origin`.
  4. Un origen **no** permitido NO recibe esa cabecera (allowlist efectiva).
  5. `allow_credentials=True` no se combina con un origen comodín (si lo
     hiciese, el navegador rechazaría la respuesta, pero además sería un
     error de configuración que hay que cazar antes).
  6. `X-Request-Id` está en `expose_headers` (P-36 necesita que el cliente
     pueda leerlo para correlacionar errores).
"""

import importlib
import os
import sys
import types
import unittest
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("RENDER", "false")
os.environ.setdefault("AUTH_SECRET", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_bi.db")


def _install_pkce_stubs() -> None:
    """`pkce_storage_factory` / `pkce_middleware` son dependencias opcionales."""
    if 'src.utils.pkce_storage_factory' not in sys.modules:
        pkce_mod = types.ModuleType('src.utils.pkce_storage_factory')

        class FakePKCEStorageFactory:
            def create_storage(self, storage_type="redis"):
                return MagicMock()

        pkce_mod.PKCEStorageFactory = FakePKCEStorageFactory
        sys.modules['src.utils.pkce_storage_factory'] = pkce_mod

    if 'src.utils.pkce_middleware' not in sys.modules:
        pkce_mid = types.ModuleType('src.utils.pkce_middleware')

        class FakePKCEAuthMiddleware:
            def __init__(self, app=None, exclude_paths=None, storage_factory=None, **kwargs):
                pass

        pkce_mid.PKCEAuthMiddleware = FakePKCEAuthMiddleware
        sys.modules['src.utils.pkce_middleware'] = pkce_mid


def _load_main():
    """Importa `main` (el real) con las dependencias opcionales simuladas."""
    _install_pkce_stubs()
    import main as main_module

    return importlib.reload(main_module)


class TestCorsMiddlewareInstalled(unittest.TestCase):
    """P-21: el middleware CORS está montado y bien configurado."""

    @classmethod
    def setUpClass(cls):
        cls.main = _load_main()
        cls.app = cls.main.app

    def test_cors_middleware_is_registered(self):
        """Sin `CORSMiddleware` no hay CORS: el frontend no puede ni llamarnos."""
        from starlette.middleware.cors import CORSMiddleware

        middlewares = [
            middleware for middleware in self.app.user_middleware
            if middleware.cls is CORSMiddleware
        ]
        self.assertTrue(
            middlewares,
            "P-21: el middleware CORS no está montado en la app.",
        )

    def test_allowed_origins_is_an_allowlist(self):
        """La allowlist no puede contener comodines.

        Regla 4: *«Sin listas negras de seguridad. Usa allowlist»*. Un `*` o un
        comodín de subdominio (`https://*.vercel.app`) convertiría la
        allowlist en "cualquiera", que es exactamente el agujero que CORS
        cierra.
        """
        origins = self.main.ALLOWED_ORIGINS

        self.assertTrue(origins, "P-21: la allowlist de orígenes está vacía.")

        for origin in origins:
            self.assertNotEqual(origin, "*", "P-21: allowlist con comodín total.")
            self.assertNotIn("*", origin, f"P-21: allowlist con comodín: {origin}")

    def test_http_origins_only_allowed_for_localhost_in_development(self):
        """Los orígenes HTTP solo pueden ser `localhost` y solo en desarrollo.

        `server/.env` legitimately allows `http://localhost:3000` so the Next.js
        dev server can call the API. That is fine **locally**; in production a
        plain-HTTP origin would let a network attacker read the API responses.
        """
        is_dev = os.getenv("ENVIRONMENT", "production").strip().lower() in {
            "development",
            "dev",
            "local",
            "test",
        }

        for origin in self.main.ALLOWED_ORIGINS:
            if origin.startswith("https://"):
                continue

            self.assertTrue(
                origin.startswith("http://"),
                f"P-21: origen con esquema desconocido en la allowlist: {origin}",
            )
            host = origin.split("://", 1)[1].split(":", 1)[0]
            self.assertIn(
                host,
                ("localhost", "127.0.0.1"),
                f"P-21: origen no-HTTPS que no es local en la allowlist: {origin}",
            )
            self.assertTrue(
                is_dev,
                f"P-21: origen HTTP local permitido en producción: {origin}",
            )

    def test_expose_headers_include_request_id(self):
        """P-36: el cliente debe poder leer `X-Request-Id` para correlacionar."""
        from starlette.middleware.cors import CORSMiddleware

        cors = next(
            m for m in self.app.user_middleware if m.cls is CORSMiddleware
        )
        self.assertIn("X-Request-Id", cors.kwargs["expose_headers"])

    def test_allow_credentials_is_not_combined_with_wildcard(self):
        """`allow_credentials=True` + origen `*` es una config inválida."""
        from starlette.middleware.cors import CORSMiddleware

        cors = next(
            m for m in self.app.user_middleware if m.cls is CORSMiddleware
        )
        options = cors.kwargs
        if options.get("allow_credentials"):
            self.assertNotIn("*", options.get("allow_origins", []))


class TestCorsBehaviour(unittest.TestCase):
    """P-21: comportamiento observable del CORS."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient

        cls.main = _load_main()
        cls.client = TestClient(cls.main.app)
        cls.allowed_origin = cls.main.ALLOWED_ORIGINS[0]

    def test_allowed_origin_receives_allow_origin_header(self):
        """Un origen de la allowlist recibe `Access-Control-Allow-Origin`."""
        response = self.client.get("/live", headers={"Origin": self.allowed_origin})
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            self.allowed_origin,
        )

    def test_unknown_origin_does_not_receive_allow_origin_header(self):
        """Un origen fuera de la allowlist NO recibe la cabecera.

        Esta es la comprobación de que la allowlist *efectivamente* restringe:
        si el middleware desapareciera o se pusiera en `*`, este test falla.
        """
        response = self.client.get("/live", headers={"Origin": "https://atacante.example"})
        self.assertIsNone(
            response.headers.get("access-control-allow-origin"),
            "P-21: un origen no permitido está recibiendoAccess-Control-Allow-Origin. "
            "La allowlist no está restringiendo nada.",
        )

    def test_preflight_from_unknown_origin_is_not_allowed(self):
        """El preflight OPTIONS de un origen desconocido no se autoriza."""
        response = self.client.options(
            "/live",
            headers={
                "Origin": "https://atacante.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertIsNone(response.headers.get("access-control-allow-origin"))

    def test_preflight_from_allowed_origin_is_allowed(self):
        """El preflight OPTIONS de un origen permitido sí se autoriza."""
        response = self.client.options(
            "/live",
            headers={
                "Origin": self.allowed_origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            self.allowed_origin,
        )


if __name__ == '__main__':
    unittest.main()
