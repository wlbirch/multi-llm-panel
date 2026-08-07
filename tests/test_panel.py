from __future__ import annotations

import httpx
import pytest

from server.providers import run_panel


@pytest.mark.asyncio
async def test_panel_isolates_provider_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret")

    async def handler(request: httpx.Request) -> httpx.Response:
        if "anthropic" in request.url.host:
            return httpx.Response(429, text="rate limited")
        return httpx.Response(
            200,
            json={"output": [{"type": "message", "content": [{"type": "output_text", "text": "ok"}]}]},
        )

    transport = httpx.MockTransport(handler)
    result = await run_panel(
        prompt="Question",
        system_prompt="Instructions",
        providers=["openai", "anthropic"],
        max_output_tokens=100,
        timeout_seconds=10,
        client_factory=lambda: httpx.AsyncClient(transport=transport),
    )

    assert result["successful_providers"] == ["openai"]
    assert result["failed_providers"] == ["anthropic"]
    assert len(result["results"]) == 2

