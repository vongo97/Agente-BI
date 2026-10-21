"""
Regresión P-51: el sandbox bloqueaba `time`, que pandas/numpy importan en runtime.
El resultado era que *todo* análisis fallaba con ImportError, aunque el código
generado fuera correcto.

También se comprueba que los módulos peligrosos siguen bloqueados.
"""
import os
import sys

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_sandbox.db")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.engine.executor import get_safe_environment, validate_code_safety, SecurityError


class TestSandboxImports:
    def test_time_esta_permitido(self):
        """pandas/numpy lo necesitan; sin él no se puede analizar nada."""
        env = get_safe_environment()
        exec("import time\nresultado = time.time() > 0", env, env)
        assert env["resultado"] is True

    def test_os_sigue_bloqueado(self):
        env = get_safe_environment()
        with pytest.raises(ImportError):
            exec("import os", env, env)

    def test_subprocess_sigue_bloqueado(self):
        env = get_safe_environment()
        with pytest.raises(ImportError):
            exec("import subprocess", env, env)


class TestSandboxRename:
    """P-52: `rename` en la lista AST bloqueaba pandas.DataFrame.rename()."""

    def test_dataframe_rename_esta_permitido(self):
        codigo = "resultado = df.rename(columns={'ventas': 'total_ventas'})"
        assert validate_code_safety(codigo) is True

    def test_os_rename_sigue_bloqueado(self):
        with pytest.raises(SecurityError):
            validate_code_safety("import os\nos.rename('a.csv', 'b.csv')")
