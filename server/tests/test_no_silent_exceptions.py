"""P-36 · Guardián del registro de excepciones.

La regla 8 del registro de problemas conocidos dice: *«Sin `except: pass`. Si se
ignora un error, se registra con contexto.»* Ese control es fácil de desconectar
—basta con que alguien escriba un `except: pass` y nadie se entera— así que este
test lo vigila de forma estática sobre **todo** `server/src/`.

Además comprueba que el mecanismo de registro existe de verdad y que el
`request_id` viaja con cada log, que es la otra mitad del criterio de cierre.

Sin este test, el control "no hay except: pass" no existiría (regla 5).
"""

import ast
import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("RENDER", "false")
os.environ.setdefault("AUTH_SECRET", "test-secret")

SRC_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'src')
)

# Cuerpos que "tragan" la excepción sin dejar rastro.
SILENT_BODIES = {"pass"}


def _iter_python_files(root: str):
    for dirpath, _dirnames, filenames in os.walk(root):
        for filename in filenames:
            if filename.endswith(".py"):
                yield os.path.join(dirpath, filename)


def _handler_body_is_silent(handler) -> bool:
    """True si el `except` contiene un `pass` (o un cuerpo vacío).

    Regla de P-36: dentro de un `except` **nada** debe ser `pass`. Un `pass`
    significa "me trago el error". Y da igual que el handler haga además otra
    cosa (un `pass` seguido de un `fallback = X` sigue tragándose el error):
    el `pass` es exactamente la marca del olvido.

    Se ignoran los `except` que re-lanzan (`raise`), que ya propagan el error
    y por tanto no lo ocultan.
    """
    if not handler.body:
        return True
    for stmt in handler.body:
        if isinstance(stmt, ast.Pass):
            return True
    return False


class TestNoSilentExceptions(unittest.TestCase):
    """P-36: ningún `except` puede quedarse en `pass`."""

    def _scan(self):
        offenders = []
        for path in _iter_python_files(SRC_ROOT):
            with open(path, "r", encoding="utf-8") as fh:
                source = fh.read()
            try:
                tree = ast.parse(source, filename=path)
            except SyntaxError as exc:  # pragma: no cover
                raise AssertionError(f"{path} no parsea: {exc}") from exc

            for node in ast.walk(tree):
                if not isinstance(node, ast.ExceptHandler):
                    continue
                if _handler_body_is_silent(node):
                    offenders.append(
                        f"{os.path.relpath(path, SRC_ROOT)}:{node.lineno}"
                    )
        return offenders

    def test_no_except_pass_in_server_src(self):
        """No debe existir ningún `except ...: pass` en server/src/."""
        offenders = self._scan()
        self.assertEqual(
            offenders,
            [],
            "P-36: hay `except: pass` sin registro. Cada uno debe llamar a "
            "`log_ignored_error(...)` (con tipo + mensaje saneado + request_id) "
            "o documentar por qué la excepción es deliberadamente ignorable.\n"
            + "\n".join(offenders),
        )

    def test_no_bare_except_in_server_src(self):
        """No debe existir `except:` a secas.

        Un `except:` sin tipo también captura `KeyboardInterrupt` y
        `SystemExit`, que nunca deben tragarse.
        """
        offenders = []
        for path in _iter_python_files(SRC_ROOT):
            with open(path, "r", encoding="utf-8") as fh:
                tree = ast.parse(fh.read(), filename=path)
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    offenders.append(
                        f"{os.path.relpath(path, SRC_ROOT)}:{node.lineno}"
                    )
        self.assertEqual(
            offenders,
            [],
            "P-36: `except:` sin tipo captura KeyboardInterrupt/SystemExit. "
            "Usa `except Exception as e:` o el tipo concreto.\n"
            + "\n".join(offenders),
        )


class TestIgnoredErrorLogging(unittest.TestCase):
    """P-36: el mecanismo de registro existe y funciona."""

    def test_log_ignored_error_includes_type_and_request_id(self):
        import logging
        from src.utils.logging_config import (
            log_ignored_error,
            request_id_var,
            get_request_id,
        )

        records = []

        class _Capture(logging.Handler):
            def emit(self, record):
                records.append(record)

        logger = logging.getLogger("test.p36")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(_Capture())
        logger.propagate = False

        token = request_id_var.set("req-abc-123")
        try:
            log_ignored_error(
                logger,
                "prueba de contexto",
                ValueError("mensaje sensible sk-ABCDEF123456"),
                extra_thing="x",
            )
        finally:
            request_id_var.reset(token)

        self.assertEqual(len(records), 1)
        message = records[0].getMessage()

        # El tipo de la excepción está.
        self.assertIn("ValueError", message)
        # El request_id está.
        self.assertIn("req-abc-123", message)
        # El contexto está.
        self.assertIn("prueba de contexto", message)

    def test_request_id_falls_back_to_dash(self):
        from src.utils.logging_config import get_request_id, request_id_var

        token = request_id_var.set(None)
        try:
            self.assertEqual(get_request_id(), "-")
        finally:
            request_id_var.reset(token)


class TestRequestIdMiddleware(unittest.TestCase):
    """P-36: el `X-Request-Id` se genera y se propaga."""

    def test_response_carries_x_request_id(self):
        import types
        from unittest.mock import MagicMock
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        # pkce es una dependencia opcional (mismo patrón que el resto de tests).
        pkce_mod = types.ModuleType('src.utils.pkce_storage_factory')

        class FakePKCEStorageFactory:
            def create_storage(self, storage_type="redis"):
                return MagicMock()

        pkce_mod.PKCEStorageFactory = FakePKCEStorageFactory
        sys.modules['src.utils.pkce_storage_factory'] = pkce_mod

        pkce_mid = types.ModuleType('src.utils.pkce_middleware')

        class FakePKCEAuthMiddleware:
            def __init__(self, app=None, exclude_paths=None, storage_factory=None, **kwargs):
                pass

        pkce_mid.PKCEAuthMiddleware = FakePKCEAuthMiddleware
        sys.modules['src.utils.pkce_middleware'] = pkce_mid

        # Importamos el middleware REAL de main.py (no una copia): si alguien
        # lo desenchufa, este test falla. Evitamos arrancar toda la app (DB y
        # routers) replicando solo el `app.middleware` decorator.
        import importlib
        import main as main_module

        main_module = importlib.reload(main_module)

        app = FastAPI()
        app.middleware("http")(main_module.request_id_middleware)

        @app.get("/ping")
        async def ping():
            from src.utils.logging_config import get_request_id
            return {"rid": get_request_id()}

        client = TestClient(app)

        # 1) Sin cabecera: el servidor genera una.
        response = client.get("/ping")
        self.assertEqual(response.status_code, 200)
        generated = response.headers.get("X-Request-Id")
        self.assertTrue(generated, "La respuesta debe llevar X-Request-Id")
        self.assertEqual(response.json()["rid"], generated)

        # 2) Con cabecera válida: se respeta la del cliente (correlación).
        response = client.get("/ping", headers={"X-Request-Id": "cliente-123"})
        self.assertEqual(response.headers.get("X-Request-Id"), "cliente-123")
        self.assertEqual(response.json()["rid"], "cliente-123")

        # 3) Con cabecera basura: se genera una nueva (no se propaga basura).
        response = client.get("/ping", headers={"X-Request-Id": "no valido; drop table"})
        self.assertNotEqual(response.headers.get("X-Request-Id"), "no valido; drop table")
        self.assertTrue(response.headers.get("X-Request-Id"))

        # 4) Un UUID del cliente se respeta tal cual.
        uuid_like = "3f2504e0-4f89-41d3-9a0c-0305e82c3301"
        response = client.get("/ping", headers={"X-Request-Id": uuid_like})
        self.assertEqual(response.headers.get("X-Request-Id"), uuid_like)


if __name__ == '__main__':
    unittest.main()
