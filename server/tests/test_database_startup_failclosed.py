"""P-19 · Arranque fail-closed de la base de datos.

P-19 dice: *«Cierre: `DATABASE_URL` inválida aborta el arranque; `alembic
upgrade head` funciona en limpio.»*

La mitad del "fallback silencioso a SQLite" ya está corregida en
`server/src/database.py`. Este test vigila que el control **no se desconecte**:
si alguien reintroduce el `except` que cae a SQLite, el test falla.

Regla 5 del registro: *«Un control desconectado no existe.»*
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


_ENV_KEYS = ("DATABASE_URL", "ENVIRONMENT", "RENDER")


def _reload_database_module(env: dict):
    """Recarga `src.database` con un entorno concreto.

    Recargar es necesario porque `src.database` lee `DATABASE_URL` y decide el
    modo (producción/desarrollo) **en el momento del import**, no por llamada.

    El entorno se aplica **durante** el reload y se restaura después; las
    llamadas que sí dependan del entorno en tiempo de ejecución (por ejemplo
    `_is_production()`) deben usar `patch.dict` explícito en el test.

    Las variables que **no** vienen en `env` se eliminan durante el reload
    para no heredar el valor del proceso de pruebas. Se usa `patch.dict` con
    `clear=False` y se restauran a mano las variables tocadas: `patch.dict`
    solo restaura las que existían al entrar, no las que se han eliminado
    durante el bloque.
    """
    import importlib

    import src.database as database_module

    saved = {key: os.environ.get(key) for key in _ENV_KEYS}

    try:
        for key in _ENV_KEYS:
            if key not in env:
                os.environ.pop(key, None)
        os.environ.update(env)
        return importlib.reload(database_module)
    finally:
        # Restauración exacta: lo que estaba y lo que no.
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class TestDatabaseUrlFailClosed(unittest.TestCase):
    """P-19: una `DATABASE_URL` inválida aborta el arranque."""

    def test_malformed_database_url_raises_at_import(self):
        """Una URL que no es una URL de BD debe abortar el import.

        Antes: `except` -> `logger.critical(...)` -> SQLite de emergencia y la
        app "arrancaba" con los datos en un fichero efímero.
        """
        with self.assertRaises(RuntimeError) as ctx:
            _reload_database_module(
                {
                    "DATABASE_URL": "esto-no-es-una-url-de-bd",
                    "ENVIRONMENT": "production",
                    "RENDER": "true",
                }
            )
        message = str(ctx.exception)
        self.assertIn("DATABASE_URL", message)
        self.assertIn("Arranque abortado", message)

    def test_error_message_does_not_leak_credentials(self):
        """El mensaje de arranque no debe filtrar la contraseña de la URL.

        Capa de conectividad: es aquí donde una URL con credenciales acaba
        apareciendo en el mensaje del driver (`could not connect to server:
        postgresql://usuario:secreto123@host/db`), y por eso hay que
        enmascararla.
        """
        module = _reload_database_module(
            {
                "DATABASE_URL": "sqlite:///./scratch/p19_test.db",
                "ENVIRONMENT": "production",
                "RENDER": "true",
            }
        )

        leaked = OSError(
            "could not connect to server: postgresql://usuario:secreto123@host/db"
        )
        with patch.object(module, "_is_production", return_value=True):
            with patch.object(module.engine, "connect", side_effect=leaked):
                with self.assertRaises(RuntimeError) as ctx:
                    module._assert_database_reachable()

        message = str(ctx.exception)
        self.assertNotIn("secreto123", message)
        self.assertIn("usuario:***@host", message)

    def test_no_silent_sqlite_fallback_in_source(self):
        """El fuente no debe contener un fallback silencioso a SQLite.

        Control estático: es la red de seguridad que sobrevive a que alguien
        "arregle" el arranque borrando la rama `raise`.
        """
        import src.database as database_module

        source_path = database_module.__file__
        with open(source_path, "r", encoding="utf-8") as fh:
            source = fh.read()

        self.assertNotIn(
            "Usando SQLite fallback",
            source,
            "P-19: reintroducido el fallback silencioso a SQLite.",
        )
        self.assertNotIn(
            'DB_URL = "sqlite:///./bi_agent.db"',
            source,
            "P-19: reintroducido el fallback silencioso a SQLite.",
        )

    def test_valid_sqlite_url_still_works_in_development(self):
        """SQLite explícito (desarrollo local) sigue funcionando.

        El endurecimiento no puede romper el flujo local: SQLite es una
        configuración legítima, lo que no es legítimo es *caerse* a SQLite.
        """
        module = _reload_database_module(
            {
                "DATABASE_URL": "sqlite:///./scratch/p19_test.db",
                "ENVIRONMENT": "development",
                "RENDER": "false",
            }
        )
        self.assertEqual(module.engine.dialect.name, "sqlite")


class TestDatabaseReachability(unittest.TestCase):
    """P-19: una BD configurada pero inalcanzable aborta en producción."""

    def test_unreachable_database_aborts_startup_in_production(self):
        """Postgres bien formado pero con host inexistente -> arranque aborta.

        `create_engine()` es perezoso: no abre conexión. Por eso hace falta
        además una comprobación de conectividad; sin ella, el host inválido
        solo se descubre en la primera petición.
        """
        module = _reload_database_module(
            {
                "DATABASE_URL": "sqlite:///./scratch/p19_test.db",
                "ENVIRONMENT": "production",
                "RENDER": "true",
            }
        )

        # Se parchea `_is_production` (no el entorno): otros archivos de test
        # mutan `os.environ["ENVIRONMENT"]` a nivel de módulo y filtran el
        # estado entre suites. El test debe depender de lo que prueba, no de
        # lo que dejó el test anterior.
        with patch.object(module, "_is_production", return_value=True):
            with patch.object(
                module.engine,
                "connect",
                side_effect=OSError("could not connect to server"),
            ):
                with self.assertRaises(RuntimeError) as ctx:
                    module._assert_database_reachable()

        message = str(ctx.exception)
        self.assertIn("no responde", message)
        self.assertIn("Arranque abortado", message)

    def test_unreachable_database_is_tolerated_in_development(self):
        """En desarrollo local se avisa pero no se aborta.

        El developer puede estar levantando la BD en otro momento; bloquearle
        el arranque local solo genera fricción.
        """
        module = _reload_database_module(
            {
                "DATABASE_URL": "sqlite:///./scratch/p19_test.db",
                "ENVIRONMENT": "development",
                "RENDER": "false",
            }
        )

        with patch.object(module, "_is_production", return_value=False):
            with patch.object(
                module.engine,
                "connect",
                side_effect=OSError("could not connect to server"),
            ):
                module._assert_database_reachable()  # no debe lanzar


class TestInitDbFailClosed(unittest.TestCase):
    """P-19: `init_db()` aborta en producción si el esquema no se puede crear."""

    def test_init_db_raises_in_production_on_schema_error(self):
        module = _reload_database_module(
            {
                "DATABASE_URL": "sqlite:///./scratch/p19_test.db",
                "ENVIRONMENT": "production",
                "RENDER": "true",
            }
        )

        with patch.object(module, "_is_production", return_value=True):
            with patch.object(
                module.Base.metadata, "create_all", side_effect=RuntimeError("boom")
            ):
                with self.assertRaises(RuntimeError) as ctx:
                    module.init_db()

        self.assertIn("Arranque abortado", str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
