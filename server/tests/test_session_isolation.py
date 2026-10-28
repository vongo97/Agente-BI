"""
Tests de aislamiento de sesiones por chat_id (P-34).

Verifica que dos conversaciones distintas no se pisen mutuamente:
cada chat debe tener su propia sesión de datos aislada.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from src.utils.common import (
    get_session_key,
    get_session_file,
    get_user_data,
    save_user_data,
    data_store,
)


def test_get_session_key_differs_by_chat():
    """get_session_key debe devolver claves distintas para distintos chats."""
    key_active = get_session_key("usuario@test.com", None)
    key_chat_1 = get_session_key("usuario@test.com", 1)
    key_chat_2 = get_session_key("usuario@test.com", 2)

    assert key_active != key_chat_1
    assert key_chat_1 != key_chat_2
    assert key_active == "usuario@test.com_active"
    assert key_chat_1 == "usuario@test.com_chat_1"
    assert key_chat_2 == "usuario@test.com_chat_2"


def test_get_session_file_differs_by_chat():
    """get_session_file debe devolver rutas de archivo distintas por chat."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Monkey-patch SESSIONS_DIR para usar directorio temporal
        import src.utils.common as common
        original_dir = common.SESSIONS_DIR
        common.SESSIONS_DIR = tmpdir
        try:
            path_active = get_session_file("usuario@test.com", None)
            path_chat_1 = get_session_file("usuario@test.com", 1)
            path_chat_2 = get_session_file("usuario@test.com", 2)

            assert path_active != path_chat_1
            assert path_chat_1 != path_chat_2
            assert path_active.endswith(".pkl")
            assert path_chat_1.endswith("_chat_1.pkl")
            assert path_chat_2.endswith("_chat_2.pkl")
        finally:
            common.SESSIONS_DIR = original_dir


def test_missing_chat_session_does_not_inherit_the_active_user_pool(tmp_path, monkeypatch):
    import src.utils.common as common

    common.data_store.clear()
    monkeypatch.setattr(common, "SESSIONS_DIR", str(tmp_path))
    monkeypatch.setattr(common, "sync_cloud_to_local", lambda *_args, **_kwargs: False)
    active_key = common.get_session_key("usuario@test.com")
    common.data_store[active_key] = {"type": "file", "data": {"private": [1]}, "sources": [91]}

    assert common.get_user_data("usuario@test.com", chat_id=42) is None
    assert common.data_store[active_key]["sources"] == [91]
    common.data_store.clear()


def test_save_and_load_user_data_isolated_by_chat():
    """save_user_data y get_user_data deben aislar datos por chat_id."""
    import src.utils.common as common
    # Limpiar data_store para evitar contaminación entre tests
    common.data_store.clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = common.SESSIONS_DIR
        common.SESSIONS_DIR = tmpdir
        try:
            # Guardar datos distintos para dos chats
            save_user_data("usuario@test.com", {"type": "file", "data": {"chat1": [1, 2]}, "sources": []}, chat_id=1)
            save_user_data("usuario@test.com", {"type": "file", "data": {"chat2": [3, 4]}, "sources": []}, chat_id=2)

            # Cada chat debe leer sus propios datos
            data_chat1 = get_user_data("usuario@test.com", chat_id=1)
            data_chat2 = get_user_data("usuario@test.com", chat_id=2)

            assert data_chat1 is not None
            assert data_chat2 is not None
            assert data_chat1["data"] == {"chat1": [1, 2]}
            assert data_chat2["data"] == {"chat2": [3, 4]}
            assert data_chat1["data"] != data_chat2["data"]

            # La sesión activa (sin chat_id) debe estar vacía o ser distinta
            data_active = get_user_data("usuario@test.com", None)
            # Puede ser None si no se guardó nada sin chat_id
            if data_active is not None:
                assert data_active["data"] != {"chat1": [1, 2]}
        finally:
            common.SESSIONS_DIR = original_dir
            common.data_store.clear()


def test_data_store_keys_are_chat_specific():
    """Las claves de data_store deben incluir el chat_id."""
    import src.utils.common as common
    common.data_store.clear()

    try:
        # Simular lo que hace get_user_data internamente
        key_chat_1 = common.get_session_key("usuario@test.com", 1)
        key_chat_2 = common.get_session_key("usuario@test.com", 2)

        common.data_store[key_chat_1] = {"type": "file", "data": {"a": 1}, "sources": []}
        common.data_store[key_chat_2] = {"type": "file", "data": {"b": 2}, "sources": []}

        assert common.data_store[key_chat_1]["data"] == {"a": 1}
        assert common.data_store[key_chat_2]["data"] == {"b": 2}
        assert common.data_store[key_chat_1] != common.data_store[key_chat_2]
    finally:
        common.data_store.clear()


def test_promote_active_session_uses_chat_key():
    """promote_active_session debe usar la clave de chat correcta."""
    import src.utils.common as common
    common.data_store.clear()

    try:
        # Simular sesión activa
        active_key = common.get_session_key("usuario@test.com", None)
        chat_key = common.get_session_key("usuario@test.com", 42)

        common.data_store[active_key] = {"type": "file", "data": {"session": "active"}, "sources": []}

        result = common.promote_active_session("usuario@test.com", 42)

        assert result is True
        assert common.data_store[chat_key] == {"type": "file", "data": {"session": "active"}, "sources": []}
        # La clave activa debe seguir existiendo (no se borra)
        assert common.data_store[active_key] is not None
    finally:
        common.data_store.clear()


def test_ensure_user_session_rebuilds_only_sources_attached_to_chat(monkeypatch):
    import src.utils.common as common

    source_a = type("Source", (), {"id": 11, "type": "file", "name": "a.csv"})()
    source_b = type("Source", (), {"id": 12, "type": "file", "name": "b.csv"})()
    chat = type("Chat", (), {"id": 7, "user_id": "usuario@test.com", "data_sources": [source_a, source_b], "data_source": source_a})()

    class Query:
        def __init__(self, model):
            self.model = model

        def filter(self, *_args, **_kwargs):
            return self

        def first(self):
            return chat

        def all(self):
            return [source_a, source_b]

    class FakeDb:
        def query(self, model):
            return Query(model)

    common.data_store.clear()
    chat_key = common.get_session_key("usuario@test.com", 7)
    common.data_store[chat_key] = {
        "type": "file",
        "data": {"a": "frame-a", "b": "frame-b", "private": "other-chat-frame"},
        "sources": [11, 12, 99],
    }
    loaded_ids = []

    def fake_load(_user_id, source, chat_id, persist=False):
        loaded_ids.append(source.id)
        session = common.data_store[common.get_session_key("usuario@test.com", chat_id)]
        session["data"][source.name.split(".")[0]] = f"frame-{source.id}"
        session["sources"].append(source.id)
        return True

    monkeypatch.setattr(common, "get_user_data", lambda *_args, **_kwargs: common.data_store.get(chat_key))
    monkeypatch.setattr(common, "load_source_to_session", fake_load)
    monkeypatch.setattr(common, "save_user_data", lambda *_args, **_kwargs: None)

    rebuilt = common.ensure_user_session("usuario@test.com", FakeDb(), chat_id=7)

    assert loaded_ids == [11, 12]
    assert rebuilt["sources"] == [11, 12]
    assert rebuilt["data"] == {"a": "frame-11", "b": "frame-12"}
    common.data_store.clear()
