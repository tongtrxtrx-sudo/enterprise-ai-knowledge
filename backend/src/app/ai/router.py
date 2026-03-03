from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol


class ProviderHTTPError(Exception):
    def __init__(self, *, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


class Provider(Protocol):
    name: str

    async def generate(self, payload: dict[str, object]) -> dict[str, object]: ...


@dataclass(slots=True)
class LocalDeterministicProvider:
    name: str = "local-deterministic"

    async def generate(self, payload: dict[str, object]) -> dict[str, object]:
        query = str(payload.get("query", "")).strip()
        context = payload.get("context", [])
        snippets = []
        citations: list[dict[str, int]] = []
        if isinstance(context, list):
            for item in context:
                if not isinstance(item, dict):
                    continue
                snippet = str(item.get("snippet", "")).strip()
                if snippet:
                    snippets.append(snippet)
                metadata = item.get("metadata", {})
                if isinstance(metadata, dict):
                    upload_id = int(metadata.get("upload_id", 0))
                    chunk_index = int(metadata.get("chunk_index", 0))
                    citations.append(
                        {"upload_id": upload_id, "chunk_index": chunk_index}
                    )

        lead = snippets[0] if snippets else "No indexed context available"
        answer = f"Answer: {query}. Context: {lead}"
        return {"text": answer, "citations": citations}


class ProviderRouter:
    def __init__(
        self,
        *,
        providers: list[Provider] | None = None,
        timeout_seconds: float = 3.0,
        max_attempts: int = 3,
    ) -> None:
        self.providers = providers or [LocalDeterministicProvider()]
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
            return True
        if isinstance(exc, ProviderHTTPError):
            return exc.status_code == 429 or 500 <= exc.status_code <= 599
        return False

    async def generate(self, payload: dict[str, object]) -> dict[str, object]:
        if not self.providers:
            raise RuntimeError("No providers configured")

        last_retryable: Exception | None = None
        for provider in self.providers:
            for attempt in range(self.max_attempts):
                try:
                    response = await asyncio.wait_for(
                        provider.generate(payload), timeout=self.timeout_seconds
                    )
                    return {"provider": provider.name, "response": response}
                except Exception as exc:  # noqa: BLE001
                    if self._is_retryable(exc):
                        last_retryable = exc
                        if attempt < self.max_attempts - 1:
                            continue
                        break
                    raise

        if last_retryable is not None:
            raise last_retryable
        raise RuntimeError("All providers failed")
