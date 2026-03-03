import asyncio


class CountingProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, payload: dict[str, object]) -> dict[str, object]:
        self.calls += 1
        _ = payload
        return {
            "text": "public answer",
            "citations": [{"upload_id": 1, "chunk_index": 0}],
        }


def test_public_query_exact_match_uses_cache_on_second_call() -> None:
    from app.ai.chat_service import ChatService

    provider = CountingProvider()
    service = ChatService(router=provider)

    first = asyncio.run(
        service.answer(
            query="What are office hours?",
            context_chunks=[
                {
                    "content": "office hours 9-5",
                    "metadata": {"upload_id": 1, "chunk_index": 0},
                }
            ],
            public_query=True,
        )
    )
    second = asyncio.run(
        service.answer(
            query="What are office hours?",
            context_chunks=[
                {
                    "content": "office hours 9-5",
                    "metadata": {"upload_id": 1, "chunk_index": 0},
                }
            ],
            public_query=True,
        )
    )

    assert provider.calls == 1
    assert first["text"] == second["text"]
    assert first["citations"] == second["citations"]
    assert second["cache_hit"] is True


def test_non_public_query_bypasses_public_cache() -> None:
    from app.ai.chat_service import ChatService

    provider = CountingProvider()
    service = ChatService(router=provider)

    asyncio.run(
        service.answer(
            query="What are office hours?",
            context_chunks=[
                {
                    "content": "office hours 9-5",
                    "metadata": {"upload_id": 1, "chunk_index": 0},
                }
            ],
            public_query=False,
        )
    )
    asyncio.run(
        service.answer(
            query="What are office hours?",
            context_chunks=[
                {
                    "content": "office hours 9-5",
                    "metadata": {"upload_id": 1, "chunk_index": 0},
                }
            ],
            public_query=False,
        )
    )

    assert provider.calls == 2
