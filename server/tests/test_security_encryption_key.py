"""
Tests de robustez del cifrado de API keys (Vektra BI).

Contexto: en Render, una ENCRYPTION_KEY mal formada (por ejemplo un hash hex de
32 bytes en vez de una clave Fernet) provocaba un ValueError en el import de
src/utils/security.py y tumbaba TODO el backend en bucle de reinicio. Estos tests
fijan el comportamiento requerido: el servicio arranca siempre y la clave efectiva
es estable entre reinicios.
"""
import base64
import hashlib
import importlib
import os
import sys

import pytest
from cryptography.fernet import Fernet

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _reload_security(monkeypatch, value):
    """Recarga src.utils.security con la variable de entorno indicada."""
    if value is None:
        monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    else:
        monkeypatch.setenv("ENCRYPTION_KEY", value)
    import src.utils.security as sec
    return importlib.reload(sec)


class TestEncryptionKeyRobustez:
    def test_clave_valida_se_usa_tal_cual(self, monkeypatch):
        key = Fernet.generate_key().decode()
        sec = _reload_security(monkeypatch, key)
        assert sec.ENCRYPTION_KEY == key

    def test_clave_mal_formada_no_tumba_el_servicio(self, monkeypatch):
        """Hex de 32 bytes: valor muy probable por error, antes causaba crash."""
        hex_key = "a" * 64
        sec = _reload_security(monkeypatch, hex_key)
        # Debe arrancar y exponer una clave Fernet válida
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

    def test_sin_variable_genera_temporal_sin_crash(self, monkeypatch):
        sec = _reload_security(monkeypatch, None)
        assert Fernet(sec.ENCRYPTION_KEY.encode()) is not None

    def test_idempotencia_de_cifrado(self, monkeypatch):
        sec = _reload_security(monkeypatch, Fernet.generate_key().decode())
        key = "sk-idem-999"
        # Un valor ya cifrado no se vuelve a cifrar
        once = sec.encrypt_key(key)
        assert sec.encrypt_key(once) == once
        assert sec.decrypt_key(once) == key