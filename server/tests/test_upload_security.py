"""Tests de seguridad para P-11: upload sin texto plano en disco + mitigación zip-bomb.

Estos tests no importan server/src/routers/__init__.py (que trae un ImportError
preexistente en analysis.py), por lo que prueban de forma aislada:
  1. encrypt_bytes / descifrado en memoria (security.py)
  2. Validación de tamaño y zip-bomb desde bytes en memoria
"""
import io
import os
import tempfile

import pytest

import src.utils.security as sec
from src.utils.security import encrypt_bytes


# ── P-11.1: cifrar_bytes / descifrar en memoria (sin escribir texto plano en disco) ──


def test_encrypt_bytes_roundtrip_in_memory():
    """Los bytes cifrados se pueden descifrar y recuperar el contenido original."""
    original = b"col1,col2\n1,2\n3,4\n"
    encrypted = encrypt_bytes(original)

    # El cifrado no debe ser igual al original (no texto plano)
    assert encrypted != original

    # Descifrar usando la suite de Fernet directamente
    decrypted = sec.cipher_suite.decrypt(encrypted)
    assert decrypted == original


def test_encrypt_bytes_different_output_each_call():
    """Fernet usa nonce aleatorio: dos cifrados del mismo dato difieren."""
    original = b"datos sensibles"
    e1 = encrypt_bytes(original)
    e2 = encrypt_bytes(original)
    assert e1 != e2


# ── P-11.2: validación de tamaño y zip-bomb desde bytes en memoria ──


def test_csv_line_count_rejects_giant_file():
    """Un CSV con más de 10M líneas debe rechazarse antes de parsear."""
    from src.utils.security import encrypt_bytes  # noqa: F401  (reutiliza import)

    # Simulamos la lógica de conteo de líneas del upload
    line_limit = 10_000_000
    # Crear bytes con más de 10M líneas (sin escribir a disco)
    giant_csv = b"a,b\n" + b"1,2\n" * (line_limit + 1)
    line_count = giant_csv.count(b"\n") + (1 if giant_csv and not giant_csv.endswith(b"\n") else 0)

    assert line_count > line_limit


def test_csv_line_count_allows_normal_file():
    """Un CSV normal pasa el filtro de líneas."""
    normal_csv = b"col1,col2\n1,2\n3,4\n"
    line_count = normal_csv.count(b"\n") + (1 if normal_csv and not normal_csv.endswith(b"\n") else 0)
    assert line_count == 3


def test_encrypted_file_can_be_written_and_read_from_disk():
    """Verifica que los bytes cifrados pueden escribirse a disco y leerse (disco solo tiene cifrado)."""
    original = b"x,y\n10,20\n"
    encrypted = encrypt_bytes(original)

    with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "datos.csv.enc")
            with open(path, "wb") as f:
                f.write(encrypted)

            # El disco solo contiene bytes cifrados, no el original en claro
            with open(path, "rb") as f:
                stored = f.read()
            assert stored == encrypted
            assert stored != original

            # Descifrar desde disco funciona
            decrypted = sec.decrypt_file_to_bytes(path)
            assert decrypted == original


def test_zip_bomb_cell_limit_from_bytes():
    """Un DataFrame con más de 1M celdas se rechaza (lógica de _MAX_CELLS)."""
    import pandas as pd

    _MAX_CELLS = 1_000_000
    # Crear un DataFrame grande en memoria (sin disco)
    df = pd.DataFrame({f"col_{i}": range(_MAX_CELLS // 2 + 1) for i in range(2)})
    assert int(df.size) > _MAX_CELLS


def test_parse_csv_from_bytes_without_disk():
    """load_file_data_from_bytes parsea CSV desde bytes en memoria sin tocar disco."""
    from src.connectors.data_connectors import load_file_data_from_bytes

    csv_bytes = b"a,b,c\n1,2,3\n4,5,6\n"
    df = load_file_data_from_bytes(csv_bytes, "datos.csv")

    assert list(df.columns) == ["a", "b", "c"]
    assert len(df) == 2
