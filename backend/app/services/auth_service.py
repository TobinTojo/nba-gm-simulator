"""Verify Supabase JWT access tokens."""

from __future__ import annotations

from functools import lru_cache

import jwt
from fastapi import HTTPException, status
from jwt import PyJWKClient

from app.config import settings


class AuthError(Exception):
    pass


def _supabase_auth_issuer() -> str | None:
    base = settings.supabase_url.strip().rstrip("/")
    if not base:
        return None
    return f"{base}/auth/v1"


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient | None:
    issuer = _supabase_auth_issuer()
    if not issuer:
        return None
    return PyJWKClient(f"{issuer}/.well-known/jwks.json")


def _decode_with_jwks(token: str) -> dict:
    client = _jwks_client()
    if client is None:
        raise AuthError("Leaderboard auth is not configured.")

    issuer = _supabase_auth_issuer()
    signing_key = client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256", "ES256"],
        audience="authenticated",
        issuer=issuer,
    )


def _decode_with_legacy_secret(token: str) -> dict:
    if not settings.supabase_jwt_secret:
        raise AuthError("Leaderboard auth is not configured.")

    return jwt.decode(
        token,
        settings.supabase_jwt_secret,
        algorithms=["HS256"],
        audience="authenticated",
    )


def verify_supabase_access_token(token: str) -> dict:
    errors: list[str] = []

    if _jwks_client() is not None:
        try:
            payload = _decode_with_jwks(token)
        except jwt.PyJWTError as exc:
            errors.append(f"asymmetric: {exc}")
        else:
            user_id = payload.get("sub")
            if not user_id:
                raise AuthError("Token is missing a user id.")
            return payload

    if settings.supabase_jwt_secret:
        try:
            payload = _decode_with_legacy_secret(token)
        except jwt.PyJWTError as exc:
            errors.append(f"legacy: {exc}")
        else:
            user_id = payload.get("sub")
            if not user_id:
                raise AuthError("Token is missing a user id.")
            return payload

    if errors:
        raise AuthError("Invalid or expired sign-in token.") from None

    raise AuthError("Leaderboard auth is not configured.")


def display_name_from_claims(claims: dict) -> str:
    metadata = claims.get("user_metadata") or {}
    for key in ("full_name", "name", "user_name", "preferred_username"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    email = claims.get("email")
    if isinstance(email, str) and "@" in email:
        return email.split("@", 1)[0]

    return "Player"


def require_auth_user(authorization: str | None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in required.",
        )

    token = authorization.removeprefix("Bearer ").strip()
    try:
        return verify_supabase_access_token(token)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
