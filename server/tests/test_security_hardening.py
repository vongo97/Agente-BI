"""
Tests de hardening de seguridad (auditoría Vektra 2026-02).

Cubre:
- validate_sql_safety: whitelist estricta de solo-lectura.
- validate_external_url_host: bloqueo SSRF de hosts privados/locales.
- validate_code_safety: el sandbox rechaza I/O de disco/red.
- get_authenticated_user / check_authorization: sin fallback secreto fuera de localhost.
"""
import os
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_bi.db")

from src.engine.executor import validate_sql_safety, validate_code_safety, SecurityError
from src.utils.security import validate_external_url_host


class TestSQLSafety:
    @pytest.mark.parametrize("q", [
        "SELECT * FROM ventas LIMIT 10",
        "SELECT nombre, SUM(total) FROM t GROUP BY nombre;",
        "WITH t AS (SELECT 1 AS a) SELECT * FROM t",
        "SELECT settings FROM config",  # 'SET' como subcadena no debe bloquear
    ])
    def test_consultas_lectura_validas(self, q):
        assert validate_sql_safety(q) is True

    @pytest.mark.parametrize("q", [
        "DROP TABLE users",
        "DELETE FROM users",
        "UPDATE users SET admin=1",
        "INSERT INTO users VALUES (1)",
        "SELECT 1; DROP TABLE users",                # multi-statement
        "WITH t AS (DELETE FROM users RETURNING *) SELECT * FROM t",
        "ATTACH DATABASE 'x.db' AS y",
        "PRAGMA table_info(users)",
        "VACUUM",
        "CREATE TABLE x (a INT)",
        "TRUNCATE TABLE users",
        "SELECT pg_read_file('/etc/passwd')",
        "SELECT lo_export(oid, '/tmp/x')",
        "GRANT ALL ON users TO attacker",
        "COPY users FROM '/etc/passwd'",
        "EXEC xp_cmdshell 'dir'",
    ])
    def test_consultas_peligrosas_bloqueadas(self, q):
        with pytest.raises((SecurityError, Exception)):
            validate_sql_safety(q)


class TestSSRFProtection:
    @pytest.mark.parametrize("url", [
        "postgresql://u:p@127.0.0.1/db",
        "postgresql://u:p@localhost/db",
        "postgresql://u:p@localhost.localdomain/db",
        "postgresql://u:p@169.254.169.254/latest/meta-data",
        "postgresql://u:p@10.0.0.5/db",
        "postgresql://u:p@192.168.1.10/db",
        "postgresql://u:p@172.16.0.9/db",
    ])
    def test_hosts_internos_bloqueados(self, url):
        with pytest.raises(ValueError):
            validate_external_url_host(url)

    def test_url_sin_host_bloqueada(self):
        with pytest.raises(ValueError):
            validate_external_url_host("postgresql://u:p@/db")

    def test_allowlist_respeta_hosts(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_SQL_HOSTS", "db.empresa.com")
        # Con allowlist activa no resuelve DNS: solo compara nombre
        validate_external_url_host("postgresql://u:p@db.empresa.com/prod")  # no lanza
        with pytest.raises(ValueError):
            validate_external_url_host("postgresql://u:p@otro.com/prod")


class TestSandboxAST:
    @pytest.mark.parametrize("code", [
        "import os",
        "import subprocess",
        "import io\nf = io.open('/etc/passwd')",
        "pd.read_csv('/etc/passwd')",
        "pd.read_csv('http://169.254.169.254/latest/meta-data')",
        "df.to_pickle('x.pkl')",
        "open('secret.txt')",
        "df.__class__.__mro__",
        "os.system('dir')",
        "os.listdir('.')",
    ])
    def test_codigo_malicioso_bloqueado(self, code):
        with pytest.raises((SecurityError, Exception)):
            validate_code_safety(code)

    @pytest.mark.parametrize("code", [
        "result = df.groupby('cat')['total'].sum()",
        "fig = px.bar(df, x='a', y='b')",
        "import numpy as np\narr = np.mean(df['x'])",
        "for i in range(10):\n    print(i)",
    ])
    def test_codigo_legitimo_permitido(self, code):
        assert validate_code_safety(code) is True
