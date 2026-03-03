from __future__ import annotations


ALLOWED_METADATA_KEYS = {
    "upload_id",
    "chunk_index",
    "filename",
    "folder",
    "score",
    "source",
}

REDACT_KEY_TOKENS = {"user", "owner", "email", "token", "username", "auth"}


def _normalize_text(text: str) -> str:
    return " ".join(text.split())


def _metadata_is_redacted(key: str) -> bool:
    lowered = key.lower()
    return any(token in lowered for token in REDACT_KEY_TOKENS)


def sanitize_context_chunks(
    chunks: list[dict[str, object]], *, snippet_limit: int = 240
) -> list[dict[str, object]]:
    sanitized: list[dict[str, object]] = []
    for item in chunks:
        content = _normalize_text(str(item.get("content", "")))
        snippet = content[:snippet_limit]

        raw_meta = item.get("metadata", {})
        safe_meta: dict[str, object] = {}
        if isinstance(raw_meta, dict):
            for key, value in raw_meta.items():
                if _metadata_is_redacted(str(key)):
                    continue
                if key in ALLOWED_METADATA_KEYS:
                    safe_meta[str(key)] = value

        sanitized.append({"snippet": snippet, "metadata": safe_meta})
    return sanitized
