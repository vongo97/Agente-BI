from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from src.database import Base, Chat, DataSource, get_db
from src.routers import dashboard as dashboard_router
from src.utils.limiter import limiter


def test_chat_can_own_multiple_sources_without_crossing_user_boundaries():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        owner_a_1 = DataSource(user_id="a@test.com", name="north.csv", type="file", url="a/north")
        owner_a_2 = DataSource(user_id="a@test.com", name="south.csv", type="file", url="a/south")
        owner_b = DataSource(user_id="b@test.com", name="private.csv", type="file", url="b/private")
        db.add_all([owner_a_1, owner_a_2, owner_b])
        db.flush()

        chat_a = Chat(
            user_id="a@test.com",
            title="Comparativo regional",
            data_source_id=owner_a_1.id,
            data_sources=[owner_a_1, owner_a_2],
        )
        chat_b = Chat(
            user_id="b@test.com",
            title="Privado",
            data_source_id=owner_b.id,
            data_sources=[owner_b],
        )
        db.add_all([chat_a, chat_b])
        db.commit()
        chat_a_id = chat_a.id
        chat_b_id = chat_b.id

    with session_factory() as db:
        reloaded_a = db.query(Chat).filter(Chat.id == chat_a_id).one()
        reloaded_b = db.query(Chat).filter(Chat.id == chat_b_id).one()
        assert [source.name for source in reloaded_a.data_sources] == ["north.csv", "south.csv"]
        assert [source.name for source in reloaded_b.data_sources] == ["private.csv"]
        assert inspect(engine).has_table("chat_data_sources")

    engine.dispose()


def test_chat_source_update_checks_ownership_and_rebuilds_chat_pool(monkeypatch):
    source = DataSource(id=21, user_id="owner@test.com", name="sales.csv", type="file", url="key/sales")
    chat = Chat(id=31, user_id="owner@test.com", title="Sales", data_source_id=21, data_sources=[])

    class Query:
        def __init__(self, model):
            self.model = model

        def filter(self, *_args, **_kwargs):
            return self

        def first(self):
            return chat if self.model is Chat else None

        def all(self):
            return [source]

    class FakeDb:
        def __init__(self):
            self.committed = False

        def query(self, model):
            return Query(model)

        def commit(self):
            self.committed = True

    db = FakeDb()
    app = FastAPI()
    app.state.limiter = limiter
    app.dependency_overrides[get_db] = lambda: db
    app.include_router(dashboard_router.router)
    monkeypatch.setattr(dashboard_router, "get_authenticated_user", lambda: "owner@test.com")
    monkeypatch.setattr(dashboard_router, "check_authorization", lambda *_args: True)
    rebuild = []
    monkeypatch.setattr(
        dashboard_router,
        "ensure_user_session",
        lambda user_id, _db, chat_id: rebuild.append((user_id, chat_id)) or {"sources": [21]},
    )

    client = TestClient(app)
    response = client.put("/history/31/sources", json={"source_ids": [21]})
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data_sources"]] == [21]
    assert chat.data_source_id == 21
    assert [item.id for item in chat.data_sources] == [21]
    assert db.committed
    assert rebuild == [("owner@test.com", 31)]

    db.committed = False
    chat.data_sources = []
    forbidden = client.put("/history/31/sources", json={"source_ids": [21, 99]})
    assert forbidden.status_code == 404
    assert not db.committed
    assert chat.data_sources == []
