def test_sanitizer_truncates_chunk_to_snippet_length() -> None:
    from app.ai.sanitizer import sanitize_context_chunks

    chunks = [
        {
            "content": "A" * 400,
            "metadata": {"upload_id": 10, "chunk_index": 0, "filename": "a.md"},
        }
    ]

    sanitized = sanitize_context_chunks(chunks, snippet_limit=120)
    assert len(sanitized) == 1
    assert len(sanitized[0]["snippet"]) == 120


def test_sanitizer_redacts_user_identifiers_from_metadata() -> None:
    from app.ai.sanitizer import sanitize_context_chunks

    chunks = [
        {
            "content": "Short chunk",
            "metadata": {
                "upload_id": 11,
                "chunk_index": 2,
                "user_id": 123,
                "owner_id": 456,
                "email": "u@example.com",
                "username": "alice",
                "folder": "public",
            },
        }
    ]

    sanitized = sanitize_context_chunks(chunks, snippet_limit=120)
    meta = sanitized[0]["metadata"]

    assert "user_id" not in meta
    assert "owner_id" not in meta
    assert "email" not in meta
    assert "username" not in meta
    assert meta["upload_id"] == 11
    assert meta["chunk_index"] == 2
