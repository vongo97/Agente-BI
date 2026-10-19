"""Tests de regresion para P-01: bypass de autenticacion fail-open.

Regla del registro (docs/PROBLEMAS_CONOCIDOS.md):
ningun control de seguridad puede activarse por la *ausencia* de configuracion.

El antiguo comportamiento (ENVIRONMENT por defecto = "development") permitia
entrar como test_user sin token en cualquier despliegue que olvidara definir
la variable. Estos tests fijan el contrato correcto: fail-closed por defecto.
"""
import os
import sys
import time
import unittest

import jwt
from fastapi import HTTPException
from starlette.requests import Request

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.utils.common import (  # noqa: E402
    _TEST_USER,
    check_authorization,
    get_authenticated_user,
    request_var,
)

SECRET = "test-secret-p01-0123456789abcdef"


def _build_request(host: str = "127.0.0.1", token: str | None = None) -> Request:
    headers = []
    if token:
        headers.append((b"authorization", f"Bearer {token}".encode()))
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "root_path": "",
            "headers": headers,
            "client": (host, 50000),
            "server": ("testserver", 80),
        }
    )


def _valid_token(email: str = "User@Example.com") -> str:
    payload = {"user_id": email, "exp": int(time.time()) + 3600}
    return jwt.encode(payload, SECRET, algorithm="HS256")


class AuthenticationBypassTest(unittest.TestCase):
    def setUp(self):
        self._saved = {
            key: os.environ.get(key)
            for key in ("ENVIRONMENT", "RENDER", "AUTHORIZED_EMAILS", "AUTH_SECRET")
        }
        os.environ.pop("ENVIRONMENT", None)
        os.environ.pop("RENDER", None)
        os.environ.pop("AUTHORIZED_EMAILS", None)
        os.environ["AUTH_SECRET"] = SECRET
        self._ctx_token = request_var.set(None)

    def tearDown(self):
        request_var.reset(self._ctx_token)
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    # ── Sin entorno declarado: el default debe ser produccion (fail-closed) ──
    def test_sin_environment_y_sin_token_deniega(self):
        request_var.set(_build_request())
        with self.assertRaises(HTTPException) as ctx:
            get_authenticated_user()
        self.assertEqual(ctx.exception.status_code, 401)

    def test_sin_environment_y_sin_contexto_deniega(self):
        with self.assertRaises(HTTPException) as ctx:
            get_authenticated_user()
        self.assertEqual(ctx.exception.status_code, 401)

    # ── Produccion explicita ─────────────────────────────────────────────────
    def test_produccion_sin_token_deniega(self):
        os.environ["ENVIRONMENT"] = "production"
        request_var.set(_build_request())
        with self.assertRaises(HTTPException) as ctx:
            get_authenticated_user()
        self.assertEqual(ctx.exception.status_code, 401)

    def test_produccion_token_valido_devuelve_email(self):
        os.environ["ENVIRONMENT"] = "production"
        request_var.set(_build_request(token=_valid_token()))
        self.assertEqual(get_authenticated_user(), "user@example.com")

    def test_produccion_token_invalido_deniega(self):
        os.environ["ENVIRONMENT"] = "production"
        request_var.set(_build_request(token="token-falso"))
        with self.assertRaises(HTTPException) as ctx:
            get_authenticated_user()
        self.assertEqual(ctx.exception.status_code, 401)

    # ── Desarrollo local real ───────────────────────────────────────────────
    def test_desarrollo_local_permite_usuario_de_pruebas(self):
        os.environ["ENVIRONMENT"] = "development"
        request_var.set(_build_request(host="127.0.0.1"))
        self.assertEqual(get_authenticated_user(), _TEST_USER)

    def test_desarrollo_ip_remota_deniega(self):
        os.environ["ENVIRONMENT"] = "development"
        request_var.set(_build_request(host="10.1.2.3"))
        with self.assertRaises(HTTPException) as ctx:
            get_authenticated_user()
        self.assertEqual(ctx.exception.status_code, 401)

    def test_render_deniega_aunque_sea_development(self):
        os.environ["ENVIRONMENT"] = "development"
        os.environ["RENDER"] = "true"
        request_var.set(_build_request(host="127.0.0.1"))
        with self.assertRaises(HTTPException) as ctx:
            get_authenticated_user()
        self.assertEqual(ctx.exception.status_code, 401)

    # ── Compatibilidad: apps de test sin middleware (no hay request) ────────
    def test_desarrollo_sin_contexto_mantiene_usuario_de_pruebas(self):
        os.environ["ENVIRONMENT"] = "development"
        self.assertEqual(get_authenticated_user(), _TEST_USER)

    # ── Lista blanca AUTHORIZED_EMAILS ──────────────────────────────────────
    def test_produccion_no_exime_test_user_de_la_allowlist(self):
        os.environ["ENVIRONMENT"] = "production"
        os.environ["AUTHORIZED_EMAILS"] = "otro@example.com"
        with self.assertRaises(HTTPException) as ctx:
            check_authorization(_TEST_USER)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_desarrollo_local_exime_test_user(self):
        os.environ["ENVIRONMENT"] = "development"
        os.environ["AUTHORIZED_EMAILS"] = "otro@example.com"
        request_var.set(_build_request(host="127.0.0.1"))
        self.assertTrue(check_authorization(_TEST_USER))

    def test_produccion_allowlist_permite_usuario_incluido(self):
        os.environ["ENVIRONMENT"] = "production"
        os.environ["AUTHORIZED_EMAILS"] = "user@example.com"
        request_var.set(_build_request(token=_valid_token()))
        self.assertTrue(check_authorization("user@example.com"))

    def test_produccion_token_no_coincide_con_usuario_deniega(self):
        os.environ["ENVIRONMENT"] = "production"
        os.environ["AUTHORIZED_EMAILS"] = "user@example.com,otro@example.com"
        request_var.set(_build_request(token=_valid_token("user@example.com")))
        with self.assertRaises(HTTPException) as ctx:
            check_authorization("otro@example.com")
        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
