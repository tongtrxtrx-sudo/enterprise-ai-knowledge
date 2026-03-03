from __future__ import annotations


def chunk_markdown(
    markdown: str, *, chunk_size: int = 400, overlap: int = 40
) -> list[str]:
    """Split Markdown into deterministic overlapping chunks."""
    if not isinstance(markdown, str):
        raise TypeError("markdown must be str")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be in range [0, chunk_size)")

    normalized = "\n".join(line.rstrip() for line in markdown.splitlines()).strip()
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0
    step = chunk_size - overlap
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks
