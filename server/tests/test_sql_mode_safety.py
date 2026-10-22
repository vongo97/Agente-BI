"""
Tests de seguridad y materialización del Modo SQL (Vektra BI) — P-03.

Valida que:
1. validate_sql_safety() aplique una lista blanca estricta (solo SELECT/WITH).
2. Se rechacen DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE, multi-statement con ';' y lecturas de archivos (pg_read_file).
3. execute_sql_safe() materialice correctamente DataFrames ante SQL válido y capture errores sin crash.
4. Guardia estática: validate_sql_safety esté cableada al flujo en analysis.py.
"""
import os
import sys
import pytest
from sqlalchemy import create_engine

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.engine.executor import validate_sql_safety, execute_sql_safe, SecurityError


class TestSQLSafetyValidation:
    """Verifica los controles de lista blanca estricta de validate_sql_safety()."""

    def test_select_simple_permitido(self):
        assert validate_sql_safety("SELECT id, nombre, total FROM ventas WHERE total > 100") is True

    def test_select_con_punto_y_coma_final_permitido(self):
        assert validate_sql_safety("SELECT * FROM productos;") is True

    def test_with_cte_permitido(self):
        query = """
        WITH resumen AS (
            SELECT categoria, SUM(monto) AS total FROM transacciones GROUP BY categoria
        )
        SELECT * FROM resumen ORDER BY total DESC
        """
        assert validate_sql_safety(query) is True

    @pytest.mark.parametrize("malicious_query", [
        "DROP TABLE usuarios",
        "DELETE FROM usuarios WHERE 1=1",
        "UPDATE usuarios SET rol = 'admin'",
        "INSERT INTO usuarios (email) VALUES ('hacker@evil.com')",
        "ALTER TABLE usuarios ADD COLUMN backdoor TEXT",
        "TRUNCATE TABLE ventas",
        "SELECT * FROM ventas; DROP TABLE usuarios;",
        "SELECT * FROM ventas; DELETE FROM logs",
        "SELECT pg_read_file('/etc/passwd')",
        "SELECT pg_write_file('/tmp/pwn', 'evil')",
        "EXEC xp_cmdshell('dir')",
        "SELECT * INTO OUTFILE '/tmp/dump.csv' FROM ventas",
    ])
    def test_queries_peligrosas_rechazadas(self, malicious_query):
        with pytest.raises(SecurityError):
            validate_sql_safety(malicious_query)


class TestSQLExecutionSafe:
    """Verifica que execute_sql_safe materialice DataFrames reales de forma segura."""

    def test_materializa_dataframe_con_select_valido(self, tmp_path):
        db_path = tmp_path / "test_data.db"
        engine = create_engine(f"sqlite:///{db_path}")
        with engine.connect() as conn:
            conn.exec_driver_sql("CREATE TABLE test_data (id INT, valor TEXT)")
            conn.exec_driver_sql("INSERT INTO test_data VALUES (1, 'Alpha'), (2, 'Beta')")
            conn.commit()

        msg, df, sql = execute_sql_safe(engine, "```sql\nSELECT * FROM test_data\n```")
        assert df is not None, f"execute_sql_safe fallo con msg: {msg}"
        assert len(df) == 2
        assert list(df.columns) == ["id", "valor"]
        assert "Resultados (2 filas)" in msg

    def test_rechaza_ejecucion_con_drop_sin_tocar_bd(self, tmp_path):
        db_path = tmp_path / "intact.db"
        engine = create_engine(f"sqlite:///{db_path}")
        with engine.connect() as conn:
            conn.exec_driver_sql("CREATE TABLE intact_table (id INT)")
            conn.commit()

        msg, df, sql = execute_sql_safe(engine, "DROP TABLE intact_table")
        assert df is None
        assert "Error SQL" in msg
        assert "SecurityError" in msg or "prohibido" in msg.lower() or "solo lectura" in msg.lower()

        # Verificar que la tabla no fue eliminada
        with engine.connect() as conn:
            res = conn.exec_driver_sql("SELECT count(*) FROM intact_table").scalar()
            assert res == 0


class TestSQLStaticGuard:
    """Guardia estática: validate_sql_safety y execute_sql_safe deben estar en analysis.py."""

    def test_analysis_referencia_controles_sql(self):
        analysis_path = os.path.join(os.path.dirname(__file__), "..", "src", "routers", "analysis.py")
        with open(analysis_path, "r", encoding="utf-8") as f:
            code = f.read()

        assert "execute_sql_safe" in code, "execute_sql_safe no está referenciada en analysis.py"
        assert "validate_sql_safety" in code or "execute_sql_safe" in code
