import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select


@pytest.fixture
def upload_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    database_path = tmp_path / "upload-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path.as_posix()}")

    config_module = importlib.import_module("app.config")
    db_module = importlib.import_module("app.db")
    models_module = importlib.import_module("app.models")
    main_module = importlib.import_module("app.main")

    config_module.get_settings.cache_clear()
    db_module.get_engine.cache_clear()
    importlib.reload(db_module)
    importlib.reload(models_module)
    importlib.reload(main_module)

    app = main_module.create_app()
    session_factory = db_module.get_session_factory()

    with TestClient(app) as client:
        yield client, session_factory, models_module


def _upload(
    client: TestClient,
    *,
    folder: str,
    filename: str,
    content: bytes,
    content_type: str = "text/plain",
):
    return client.post(
        "/uploads",
        data={"folder": folder, "filename": filename},
        files={"file": (filename, content, content_type)},
    )


def test_rejects_file_larger_than_10mb(upload_context) -> None:
    client, session_factory, models_module = upload_context
    response = _upload(
        client,
        folder="folder-a",
        filename="notes.txt",
        content=b"a" * (10 * 1024 * 1024 + 1),
    )

    assert response.status_code == 413
    assert response.json() == {
        "code": "file_too_large",
        "detail": "File size exceeds 10MB",
    }

    with session_factory() as session:
        count = session.scalar(
            select(func.count()).select_from(models_module.UploadRecord)
        )
        assert count == 0


def test_rejects_unsafe_filename(upload_context) -> None:
    client, _, _ = upload_context
    response = _upload(
        client,
        folder="folder-a",
        filename="../evil.txt",
        content=b"safe text",
    )

    assert response.status_code == 400
    assert response.json() == {
        "code": "unsafe_filename",
        "detail": "Filename contains unsafe characters",
    }


def test_rejects_executable_signature(upload_context) -> None:
    client, _, _ = upload_context
    response = _upload(
        client,
        folder="folder-a",
        filename="payload.bin",
        content=b"MZ\x90\x00\x03\x00",
        content_type="application/octet-stream",
    )

    assert response.status_code == 400
    assert response.json() == {
        "code": "executable_signature",
        "detail": "Executable files are not allowed",
    }


def test_duplicate_checksum_in_same_folder_returns_409(upload_context) -> None:
    client, _, _ = upload_context
    first = _upload(
        client,
        folder="folder-a",
        filename="report.txt",
        content=b"same-content",
    )
    assert first.status_code == 201

    duplicate = _upload(
        client,
        folder="folder-a",
        filename="other-name.txt",
        content=b"same-content",
    )
    assert duplicate.status_code == 409
    assert duplicate.json() == {
        "code": "duplicate_checksum",
        "detail": "Identical file already exists in this folder",
    }


def test_same_name_new_hash_creates_new_version(upload_context) -> None:
    client, _, _ = upload_context
    first = _upload(
        client,
        folder="folder-a",
        filename="report.txt",
        content=b"v1",
    )
    assert first.status_code == 201
    assert first.json()["version"] == 1

    second = _upload(
        client,
        folder="folder-a",
        filename="report.txt",
        content=b"v2-different",
    )
    assert second.status_code == 201
    payload = second.json()
    assert payload["version"] == 2
    assert payload["code"] == "uploaded"


def test_success_persists_minio_layout_and_parse_status(upload_context) -> None:
    client, session_factory, models_module = upload_context
    response = _upload(
        client,
        folder="folder-z",
        filename="analysis.txt",
        content=b"content-for-minio",
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["code"] == "uploaded"
    assert payload["object_key"].startswith("folder-z/")
    assert "/v1/analysis.txt" in payload["object_key"]

    with session_factory() as session:
        record = session.scalar(
            select(models_module.UploadRecord).where(
                models_module.UploadRecord.checksum_sha256 == payload["checksum_sha256"]
            )
        )
        assert record is not None
        assert record.parse_status in {"normal", "degraded"}


def test_success_triggers_parse_task_asynchronously(
    upload_context, monkeypatch
) -> None:
    client, _, _ = upload_context
    calls: list[tuple[int, str]] = []

    upload_router = importlib.import_module("app.routers.upload")

    def fake_schedule(upload_id: int, object_key: str) -> None:
        calls.append((upload_id, object_key))

    monkeypatch.setattr(upload_router, "schedule_parse_task", fake_schedule)

    response = _upload(
        client,
        folder="folder-parse",
        filename="doc.txt",
        content=b"parse-me",
    )
    assert response.status_code == 201
    payload = response.json()
    assert calls == [(payload["upload_id"], payload["object_key"])]
