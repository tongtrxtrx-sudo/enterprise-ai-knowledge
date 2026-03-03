import importlib
from pathlib import Path

import pytest
from sqlalchemy import select


@pytest.fixture
def retrieval_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    database_path = tmp_path / "retrieval-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path.as_posix()}")

    config_module = importlib.import_module("app.config")
    db_module = importlib.import_module("app.db")
    models_module = importlib.import_module("app.models")

    config_module.get_settings.cache_clear()
    db_module.get_engine.cache_clear()
    importlib.reload(db_module)
    importlib.reload(models_module)

    models_module.Base.metadata.create_all(bind=db_module.get_engine())

    return db_module.get_session_factory(), models_module


def _add_chunk(
    models_module,
    *,
    upload_id: int,
    chunk_index: int,
    content: str,
    vector,
    read_allow: str,
    vector_ready: bool = True,
):
    return models_module.DocChunk(
        upload_id=upload_id,
        chunk_index=chunk_index,
        content=content,
        content_tsv=content.lower(),
        content_vector=vector,
        vector_ready=vector_ready,
        read_allow=read_allow,
    )


def test_rrf_retrieval_excludes_unauthorized_content(retrieval_context) -> None:
    session_factory, models_module = retrieval_context
    retrieval_module = importlib.import_module("app.indexing.retrieval")

    with session_factory() as session:
        session.add_all(
            [
                _add_chunk(
                    models_module,
                    upload_id=10,
                    chunk_index=0,
                    content="alpha public vector",
                    vector=[0.1, 1.0],
                    read_allow="|principal:user:1|",
                ),
                _add_chunk(
                    models_module,
                    upload_id=11,
                    chunk_index=0,
                    content="alpha forbidden vector",
                    vector=[0.1, 1.1],
                    read_allow="|principal:user:2|",
                ),
                _add_chunk(
                    models_module,
                    upload_id=12,
                    chunk_index=0,
                    content="alpha admin vector",
                    vector=[0.2, 1.2],
                    read_allow="|role:admin|",
                ),
            ]
        )
        session.commit()

        result = retrieval_module.hybrid_rrf_search(
            session,
            query_text="alpha",
            query_vector=[0.1, 0.0],
            principals=["principal:user:1"],
            limit=5,
        )

        ids = [item["id"] for item in result]
        assert len(ids) == 1
        selected = session.scalar(
            select(models_module.DocChunk).where(models_module.DocChunk.id == ids[0])
        )
        assert selected is not None
        assert selected.read_allow == "|principal:user:1|"


def test_rrf_ranking_is_deterministic_for_repeated_calls(retrieval_context) -> None:
    session_factory, models_module = retrieval_context
    retrieval_module = importlib.import_module("app.indexing.retrieval")

    with session_factory() as session:
        session.add_all(
            [
                _add_chunk(
                    models_module,
                    upload_id=20,
                    chunk_index=0,
                    content="beta first",
                    vector=[0.2, 0.0],
                    read_allow="|principal:user:9|",
                ),
                _add_chunk(
                    models_module,
                    upload_id=20,
                    chunk_index=1,
                    content="beta second",
                    vector=[0.21, 0.0],
                    read_allow="|principal:user:9|",
                ),
                _add_chunk(
                    models_module,
                    upload_id=20,
                    chunk_index=2,
                    content="beta third",
                    vector=[0.8, 0.0],
                    read_allow="|principal:user:9|",
                ),
            ]
        )
        session.commit()

        first = retrieval_module.hybrid_rrf_search(
            session,
            query_text="beta",
            query_vector=[0.2, 0.0],
            principals=["principal:user:9"],
            limit=3,
        )
        second = retrieval_module.hybrid_rrf_search(
            session,
            query_text="beta",
            query_vector=[0.2, 0.0],
            principals=["principal:user:9"],
            limit=3,
        )

        assert [item["id"] for item in first] == [item["id"] for item in second]
        assert [item["rrf_score"] for item in first] == [
            item["rrf_score"] for item in second
        ]
