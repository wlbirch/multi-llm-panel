from __future__ import annotations

import httpx
import pytest

from server.providers import ProviderConfig, call_provider


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("protocol", "response_json", "expected"),
    [
        (
            "openai_responses",
            {"output": [{"type": "message", "content": [{"type": "output_text", "text": "OpenAI answer"}]}]},
            "OpenAI answer",
        ),
        ("anthropic_messages", {"content": [{"type": "text", "text": "Claude answer"}]}, "Claude answer"),
        (
            "gemini_generate_content",
            {"candidates": [{"content": {"parts": [{"text": "Gemini answer"}]}}]},
            "Gemini answer",
        ),
        ("openai_chat", {"choices": [{"message": {"content": "Compatible answer"}}]}, "Compatible answer"),
    ],
)
async def test_provider_protocols(protocol: str, response_json: dict, expected: str) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert (
            request.headers.get("authorization")
            or request.headers.get("x-api-key")
            or request.headers.get("x-goog-api-key")
        )
        return httpx.Response(200, json=response_json)

    config = ProviderConfig("test", "secret", "model", "https://provider.test/v1", protocol)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await call_provider(
            config,
            prompt="Question",
            system_prompt="Instructions",
            max_output_tokens=100,
            client=client,
        )

    assert result.status == "ok"
    assert result.text == expected


@pytest.mark.asyncio
async def test_unconfigured_provider_is_skipped() -> None:
    config = ProviderConfig("missing", None, "model", "https://provider.test/v1", "openai_chat")
    async with httpx.AsyncClient() as client:
        result = await call_provider(
            config,
            prompt="Question",
            system_prompt="Instructions",
            max_output_tokens=100,
            client=client,
        )
    assert result.status == "not_configured"
