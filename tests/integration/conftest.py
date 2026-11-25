"""Fixtures that run the REAL FastAPI app with a fake MongoDB and a tiny real model."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.api.deps as deps
import app.api.main as main_module
import app.api.routes.train as train_route


@pytest.fixture(autouse=True)
def never_run_real_training(monkeypatch):
    """Safety net: the real pipeline reads MongoDB, logs to DagsHub, overwrites
    final_models/ and uploads to S3. No test may trigger it by accident.
    Tests that need /train override this with their own stub."""

    def forbidden():
        raise AssertionError("real training must never run inside tests")

    monkeypatch.setattr(train_route, "_train_blocking", forbidden)


class FakeCursor:
    def __init__(self, docs):
        self.docs = list(docs)

    def sort(self, key, direction=1):
        self.docs.sort(key=lambda d: d[key], reverse=direction == -1)
        return self

    def skip(self, n):
        self.docs = self.docs[n:]
        return self

    def limit(self, n):
        self.docs = self.docs[:n]
        return self

    async def to_list(self, length=None):
        return self.docs[:length]


class FakeCollection:
    """The few async pymongo methods the API uses, backed by a list."""

    def __init__(self):
        self.docs: list[dict] = []

    async def insert_many(self, docs):
        self.docs.extend(docs)

    async def count_documents(self, _filter):
        return len(self.docs)

    def find(self, _filter=None, _projection=None):
        return FakeCursor(self.docs)


class FakeMongoClient:
    def __init__(self, *_args, **_kwargs):
        self.collection = FakeCollection()
        self.admin = SimpleNamespace(command=self._ping)
        self.ping_works = True

    async def _ping(self, _command):
        if not self.ping_works:
            raise ConnectionError("mongo down")
        return {"ok": 1}

    def __getitem__(self, _db_name):
        return {"predictions": self.collection}  # db["predictions"] -> collection

    async def close(self):
        pass


@pytest.fixture
def client(monkeypatch, tiny_model_dir):
    """A TestClient with the model loaded from tiny_model_dir and Mongo faked."""
    monkeypatch.setattr(deps, "FINAL_MODEL_DIR", tiny_model_dir)
    monkeypatch.setattr(main_module, "AsyncMongoClient", FakeMongoClient)
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: SimpleNamespace(mongodb_uri="mongodb://fake", mlflow_uri="http://fake"),
    )
    with TestClient(main_module.app) as test_client:
        yield test_client


@pytest.fixture
def no_model_client(monkeypatch, tmp_path):
    """Same as client, but final_models/ is empty (nothing trained yet)."""
    monkeypatch.setattr(deps, "FINAL_MODEL_DIR", tmp_path / "empty")
    monkeypatch.setattr(main_module, "AsyncMongoClient", FakeMongoClient)
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: SimpleNamespace(mongodb_uri="mongodb://fake", mlflow_uri="http://fake"),
    )
    with TestClient(main_module.app) as test_client:
        yield test_client
