import asyncio


class DummyProvider:
    def __init__(self, name: str, responses: list[object]) -> None:
        self.name = name
        self.responses = responses
        self.calls = 0

    async def generate(self, payload: dict[str, object]) -> dict[str, object]:
        _ = payload
        index = self.calls
        self.calls += 1
        item = self.responses[index]
        if isinstance(item, Exception):
            raise item
        return item


def test_router_retries_three_attempts_then_failover_on_retryable_errors() -> None:
    from app.ai.router import ProviderHTTPError, ProviderRouter

    primary = DummyProvider(
        "primary",
        [
            ProviderHTTPError(status_code=429, message="rate limited"),
            ProviderHTTPError(status_code=503, message="upstream down"),
            TimeoutError("timed out"),
        ],
    )
    secondary = DummyProvider("secondary", [{"text": "fallback ok"}])

    router = ProviderRouter(providers=[primary, secondary], timeout_seconds=0.01)
    result = asyncio.run(router.generate(payload={"query": "hello"}))

    assert result["provider"] == "secondary"
    assert result["response"]["text"] == "fallback ok"
    assert primary.calls == 3
    assert secondary.calls == 1


def test_router_does_not_retry_non_retryable_errors() -> None:
    from app.ai.router import ProviderHTTPError, ProviderRouter

    primary = DummyProvider(
        "primary", [ProviderHTTPError(status_code=400, message="bad request")]
    )
    secondary = DummyProvider("secondary", [{"text": "should not be used"}])
    router = ProviderRouter(providers=[primary, secondary], timeout_seconds=0.01)

    try:
        asyncio.run(router.generate(payload={"query": "hello"}))
    except ProviderHTTPError as exc:
        assert exc.status_code == 400
    else:
        raise AssertionError("Expected non-retryable error")

    assert primary.calls == 1
    assert secondary.calls == 0
