from __future__ import annotations

import asyncio
import os
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable, Iterable

import httpx


DEFAULT_PROVIDER_ORDER = (
    "openai",
    "anthropic",
    "gemini",
    "huggingface",
    "kimi",
    "mistral",
    "grok",
)


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    api_key: str | None
    model: str
    base_url: str
    protocol: str

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model and self.base_url)

    def public_dict(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "configured": self.configured,
            "model": self.model,
            "base_url": self.base_url,
            "protocol": self.protocol,
        }


@dataclass
class ProviderResult:
    provider: str
    model: str
    status: str
    text: str = ""
    latency_ms: int = 0
    usage: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def load_provider_configs() -> dict[str, ProviderConfig]:
    configs = {
        "openai": ProviderConfig(
            "openai",
            _env("OPENAI_API_KEY") or None,
            _env("OPENAI_MODEL", "gpt-5.6-terra"),
            _env("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            "openai_responses",
        ),
        "anthropic": ProviderConfig(
            "anthropic",
            _env("ANTHROPIC_API_KEY") or None,
            _env("ANTHROPIC_MODEL", "claude-sonnet-5"),
            _env("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1").rstrip("/"),
            "anthropic_messages",
        ),
        "gemini": ProviderConfig(
            "gemini",
            _env("GEMINI_API_KEY") or None,
            _env("GEMINI_MODEL", "gemini-3.6-flash"),
            _env("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/"),
            "gemini_generate_content",
        ),
        "huggingface": ProviderConfig(
            "huggingface",
            _env("HUGGINGFACE_API_KEY") or None,
            _env("HUGGINGFACE_MODEL", "Qwen/Qwen3-Coder-480B-A35B-Instruct:cheapest"),
            _env("HUGGINGFACE_BASE_URL", "https://router.huggingface.co/v1").rstrip("/"),
            "openai_chat",
        ),
        "kimi": ProviderConfig(
            "kimi",
            _env("KIMI_API_KEY") or None,
            _env("KIMI_MODEL", "kimi-k3"),
            _env("KIMI_BASE_URL", "https://api.moonshot.ai/v1").rstrip("/"),
            "openai_chat",
        ),
        "mistral": ProviderConfig(
            "mistral",
            _env("MISTRAL_API_KEY") or None,
            _env("MISTRAL_MODEL", "mistral-large-latest"),
            _env("MISTRAL_BASE_URL", "https://api.mistral.ai/v1").rstrip("/"),
            "openai_chat",
        ),
        "grok": ProviderConfig(
            "grok",
            _env("XAI_API_KEY") or _env("GROK_API_KEY") or None,
            _env("XAI_MODEL", "grok-4.5"),
            _env("XAI_BASE_URL", "https://api.x.ai/v1").rstrip("/"),
            "openai_chat",
        ),
    }

    for name, prefix in (("llama_colab", "LLAMA_COLAB"), ("qwen_colab", "QWEN_COLAB")):
        configs[name] = ProviderConfig(
            name,
            _env(f"{prefix}_API_KEY") or None,
            _env(f"{prefix}_MODEL"),
            _env(f"{prefix}_BASE_URL").rstrip("/"),
            "openai_chat",
        )
    return configs


def _messages(system_prompt: str, prompt: str) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt.strip()})
    messages.append({"role": "user", "content": prompt})
    return messages


def _extract_openai_chat(data: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    choices = data.get("choices") or []
    if not choices:
        return "", data.get("usage")
    content = (choices[0].get("message") or {}).get("content")
    if isinstance(content, str):
        return content, data.get("usage")
    if isinstance(content, list):
        text = "\n".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
        return text, data.get("usage")
    return "", data.get("usage")


def _extract_openai_response(data: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    chunks: list[str] = []
    for item in data.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for block in item.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "output_text":
                chunks.append(str(block.get("text", "")))
    return "\n".join(chunk for chunk in chunks if chunk), data.get("usage")


def _extract_anthropic(data: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    chunks = [
        str(block.get("text", ""))
        for block in data.get("content") or []
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    return "\n".join(chunk for chunk in chunks if chunk), data.get("usage")


def _extract_gemini(data: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    chunks: list[str] = []
    for candidate in data.get("candidates") or []:
        for part in (candidate.get("content") or {}).get("parts") or []:
            if isinstance(part, dict) and "text" in part:
                chunks.append(str(part["text"]))
    return "\n".join(chunk for chunk in chunks if chunk), data.get("usageMetadata")


async def _post_json(
    client: httpx.AsyncClient,
    url: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = await client.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


async def call_provider(
    config: ProviderConfig,
    *,
    prompt: str,
    system_prompt: str,
    max_output_tokens: int,
    client: httpx.AsyncClient,
) -> ProviderResult:
    started = time.perf_counter()
    if not config.configured:
        return ProviderResult(
            provider=config.name,
            model=config.model,
            status="not_configured",
            error="The provider key, model, or base URL is not configured.",
        )

    try:
        if config.protocol == "openai_responses":
            data = await _post_json(
                client,
                f"{config.base_url}/responses",
                headers={"Authorization": f"Bearer {config.api_key}"},
                payload={
                    "model": config.model,
                    "instructions": system_prompt,
                    "input": prompt,
                    "max_output_tokens": max_output_tokens,
                    "store": False,
                },
            )
            text, usage = _extract_openai_response(data)
        elif config.protocol == "anthropic_messages":
            data = await _post_json(
                client,
                f"{config.base_url}/messages",
                headers={
                    "x-api-key": str(config.api_key),
                    "anthropic-version": "2023-06-01",
                },
                payload={
                    "model": config.model,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_output_tokens,
                },
            )
            text, usage = _extract_anthropic(data)
        elif config.protocol == "gemini_generate_content":
            data = await _post_json(
                client,
                f"{config.base_url}/models/{config.model}:generateContent",
                headers={"x-goog-api-key": str(config.api_key)},
                payload={
                    "systemInstruction": {"parts": [{"text": system_prompt}]},
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": max_output_tokens},
                },
            )
            text, usage = _extract_gemini(data)
        else:
            token_field = "max_completion_tokens" if config.name == "kimi" else "max_tokens"
            data = await _post_json(
                client,
                f"{config.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {config.api_key}"},
                payload={
                    "model": config.model,
                    "messages": _messages(system_prompt, prompt),
                    token_field: max_output_tokens,
                    "stream": False,
                },
            )
            text, usage = _extract_openai_chat(data)

        latency_ms = int((time.perf_counter() - started) * 1000)
        if not text.strip():
            return ProviderResult(
                provider=config.name,
                model=config.model,
                status="error",
                latency_ms=latency_ms,
                usage=usage,
                error="Provider returned no text output.",
            )
        return ProviderResult(
            provider=config.name,
            model=config.model,
            status="ok",
            text=text.strip(),
            latency_ms=latency_ms,
            usage=usage,
        )
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500]
        return ProviderResult(
            provider=config.name,
            model=config.model,
            status="error",
            latency_ms=int((time.perf_counter() - started) * 1000),
            error=f"HTTP {exc.response.status_code}: {body}",
        )
    except Exception as exc:  # noqa: BLE001
        return ProviderResult(
            provider=config.name,
            model=config.model,
            status="error",
            latency_ms=int((time.perf_counter() - started) * 1000),
            error=f"{type(exc).__name__}: {exc}",
        )


async def run_panel(
    *,
    prompt: str,
    system_prompt: str,
    providers: Iterable[str] | None,
    max_output_tokens: int,
    timeout_seconds: float,
    client_factory: Callable[[], httpx.AsyncClient] | None = None,
) -> dict[str, Any]:
    configs = load_provider_configs()
    selected = list(providers or DEFAULT_PROVIDER_ORDER)
    unknown = [name for name in selected if name not in configs]
    if unknown:
        raise ValueError(f"Unknown providers: {', '.join(unknown)}")

    max_concurrency = max(1, int(_env("PANEL_MAX_CONCURRENCY", "7")))
    semaphore = asyncio.Semaphore(max_concurrency)
    factory = client_factory or (
        lambda: httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds, connect=min(10.0, timeout_seconds)),
            limits=httpx.Limits(max_connections=max_concurrency, max_keepalive_connections=max_concurrency),
        )
    )

    async with factory() as client:
        async def guarded(name: str) -> ProviderResult:
            async with semaphore:
                return await call_provider(
                    configs[name],
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_output_tokens=max_output_tokens,
                    client=client,
                )

        results = await asyncio.gather(*(guarded(name) for name in selected))

    return {
        "requested_providers": selected,
        "successful_providers": [result.provider for result in results if result.status == "ok"],
        "failed_providers": [result.provider for result in results if result.status != "ok"],
        "results": [result.to_dict() for result in results],
    }
