"""Verify Supabase JWT access tokens."""

from __future__ import annotations

import jwt
from fastapi import HTTPException, status

from app.config import settings


class AuthError(Exception):
    pass


def verify_supabase_access_token(token: str) -> dict:
    if not settings.supabase_jwt_secret:
        raise AuthError("Leaderboard auth is not configured.")

    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise AuthError("Invalid or expired sign-in token.") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise AuthError("Token is missing a user id.")

    return payload


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
