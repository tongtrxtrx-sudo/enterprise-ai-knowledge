import importlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def chat_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    database_path = tmp_path / "chat-sse.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    monkeypatch.setenv("JWT_SECRET", "chat-sse-secret-for-tests-32-bytes")

    config_module = importlib.import_module("app.config")
    db_module = importlib.import_module("app.db")
    models_module = importlib.import_module("app.models")
    security_module = importlib.import_module("app.security")
    main_module = importlib.import_module("app.main")

    config_module.get_settings.cache_clear()
    db_module.get_engine.cache_clear()
    importlib.reload(db_module)
    importlib.reload(models_module)
    importlib.reload(security_module)
    importlib.reload(main_module)

    app = main_module.create_app()
    session_factory = db_module.get_session_factory()

    with session_factory() as session:
        user = models_module.User(
            username="chat-user", password_hash="x", role="user", department="eng"
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        token = security_module.issue_access_token(
            user_id=user.id, role=user.role, token_version=user.token_version
        )

    with TestClient(app) as client:
        yield client, token


def _read_sse_events(response_text: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for line in response_text.splitlines():
        if not line.startswith("data: "):
            continue
        events.append(json.loads(line.removeprefix("data: ")))
    return events


def test_chat_endpoint_streams_chunk_events_with_citations(chat_client) -> None:
    client, token = chat_client
    headers = {"Authorization": f"Bearer {token}"}

    with client.stream(
        "POST",
        "/chat/stream",
        json={"query": "What is the onboarding policy?", "folder": "public"},
        headers=headers,
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = response.read().decode("utf-8")

    events = _read_sse_events(body)
    chunk_events = [item for item in events if item.get("type") == "chunk"]
    assert len(chunk_events) >= 1
    assert all("citations" in item for item in chunk_events)
    assert all(isinstance(item["citations"], list) for item in chunk_events)


def test_chat_chunk_event_citations_include_upload_and_chunk_index(chat_client) -> None:
    client, token = chat_client
    headers = {"Authorization": f"Bearer {token}"}

    with client.stream(
        "POST",
        "/chat/stream",
        json={"query": "Tell me deployment checklist", "folder": "public"},
        headers=headers,
    ) as response:
        assert response.status_code == 200
        body = response.read().decode("utf-8")

    events = _read_sse_events(body)
    first_chunk = next(item for item in events if item.get("type") == "chunk")
    first_citation = first_chunk["citations"][0]
    assert "upload_id" in first_citation
    assert "chunk_index" in first_citation
