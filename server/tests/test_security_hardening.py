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

    def test_todas_las_ips_del_dns_se_validan(self, monkeypatch):
        """P-33: un registro DNS privado secundario no puede colarse (antes solo se miraba el primero)."""
        import socket

        monkeypatch.delenv("ALLOWED_SQL_HOSTS", raising=False)
        monkeypatch.delenv("RENDER", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "development")

        def fake_getaddrinfo(host, port, *args, **kwargs):
            return [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.7", 0)),
            ]

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
        with pytest.raises(ValueError):
            validate_external_url_host("postgresql://u:p@rebind.example.com/db")

    def test_produccion_exige_allowlist_sql(self, monkeypatch):
        """P-33: en producción sin ALLOWED_SQL_HOSTS se rechaza (fail-closed)."""
        monkeypatch.delenv("ALLOWED_SQL_HOSTS", raising=False)
        monkeypatch.delenv("RENDER", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "production")
        with pytest.raises(ValueError):
            validate_external_url_host("postgresql://u:p@db.example.com/prod")

    @pytest.mark.parametrize("url", [
        "sqlite:////etc/passwd",
        "file:///etc/passwd",
        "duckdb:///tmp/x.duckdb",
    ])
    def test_esquemas_locales_bloqueados(self, monkeypatch, url):
        """P-33: la allowlist de esquemas impide leer archivos locales vía URL de conexión."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        with pytest.raises(ValueError):
            validate_external_url_host(url)

    def test_get_sql_engine_valida_ssrf(self, monkeypatch):
        """P-33: el punto único de creación de motores también valida la URL."""
        from src.connectors.data_connectors import get_sql_engine

        monkeypatch.delenv("ALLOWED_SQL_HOSTS", raising=False)
        monkeypatch.delenv("RENDER", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "production")
        with pytest.raises(ValueError):
            get_sql_engine("postgresql://u:p@10.0.0.5/db")


class TestRateLimitKey:
    """P-31: la clave del rate limiter no se puede evadir con X-Forwarded-For."""

    @staticmethod
    def _request(headers=None):
        from starlette.requests import Request
        return Request({
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": headers or [],
            "client": ("203.0.113.9", 1234),
        })

    def test_usa_la_ip_del_par_tcp_no_x_forwarded_for(self, monkeypatch):
        import src.utils.common as common
        from src.utils.limiter import get_user_or_ip

        monkeypatch.setattr(common, "get_authenticated_user", lambda: None)
        req = self._request([(b"x-forwarded-for", b"9.9.9.9")])
        assert get_user_or_ip(req) == "203.0.113.9"

    def test_prioriza_el_usuario_autenticado(self, monkeypatch):
        import src.utils.common as common
        from src.utils.limiter import get_user_or_ip

        monkeypatch.setattr(common, "get_authenticated_user", lambda: "user@example.com")
        assert get_user_or_ip(self._request()) == "user@example.com"


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
