"""Regresión del diagnóstico de Storage (P-50).

Caso real (2026-10-19): ``SUPABASE_URL`` tenía un typo (``hhttps://...``) y la
clave era del formato nuevo (``sb_secret_...``). El cliente no se creaba,
``/upload`` devolvía 503 y ``/health`` decía ``not_configured`` aunque las dos
variables estuvieran definidas, así que la causa era invisible.

Ahora ``/health`` publica el motivo real (``invalid_url``, ``invalid_api_key``,
``client_init_failed``) sin exponer credenciales, y el log dice qué revisar.
"""
import logging
import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services import storage_service as storage  # noqa: E402

URL_VALIDA = "https://ejemplo.supabase.co"
CLAVE_NUEVA = "sb_secret_" + "x" * 32
CLAVE_JWT_FALSA = "eyJhbGciOiJIUzI1NiJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIn0.firma"


@pytest.fixture(autouse=True)
def _estado_limpio(monkeypatch):
    """Aísla cada test del .env del proyecto y de la caché del probe."""
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    storage._probe_cache.update(ok=None, reason=None, ts=0.0)
    storage._last_client_error = None
    yield
    storage._probe_cache.update(ok=None, reason=None, ts=0.0)
    storage._last_client_error = None


def test_sin_credenciales_reporta_not_configured():
    assert storage.storage_configured() is False
    assert storage.probe_bucket(force=True) == {"ok": False, "reason": "not_configured"}


def test_url_con_typo_reporta_invalid_url(monkeypatch, caplog):
    monkeypatch.setenv("SUPABASE_URL", "hhttps://ejemplo.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", CLAVE_NUEVA)

    with caplog.at_level(logging.ERROR, logger=storage.logger.name):
        assert storage.get_supabase_client() is None
        probe = storage.probe_bucket(force=True)

    # Antes: {"ok": False, "reason": "not_configured"} con credenciales presentes.
    assert probe == {"ok": False, "reason": "invalid_url"}
    # El log debe ser accionable y no contener la credencial.
    assert "invalid_url" in caplog.text
    assert CLAVE_NUEVA not in caplog.text


def test_url_vacia_pero_clave_presente_no_rompe(monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", CLAVE_NUEVA)
    assert storage.get_supabase_client() is None
    assert storage.probe_bucket(force=True) == {"ok": False, "reason": "not_configured"}


def test_clave_nueva_sb_secret_crea_cliente(monkeypatch):
    """Regresión del bug real: supabase-py 2.10.0 rechazaba ``sb_secret_...``."""
    monkeypatch.setenv("SUPABASE_URL", URL_VALIDA)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", CLAVE_NUEVA)
    assert storage.get_supabase_client() is not None


def test_clave_jwt_legacy_sigue_funcionando(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", URL_VALIDA)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", CLAVE_JWT_FALSA)
    assert storage.get_supabase_client() is not None
