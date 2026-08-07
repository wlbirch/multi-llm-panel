from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl
from starlette.requests import Request
from starlette.responses import JSONResponse

from server.providers import DEFAULT_PROVIDER_ORDER, load_provider_configs, run_panel
from server.token_verifiers import JWTVerifier

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

PORT = int(os.getenv("PORT", "8788"))
AUTH_MODE = os.getenv("AUTH_MODE", "dev").lower()
RESOURCE_SERVER_URL = os.getenv("RESOURCE_SERVER_URL", f"http://localhost:{PORT}").rstrip("/")
REQUIRED_SCOPES = [
    scope.strip()
    for scope in os.getenv("REQUIRED_SCOPES", "openid").split(",")
    if scope.strip()
]


def build_mcp() -> FastMCP:
    kwargs: dict[str, Any] = {
        "name": "CrossLLM MCP",
        "instructions": (
            "Query independent LLM providers in parallel. Use list_panel_providers before the first panel call, "
            "then use run_llm_panel and synthesize the returned answers. Provider failures are isolated."
        ),
    }
    if AUTH_MODE == "oauth":
        issuer_base = os.getenv("AUTH0_ISSUER", "").rstrip("/")
        if not issuer_base:
            raise RuntimeError("AUTH0_ISSUER is required when AUTH_MODE=oauth")
        issuer = f"{issuer_base}/"
        kwargs.update(
            token_verifier=JWTVerifier(f"{issuer_base}/.well-known/jwks.json", issuer=issuer),
            auth=AuthSettings(
                issuer_url=AnyHttpUrl(issuer_base),
                resource_server_url=AnyHttpUrl(RESOURCE_SERVER_URL),
                required_scopes=REQUIRED_SCOPES,
            ),
        )
    elif AUTH_MODE != "dev":
        raise RuntimeError("AUTH_MODE must be 'dev' or 'oauth'")
    return FastMCP(**kwargs)


mcp = build_mcp()


@mcp.tool()
async def list_panel_providers() -> dict[str, Any]:
    """List panel providers, models, endpoints, and whether their secret configuration is present."""
    configs = load_provider_configs()
    return {
        "default_provider_order": list(DEFAULT_PROVIDER_ORDER),
        "providers": [configs[name].public_dict() for name in configs],
    }


@mcp.tool()
async def run_llm_panel(
    prompt: str,
    system_prompt: str = (
        "Answer independently. Be accurate, explicit about uncertainty, and do not claim consensus with other models."
    ),
    providers: list[str] | None = None,
    max_output_tokens: int | None = None,
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    """Run one task across selected LLM providers concurrently and return each independent answer.

    Use all seven default providers when providers is omitted. The calling ChatGPT agent must
    compare the answers; this tool deliberately does not use an eighth model for synthesis.
    """
    if not prompt or not prompt.strip():
        raise ValueError("prompt must not be empty")
    applied_tokens = max_output_tokens or int(os.getenv("PANEL_MAX_OUTPUT_TOKENS", "1200"))
    applied_timeout = timeout_seconds or float(os.getenv("PANEL_TIMEOUT_SECONDS", "90"))
    applied_tokens = max(64, min(applied_tokens, 16_000))
    applied_timeout = max(5.0, min(applied_timeout, 300.0))
    return await run_panel(
        prompt=prompt.strip(),
        system_prompt=system_prompt.strip(),
        providers=providers,
        max_output_tokens=applied_tokens,
        timeout_seconds=applied_timeout,
    )


async def health(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


app = mcp.streamable_http_app()
app.add_route("/health", health, methods=["GET"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
