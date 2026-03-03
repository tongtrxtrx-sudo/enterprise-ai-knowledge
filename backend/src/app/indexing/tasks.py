from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy import delete, select

from app.db import get_session_factory
from app.indexing.chunker import chunk_markdown
from app.indexing.embedding import embed_texts
from app.models import DocChunk, IndexTree, UploadRecord
from app.permissions.service import build_upload_read_allow

try:
    from markitdown import MarkItDown
except Exception:  # noqa: BLE001
    MarkItDown = None


def parse_to_markdown(raw_text: str) -> str:
    """Convert raw text to Markdown using MarkItDown when available."""
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")

    stripped = raw_text.strip()
    if not stripped:
        return ""

    if MarkItDown is None:
        return stripped

    try:
        converter = MarkItDown()
        result = converter.convert(stripped)
        if hasattr(result, "text_content"):
            return str(result.text_content).strip()
        if hasattr(result, "markdown"):
            return str(result.markdown).strip()
        return str(result).strip()
    except Exception:  # noqa: BLE001
        return stripped


def _upsert_chunks(session, upload: UploadRecord, markdown: str) -> list[DocChunk]:
    chunks = chunk_markdown(markdown)
    if not chunks:
        chunks = [markdown] if markdown else [""]

    now = datetime.now(UTC)
    read_allow = build_upload_read_allow(session, upload)
    saved_rows: list[DocChunk] = []
    for idx, chunk in enumerate(chunks):
        row = session.scalar(
            select(DocChunk).where(
                DocChunk.upload_id == upload.id,
                DocChunk.chunk_index == idx,
            )
        )
        if row is None:
            row = DocChunk(
                upload_id=upload.id,
                chunk_index=idx,
                content=chunk,
                content_tsv=chunk.lower(),
                vector_ready=False,
                read_allow=read_allow,
                updated_at=now,
            )
            session.add(row)
        else:
            row.content = chunk
            row.content_tsv = chunk.lower()
            row.read_allow = read_allow
            row.updated_at = now
        saved_rows.append(row)

    session.execute(
        delete(DocChunk).where(
            DocChunk.upload_id == upload.id,
            DocChunk.chunk_index >= len(chunks),
        )
    )
    return saved_rows


def _upsert_index_tree(
    session, upload: UploadRecord, markdown: str, chunk_count: int
) -> None:
    now = datetime.now(UTC)
    hash_value = sha256(markdown.encode("utf-8")).hexdigest()
    index_row = session.scalar(
        select(IndexTree).where(IndexTree.upload_id == upload.id)
    )
    if index_row is None:
        session.add(
            IndexTree(
                upload_id=upload.id,
                markdown_sha256=hash_value,
                chunk_count=chunk_count,
                created_at=now,
                updated_at=now,
            )
        )
        return

    index_row.markdown_sha256 = hash_value
    index_row.chunk_count = chunk_count
    index_row.updated_at = now


def run_parse_pipeline(upload_id: int) -> None:
    """Run parse -> chunk -> vector pipeline for one upload record."""
    session_factory = get_session_factory()
    with session_factory() as session:
        upload = session.scalar(
            select(UploadRecord).where(UploadRecord.id == upload_id)
        )
        if upload is None:
            return

        try:
            markdown = parse_to_markdown(upload.source_text)
            upload.markdown_content = markdown

            chunk_rows = _upsert_chunks(session, upload, markdown)
            _upsert_index_tree(session, upload, markdown, len(chunk_rows))

            try:
                vectors = embed_texts([row.content for row in chunk_rows])
                if len(vectors) != len(chunk_rows):
                    raise RuntimeError("embedding length mismatch")

                for row, vector in zip(chunk_rows, vectors, strict=True):
                    row.content_vector = vector
                    row.vector_ready = True

                upload.parse_status = "normal"
                upload.parse_error = None
            except Exception as exc:  # noqa: BLE001
                for row in chunk_rows:
                    row.content_vector = None
                    row.vector_ready = False
                upload.parse_status = "degraded"
                upload.parse_error = str(exc)

            session.commit()
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            upload = session.scalar(
                select(UploadRecord).where(UploadRecord.id == upload_id)
            )
            if upload is not None:
                upload.parse_status = "failed"
                upload.parse_error = str(exc)
                session.commit()
