from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.ai.router import ProviderRouter
from app.ai.sanitizer import sanitize_context_chunks


class ChatGenerator(Protocol):
    async def generate(self, payload: dict[str, object]) -> dict[str, object]: ...


@dataclass(slots=True)
class CachedPublicAnswer:
    text: str
    citations: list[dict[str, int]]


@dataclass(slots=True)
class ChatService:
    router: ChatGenerator = field(default_factory=ProviderRouter)
    snippet_limit: int = 240
    _public_cache: dict[str, CachedPublicAnswer] = field(default_factory=dict)

    @staticmethod
    def route_skill(query: str) -> str:
        query_lower = query.strip().lower()
        if query_lower.startswith("summarize") or query_lower.startswith("summary"):
            return "summarization"
        return "knowledge_qa"

    @staticmethod
    def _cache_key(query: str) -> str:
        return query.strip()

    async def answer(
        self,
        *,
        query: str,
        context_chunks: list[dict[str, object]],
        public_query: bool,
    ) -> dict[str, object]:
        cache_key = self._cache_key(query)
        if public_query and cache_key in self._public_cache:
            cached = self._public_cache[cache_key]
            return {
                "text": cached.text,
                "citations": cached.citations,
                "cache_hit": True,
                "skill": self.route_skill(query),
            }

        skill = self.route_skill(query)
        sanitized_context = sanitize_context_chunks(
            context_chunks, snippet_limit=self.snippet_limit
        )
        fallback_citations: list[dict[str, int]] = []
        for item in sanitized_context:
            metadata = item.get("metadata", {})
            if not isinstance(metadata, dict):
                continue
            if "upload_id" in metadata and "chunk_index" in metadata:
                fallback_citations.append(
                    {
                        "upload_id": int(metadata["upload_id"]),
                        "chunk_index": int(metadata["chunk_index"]),
                    }
                )

        payload = {"query": query.strip(), "skill": skill, "context": sanitized_context}
        generated = await self.router.generate(payload)
        provider_response = generated.get("response", generated)
        text = str(provider_response.get("text", ""))

        raw_citations = provider_response.get("citations", fallback_citations)
        citations: list[dict[str, int]] = []
        if isinstance(raw_citations, list):
            for item in raw_citations:
                if not isinstance(item, dict):
                    continue
                if "upload_id" not in item or "chunk_index" not in item:
                    continue
                citations.append(
                    {
                        "upload_id": int(item["upload_id"]),
                        "chunk_index": int(item["chunk_index"]),
                    }
                )

        result = {
            "text": text,
            "citations": citations,
            "cache_hit": False,
            "skill": skill,
        }
        if public_query:
            self._public_cache[cache_key] = CachedPublicAnswer(
                text=text,
                citations=citations,
            )
        return result
