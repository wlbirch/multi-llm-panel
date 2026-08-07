from __future__ import annotations

import logging
import os
from typing import Any

import jwt
from jwt import PyJWKClient
from mcp.server.auth.provider import AccessToken, TokenVerifier

logger = logging.getLogger(__name__)


class JWTVerifier(TokenVerifier):
    """Verify Auth0 RS256 access tokens against issuer and audience."""

    def __init__(self, jwks_uri: str, *, issuer: str):
        if not jwks_uri or not issuer:
            raise ValueError("jwks_uri and issuer are required")
        audiences = os.getenv("JWT_AUDIENCES", "")
        self._audiences = tuple(value.strip() for value in audiences.split(",") if value.strip())
        if not self._audiences:
            raise ValueError("JWT_AUDIENCES must contain at least one audience")
        client_ids = os.getenv("JWT_CLIENT_IDS", "")
        self._client_ids = tuple(value.strip() for value in client_ids.split(",") if value.strip())
        if not self._client_ids:
            raise ValueError("JWT_CLIENT_IDS must contain at least one allowed OAuth client")
        self._issuer = issuer
        self._jwk_client = PyJWKClient(jwks_uri)

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token or token.count(".") != 2:
            return None
        try:
            signing_key = self._jwk_client.get_signing_key_from_jwt(token).key
            claims: dict[str, Any] = jwt.decode(
                token,
                key=signing_key,
                algorithms=["RS256"],
                audience=list(self._audiences),
                issuer=self._issuer,
                options={"require": ["exp", "iat"]},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Rejected OAuth access token: %s", exc)
            return None

        scope_value = claims.get("scope") or claims.get("scp") or ""
        scopes = scope_value.split() if isinstance(scope_value, str) else list(scope_value)
        client_id = str(claims.get("azp") or claims.get("client_id") or "")
        if client_id not in self._client_ids:
            logger.warning("Rejected OAuth access token from unauthorized client: %s", client_id or "missing")
            return None
        logger.info("Accepted OAuth access token client_id=%s scopes=%s", client_id, sorted(str(scope) for scope in scopes))
        audience = claims.get("aud")
        resource = audience[0] if isinstance(audience, list) and audience else audience
        return AccessToken(
            token=token,
            client_id=client_id,
            subject=str(claims.get("sub") or "unknown_subject"),
            scopes=[str(scope) for scope in scopes],
            expires_at=claims.get("exp"),
            resource=resource,
            claims=claims,
        )
