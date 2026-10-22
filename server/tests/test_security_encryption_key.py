"""
Tests de robustez del cifrado de API keys (Vektra BI) — P-10.

Contexto:
- En producción o Render, la ausencia de ENCRYPTION_KEY debe abortar (fail-closed)
  para evitar generar claves efímeras que corrompan los datos tras reiniciar.
- En desarrollo local, se genera un fallback determinista para no quebrar la sesión.
- Una clave mal formada en variable se deriva determinísticamente con SHA-256.
- encrypt_key y decrypt_key nunca aceptan ni persisten texto plano (P-10).
"""
import base64
import hashlib
import importlib
import os
import sys

import pytest
from cryptography.fernet import Fernet

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _reload_security(monkeypatch, value, environment="development", render=None):
    """Recarga src.utils.security con la configuración indicada."""
    import dotenv
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **kw: None)

    if value is None:
        monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    else:
        monkeypatch.setenv("ENCRYPTION_KEY", value)

    if environment is None:
        monkeypatch.delenv("ENVIRONMENT", raising=False)
    else:
        monkeypatch.setenv("ENVIRONMENT", environment)

    if render is None:
        monkeypatch.delenv("RENDER", raising=False)
    else:
        monkeypatch.setenv("RENDER", render)

    import src.utils.security as sec
    return importlib.reload(sec)


class TestEncryptionKeyRobustez:
    def test_clave_valida_se_usa_tal_cual(self, monkeypatch):
        key = Fernet.generate_key().decode()
        sec = _reload_security(monkeypatch, key)
        assert sec.ENCRYPTION_KEY == key

    def test_clave_mal_formada_no_tumba_el_servicio(self, monkeypatch):
        """Hex de 32 bytes: se deriva clave determinista con SHA-256."""
        hex_key = "a" * 64
        sec = _reload_security(monkeypatch, hex_key)
        token = sec.encrypt_key("sk-test-123")
        assert token.startswith("gAAAA")
        assert sec.decrypt_key(token) == "sk-test-123"

    def test_clave_derivada_es_estable_entre_reinicios(self, monkeypatch):
        hex_key = "b" * 64
        sec1 = _reload_security(monkeypatch, hex_key)
        first = sec1.ENCRYPTION_KEY
        sec2 = _reload_security(monkeypatch, hex_key)
        assert sec2.ENCRYPTION_KEY == first

    def test_clave_derivada_es_fernet_valida(self, monkeypatch):
        sec = _reload_security(monkeypatch, "clave-corta")
        assert Fernet(sec.ENCRYPTION_KEY.encode()) is not None
        assert len(base64.urlsafe_b64decode(sec.ENCRYPTION_KEY)) == 32

    def test_derivacion_no_colisiona_entre_valores_distintos(self, monkeypatch):
        a = _reload_security(monkeypatch, "clave-a").ENCRYPTION_KEY
        b = _reload_security(monkeypatch, "clave-b").ENCRYPTION_KEY
        assert a != b

    def test_sin_variable_en_desarrollo_usa_fallback_determinista(self, monkeypatch):
        sec = _reload_security(monkeypatch, None, environment="development")
        assert Fernet(sec.ENCRYPTION_KEY.encode()) is not None
        # Debe ser estable entre recargas en dev
        sec2 = _reload_security(monkeypatch, None, environment="development")
        assert sec.ENCRYPTION_KEY == sec2.ENCRYPTION_KEY

    def test_sin_variable_en_produccion_falla_con_runtime_error(self, monkeypatch):
        with pytest.raises(RuntimeError) as exc_info:
            _reload_security(monkeypatch, None, environment="production")
        assert "ENCRYPTION_KEY" in str(exc_info.value)

    def test_sin_variable_en_render_falla_con_runtime_error(self, monkeypatch):
        with pytest.raises(RuntimeError) as exc_info:
            _reload_security(monkeypatch, None, environment="development", render="true")
        assert "ENCRYPTION_KEY" in str(exc_info.value)

    def test_idempotencia_de_cifrado(self, monkeypatch):
        sec = _reload_security(monkeypatch, Fernet.generate_key().decode())
        key = "sk-idem-999"
        once = sec.encrypt_key(key)
        assert sec.encrypt_key(once) == once
        assert sec.decrypt_key(once) == key

    def test_decrypt_key_rechaza_texto_plano(self, monkeypatch):
        sec = _reload_security(monkeypatch, Fernet.generate_key().decode())
        # Texto plano que no empieza con gAAAA no debe devolverse como válido
        assert sec.decrypt_key("sk-plaintext-unencrypted") is None
