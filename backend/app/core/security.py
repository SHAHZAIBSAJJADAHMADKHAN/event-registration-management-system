"""Supabase JWT verification using the configured issuer and JWKS endpoint."""

from functools import lru_cache
from collections.abc import Mapping
from typing import Annotated

import jwt
from fastapi import Depends
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError

from app.core.config import Settings, get_settings


class JWTVerificationError(Exception):
    """A token could not be verified safely."""


class JWTVerifier:
    """Verifies asymmetric Supabase access tokens against the project's JWKS."""

    def __init__(self, issuer: str, jwks_url: str) -> None:
        self._issuer = issuer
        self._jwks_client = PyJWKClient(jwks_url, cache_keys=True)

    def verify(self, token: str) -> Mapping[str, object]:
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=[signing_key.algorithm_name],
                issuer=self._issuer,
                leeway=30,
                options={"require": ["exp", "sub"], "verify_aud": False},
            )
        except (PyJWTError, ValueError, TypeError) as error:
            raise JWTVerificationError("JWT verification failed.") from error


@lru_cache
def _build_jwt_verifier(issuer: str, jwks_url: str) -> JWTVerifier:
    return JWTVerifier(issuer, jwks_url)


def get_jwt_verifier(
    settings: Annotated[Settings, Depends(get_settings)],
) -> JWTVerifier:
    """Provide a cached verifier without exposing keys or accepting client JWKS URLs."""
    if not settings.supabase_jwt_issuer or not settings.supabase_jwks_url:
        raise RuntimeError("JWT verification configuration is unavailable.")
    return _build_jwt_verifier(settings.supabase_jwt_issuer, settings.supabase_jwks_url)


def require_claim_subject(claims: Mapping[str, object]) -> str:
    """Extract a non-empty subject from already-verified JWT claims."""
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise ValueError("Verified token is missing a subject claim.")
    return subject
