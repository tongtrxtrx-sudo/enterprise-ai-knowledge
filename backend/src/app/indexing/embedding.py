from __future__ import annotations

from hashlib import sha256


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate deterministic fallback vectors for provided texts."""
    if not isinstance(texts, list):
        raise TypeError("texts must be list[str]")

    vectors: list[list[float]] = []
    for text in texts:
        if not isinstance(text, str):
            raise TypeError("each text must be str")
        digest = sha256(text.encode("utf-8")).hexdigest()
        first = int(digest[:8], 16) / 0xFFFFFFFF
        second = int(digest[8:16], 16) / 0xFFFFFFFF
        vectors.append([first, second])
    return vectors
