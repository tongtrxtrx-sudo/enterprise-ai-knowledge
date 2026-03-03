import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select


@pytest.fixture
def pipeline_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    database_path = tmp_path / "pipeline-test.db"
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


def test_pipeline_persists_markdown_chunks_tsv_and_vectors(
    pipeline_context, monkeypatch
) -> None:
    client, session_factory, models_module = pipeline_context
    tasks_module = importlib.import_module("app.indexing.tasks")

    monkeypatch.setattr(
        tasks_module, "parse_to_markdown", lambda raw: f"# Title\n\n{raw}"
    )
    monkeypatch.setattr(
        tasks_module,
        "embed_texts",
        lambda texts: [
            [float(idx + 1), float(len(text))] for idx, text in enumerate(texts)
        ],
    )

    response = _upload(
        client,
        folder="folder-a",
        filename="doc.md",
        content=b"hello chunk world",
    )

    assert response.status_code == 201
    payload = response.json()

    with session_factory() as session:
        upload = session.scalar(
            select(models_module.UploadRecord).where(
                models_module.UploadRecord.id == payload["upload_id"]
            )
        )
        assert upload is not None
        assert upload.parse_status == "normal"
        assert upload.markdown_content.startswith("# Title")

        chunks = session.scalars(
            select(models_module.DocChunk).where(
                models_module.DocChunk.upload_id == upload.id
            )
        ).all()
        assert len(chunks) >= 1
        assert all(chunk.content_tsv for chunk in chunks)
        assert all(chunk.vector_ready for chunk in chunks)
        assert all(chunk.content_vector is not None for chunk in chunks)

        tree = session.scalar(
            select(models_module.IndexTree).where(
                models_module.IndexTree.upload_id == upload.id
            )
        )
        assert tree is not None
        assert tree.chunk_count == len(chunks)


def test_vector_failure_keeps_deterministic_rows_and_allows_retry(
    pipeline_context, monkeypatch
) -> None:
    client, session_factory, models_module = pipeline_context
    tasks_module = importlib.import_module("app.indexing.tasks")

    monkeypatch.setattr(tasks_module, "parse_to_markdown", lambda raw: raw)

    def raise_vector_error(_: list[str]) -> list[list[float]]:
        raise RuntimeError("provider down")

    monkeypatch.setattr(tasks_module, "embed_texts", raise_vector_error)

    response = _upload(
        client,
        folder="folder-b",
        filename="retry.txt",
        content=b"retry me once",
    )
    assert response.status_code == 201
    upload_id = response.json()["upload_id"]

    with session_factory() as session:
        upload = session.scalar(
            select(models_module.UploadRecord).where(
                models_module.UploadRecord.id == upload_id
            )
        )
        assert upload is not None
        assert upload.parse_status == "degraded"

        initial_count = session.scalar(
            select(func.count())
            .select_from(models_module.DocChunk)
            .where(models_module.DocChunk.upload_id == upload_id)
        )
        assert initial_count and initial_count > 0

        initial_not_ready = session.scalar(
            select(func.count())
            .select_from(models_module.DocChunk)
            .where(
                models_module.DocChunk.upload_id == upload_id,
                models_module.DocChunk.vector_ready.is_(False),
            )
        )
        assert initial_not_ready == initial_count

    monkeypatch.setattr(
        tasks_module,
        "embed_texts",
        lambda texts: [[0.5, float(len(text))] for text in texts],
    )

    tasks_module.run_parse_pipeline(upload_id=upload_id)

    with session_factory() as session:
        upload = session.scalar(
            select(models_module.UploadRecord).where(
                models_module.UploadRecord.id == upload_id
            )
        )
        assert upload is not None
        assert upload.parse_status == "normal"

        final_count = session.scalar(
            select(func.count())
            .select_from(models_module.DocChunk)
            .where(models_module.DocChunk.upload_id == upload_id)
        )
        assert final_count == initial_count

        ready_count = session.scalar(
            select(func.count())
            .select_from(models_module.DocChunk)
            .where(
                models_module.DocChunk.upload_id == upload_id,
                models_module.DocChunk.vector_ready.is_(True),
            )
        )
        assert ready_count == final_count
