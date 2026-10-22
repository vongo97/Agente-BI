"""
Tests de límite y TTL de data_store (P-35).

Verifica que:
1. data_store tiene un límite máximo de entradas (evita OOM).
2. Las entradas expiran después del TTL (libera sesiones abandonadas).
3. Cuando se excede el límite, se elimina la entrada más antigua.
"""
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.utils.common import _BoundedStore, data_store


def test_bounded_store_respects_max_entries():
    """Cuando se excede max_entries, se elimina la entrada más antigua."""
    store = _BoundedStore(max_entries=3, ttl_seconds=3600)

    store["a"] = 1
    store["b"] = 2
    store["c"] = 3
    assert len(store) == 3

    # Agregar una cuarta entrada: debe eliminar "a" (la más antigua)
    store["d"] = 4
    assert len(store) == 3
    assert "a" not in store
    assert "b" in store
    assert "c" in store
    assert "d" in store


def test_bounded_store_ttl_expires_entries():
    """Las entradas expiran después de ttl_seconds."""
    store = _BoundedStore(max_entries=10, ttl_seconds=0.1)

    store["a"] = 1
    assert "a" in store
    assert store["a"] == 1

    # Esperar a que expire
    time.sleep(0.15)

    assert "a" not in store
    assert store.get("a") is None


def test_bounded_store_get_expired_returns_none():
    """get() devuelve None para entradas expiradas."""
    store = _BoundedStore(max_entries=10, ttl_seconds=0.1)

    store["a"] = 1
    time.sleep(0.15)

    assert store.get("a") is None
    assert store.get("a", "default") == "default"


def test_bounded_store_clear():
    """clear() elimina todas las entradas."""
    store = _BoundedStore(max_entries=10, ttl_seconds=3600)
    store["a"] = 1
    store["b"] = 2
    assert len(store) == 2

    store.clear()
    assert len(store) == 0


def test_data_store_is_bounded_store_instance():
    """data_store debe ser una instancia de _BoundedStore."""
    from src.utils.common import _BoundedStore as BS
    assert isinstance(data_store, BS)


def test_bounded_store_pop():
    """pop() elimina y devuelve la entrada."""
    store = _BoundedStore(max_entries=10, ttl_seconds=3600)
    store["a"] = 1

    val = store.pop("a")
    assert val == 1
    assert "a" not in store

    # pop con default para clave inexistente
    assert store.pop("inexistente", "default") == "default"


def test_bounded_store_len_after_expiration():
    """len() debe reflejar solo entradas no expiradas."""
    store = _BoundedStore(max_entries=10, ttl_seconds=0.1)
    store["a"] = 1
    store["b"] = 2
    assert len(store) == 2

    time.sleep(0.15)
    # Ambas entradas expiran juntas (mismo TTL)
    assert len(store) == 0
