"""Regresión P-47: una migración fallida no debe bloquear las siguientes.

En PostgreSQL, un ALTER TABLE que falla porque la columna ya existe deja la
transacción abortada. El código anterior reutilizaba la misma conexión, así que
si ``is_encrypted`` ya existía, ``size_bytes`` nunca se agregaba y /upload
respondía 500 en producción.
"""
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database import db_schema_diagnostic, init_db


def test_init_db_adds_missing_columns_after_existing_column(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE data_sources ("
                "id INTEGER PRIMARY KEY, user_id VARCHAR, name VARCHAR, "
                "type VARCHAR, url TEXT, columns TEXT, "
                "is_encrypted BOOLEAN, created_at DATETIME)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE user_configs ("
                "id INTEGER PRIMARY KEY, user_id VARCHAR UNIQUE)"
            )
        )

    with patch("src.database.engine", engine):
        init_db()

    data_source_columns = {
        column["name"] for column in inspect(engine).get_columns("data_sources")
    }
    user_config_columns = {
        column["name"] for column in inspect(engine).get_columns("user_configs")
    }

    assert "is_encrypted" in data_source_columns
    assert "size_bytes" in data_source_columns
    assert "brand_color" in user_config_columns
    assert "pdf_orientation" in user_config_columns

    with patch("src.database.engine", engine):
        assert db_schema_diagnostic()["upload_schema_ready"] is True
