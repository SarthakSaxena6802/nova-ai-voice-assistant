"""Shared fixtures: an isolated temporary database, no network, no real browser."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

_TMP = Path(tempfile.mkdtemp(prefix="nova-tests-"))
os.environ["NOVA_DATABASE_URL"] = f"sqlite:///{(_TMP / 'test.db').as_posix()}"
os.environ["NOVA_OPEN_BROWSER_ON_SERVER"] = "false"
os.environ["NOVA_WEATHER_ENABLED"] = "false"
os.environ["NOVA_LLM_PROVIDER"] = ""
os.environ["NOVA_LOG_LEVEL"] = "WARNING"

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()


@pytest.fixture(scope="session")
def settings():
    s = get_settings()
    if not s.model_path.exists():
        from app.ml.trainer import train_and_save

        train_and_save(s.dataset_path, s.model_path, s.model_report_path, s.unseen_dataset_path)
    return s


@pytest.fixture(scope="session")
def classifier(settings):
    from app.ml.intent_classifier import IntentClassifier

    clf = IntentClassifier()
    clf.load(settings.model_path)
    assert clf.is_loaded, clf.load_error
    return clf


@pytest.fixture(scope="session")
def client(settings):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db(settings):
    from app.database.session import SessionLocal, create_tables, init_engine

    init_engine(settings.database_url)
    create_tables()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def say(client):
    """Send text through the full pipeline; each test gets its own conversation session."""
    import uuid

    session = uuid.uuid4().hex[:12]

    def _say(text: str, source: str = "text") -> dict:
        resp = client.post("/api/assistant/process", json={"text": text, "source": source, "session_id": session})
        assert resp.status_code == 200, resp.text
        return resp.json()

    return _say
