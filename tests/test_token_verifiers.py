from __future__ import annotations

import pytest

from server import token_verifiers
from server.token_verifiers import JWTVerifier


class _SigningKey:
    key = object()


@pytest.mark.asyncio
async def test_verifier_accepts_allowlisted_oauth_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_AUDIENCES", "https://crossllm-mcp.onrender.com/mcp")
    monkeypatch.setenv("JWT_CLIENT_IDS", "tpc_allowed")
    verifier = JWTVerifier("https://issuer.example/.well-known/jwks.json", issuer="https://issuer.example/")
    monkeypatch.setattr(verifier._jwk_client, "get_signing_key_from_jwt", lambda _: _SigningKey())
    monkeypatch.setattr(
        token_verifiers.jwt,
        "decode",
        lambda *args, **kwargs: {
            "sub": "user_1",
            "azp": "tpc_allowed",
            "aud": "https://crossllm-mcp.onrender.com/mcp",
            "scope": "openid email profile",
            "exp": 2_000_000_000,
            "iat": 1_900_000_000,
        },
    )

    access_token = await verifier.verify_token("header.payload.signature")

    assert access_token is not None
    assert access_token.client_id == "tpc_allowed"
    assert access_token.scopes == ["openid", "email", "profile"]


@pytest.mark.asyncio
async def test_verifier_rejects_other_oauth_clients(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_AUDIENCES", "https://crossllm-mcp.onrender.com/mcp")
    monkeypatch.setenv("JWT_CLIENT_IDS", "tpc_allowed")
    verifier = JWTVerifier("https://issuer.example/.well-known/jwks.json", issuer="https://issuer.example/")
    monkeypatch.setattr(verifier._jwk_client, "get_signing_key_from_jwt", lambda _: _SigningKey())
    monkeypatch.setattr(
        token_verifiers.jwt,
        "decode",
        lambda *args, **kwargs: {
            "sub": "user_1",
            "azp": "tpc_other",
            "aud": "https://crossllm-mcp.onrender.com/mcp",
            "scope": "openid email profile",
            "exp": 2_000_000_000,
            "iat": 1_900_000_000,
        },
    )

    assert await verifier.verify_token("header.payload.signature") is None
