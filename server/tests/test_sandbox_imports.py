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


class TestSandboxP16Hardening:
    """P-16: Bloqueo exhaustivo de I/O a disco/red y reflexión dinámica en el AST."""

    def test_to_csv_bloqueado_en_ast(self):
        with pytest.raises(SecurityError):
            validate_code_safety("df.to_csv('leak.csv')")

    def test_read_table_bloqueado_en_ast(self):
        with pytest.raises(SecurityError):
            validate_code_safety("pd.read_table('leak.txt')")

    def test_numpy_save_bloqueado_en_ast(self):
        with pytest.raises(SecurityError):
            validate_code_safety("np.save('leak.npy', arr)")

    def test_plt_savefig_bloqueado_en_ast(self):
        with pytest.raises(SecurityError):
            validate_code_safety("plt.savefig('leak.png')")

    def test_getattr_dinamico_bloqueado_en_ast(self):
        with pytest.raises(SecurityError):
            validate_code_safety("func = getattr(pd, 'read_csv')")

    def test_setattr_dinamico_bloqueado_en_ast(self):
        with pytest.raises(SecurityError):
            validate_code_safety("setattr(obj, 'attr', 123)")

    def test_operaciones_legitimas_permitidas(self):
        codigo = """
total = df['ventas'].sum()
media = df['ventas'].mean()
agrupado = df.groupby('categoria')['ventas'].agg(['count', 'sum'])
resultado = agrupado.reset_index()
"""
        assert validate_code_safety(codigo) is True
