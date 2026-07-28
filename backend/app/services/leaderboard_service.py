"""Persistent online leaderboard (one high score per user)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from uuid import UUID

import httpx
import psycopg2
from psycopg2.extras import RealDictCursor

from app.config import settings

logger = logging.getLogger(__name__)


class LeaderboardUnavailable(Exception):
    pass


def _rest_configured() -> bool:
    return bool(settings.supabase_url.strip() and settings.supabase_service_role_key.strip())


def leaderboard_enabled() -> bool:
    return bool(settings.leaderboard_database_url.strip()) or _rest_configured()


def _normalize_database_url(url: str) -> str:
    cleaned = url.strip()
    if not cleaned:
        return cleaned

    parsed = urlparse(cleaned)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if "sslmode" not in query:
        query["sslmode"] = "require"
    return urlunparse(parsed._replace(query=urlencode(query)))


def _connection():
    if not settings.leaderboard_database_url.strip():
        raise LeaderboardUnavailable("Leaderboard database is not configured.")

    conn = psycopg2.connect(
        _normalize_database_url(settings.leaderboard_database_url),
        connect_timeout=10,
    )
    conn.prepare_threshold = None
    return conn


def _rest_headers() -> dict[str, str]:
    key = settings.supabase_service_role_key.strip()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _rank_for_user(rows: list[dict[str, Any]], user_id: str) -> int | None:
    sorted_rows = sorted(
        rows,
        key=lambda row: (-int(row["high_score"]), str(row.get("updated_at") or "")),
    )
    for index, row in enumerate(sorted_rows, start=1):
        if str(row["user_id"]) == user_id:
            return index
    return None


def _submit_via_rest(user_id: str, display_name: str, score: int) -> dict[str, Any]:
    base = settings.supabase_url.strip().rstrip("/")
    headers = _rest_headers()

    with httpx.Client(timeout=15.0) as client:
        existing_resp = client.get(
            f"{base}/rest/v1/leaderboard",
            params={"user_id": f"eq.{user_id}", "select": "high_score,updated_at"},
            headers=headers,
        )
        existing_resp.raise_for_status()
        existing_rows = existing_resp.json()
        previous_high = int(existing_rows[0]["high_score"]) if existing_rows else 0
        new_high = max(previous_high, score)
        is_new_best = score > previous_high

        if existing_rows and not is_new_best:
            updated_at = existing_rows[0]["updated_at"]
        else:
            updated_at = datetime.now(timezone.utc).isoformat()

        upsert_resp = client.post(
            f"{base}/rest/v1/leaderboard",
            headers={**headers, "Prefer": "resolution=merge-duplicates,return=representation"},
            params={"on_conflict": "user_id"},
            json={
                "user_id": user_id,
                "display_name": display_name[:80],
                "high_score": new_high,
                "updated_at": updated_at,
            },
        )
        upsert_resp.raise_for_status()

        all_resp = client.get(
            f"{base}/rest/v1/leaderboard",
            params={"select": "user_id,high_score,updated_at"},
            headers=headers,
        )
        all_resp.raise_for_status()
        rank = _rank_for_user(all_resp.json(), user_id)

    return {
        "high_score": new_high,
        "is_new_best": is_new_best,
        "rank": rank,
    }


def _submit_via_postgres(user_id: str, display_name: str, score: int) -> dict[str, Any]:
    user_uuid = UUID(str(user_id))
    with _connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT high_score FROM public.leaderboard WHERE user_id = %s",
                (user_uuid,),
            )
            existing = cur.fetchone()
            previous_high = int(existing["high_score"]) if existing else 0

            cur.execute(
                """
                INSERT INTO public.leaderboard (user_id, display_name, high_score, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    high_score = GREATEST(public.leaderboard.high_score, EXCLUDED.high_score),
                    updated_at = CASE
                        WHEN EXCLUDED.high_score > public.leaderboard.high_score THEN NOW()
                        ELSE public.leaderboard.updated_at
                    END
                RETURNING high_score
                """,
                (user_uuid, display_name[:80], score),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("Insert did not return a row.")

            cur.execute(
                """
                SELECT rank FROM (
                    SELECT user_id, RANK() OVER (ORDER BY high_score DESC, updated_at ASC) AS rank
                    FROM public.leaderboard
                ) ranked
                WHERE user_id = %s
                """,
                (user_uuid,),
            )
            rank_row = cur.fetchone()
            conn.commit()

    high_score = int(row["high_score"])
    return {
        "high_score": high_score,
        "is_new_best": score > previous_high,
        "rank": int(rank_row["rank"]) if rank_row else None,
    }


def submit_high_score(user_id: str, display_name: str, score: int) -> dict[str, Any]:
    if _rest_configured():
        try:
            return _submit_via_rest(user_id, display_name, score)
        except Exception:
            logger.exception("Leaderboard REST submit failed for user %s", user_id)
            if settings.leaderboard_database_url.strip():
                return _submit_via_postgres(user_id, display_name, score)
            raise

    return _submit_via_postgres(user_id, display_name, score)


def _get_via_rest(limit: int, user_id: str | None) -> list[dict[str, Any]]:
    base = settings.supabase_url.strip().rstrip("/")
    headers = _rest_headers()

    with httpx.Client(timeout=15.0) as client:
        response = client.get(
            f"{base}/rest/v1/leaderboard",
            params={
                "select": "user_id,display_name,high_score,updated_at",
                "order": "high_score.desc,updated_at.asc",
                "limit": str(limit),
            },
            headers=headers,
        )
        response.raise_for_status()
        rows = response.json()

    entries: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        updated_at = row.get("updated_at")
        entries.append(
            {
                "rank": index,
                "display_name": str(row["display_name"]),
                "high_score": int(row["high_score"]),
                "updated_at": updated_at if isinstance(updated_at, str) else None,
                "is_you": user_id is not None and str(row["user_id"]) == user_id,
            }
        )
    return entries


def get_leaderboard(limit: int = 25, user_id: str | None = None) -> list[dict[str, Any]]:
    capped_limit = max(1, min(limit, 100))

    if settings.leaderboard_database_url.strip():
        try:
            with _connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT
                            user_id,
                            display_name,
                            high_score,
                            updated_at,
                            RANK() OVER (ORDER BY high_score DESC, updated_at ASC) AS rank
                        FROM public.leaderboard
                        ORDER BY high_score DESC, updated_at ASC
                        LIMIT %s
                        """,
                        (capped_limit,),
                    )
                    rows = cur.fetchall()

            entries: list[dict[str, Any]] = []
            for row in rows:
                updated_at = row["updated_at"]
                entries.append(
                    {
                        "rank": int(row["rank"]),
                        "display_name": str(row["display_name"]),
                        "high_score": int(row["high_score"]),
                        "updated_at": updated_at.isoformat() if isinstance(updated_at, datetime) else None,
                        "is_you": user_id is not None and str(row["user_id"]) == user_id,
                    }
                )
            return entries
        except Exception:
            logger.exception("Leaderboard postgres read failed")
            if not _rest_configured():
                raise

    return _get_via_rest(capped_limit, user_id)


def _profile_via_rest(user_id: str) -> dict[str, Any]:
    base = settings.supabase_url.strip().rstrip("/")
    headers = _rest_headers()

    with httpx.Client(timeout=15.0) as client:
        response = client.get(
            f"{base}/rest/v1/leaderboard",
            params={
                "user_id": f"eq.{user_id}",
                "select": "display_name,high_score,friendly_wins,updated_at",
            },
            headers=headers,
        )
        if response.status_code >= 400:
            # Column may not exist until migration is applied.
            response = client.get(
                f"{base}/rest/v1/leaderboard",
                params={
                    "user_id": f"eq.{user_id}",
                    "select": "display_name,high_score,updated_at",
                },
                headers=headers,
            )
        response.raise_for_status()
        rows = response.json()

        all_resp = client.get(
            f"{base}/rest/v1/leaderboard",
            params={"select": "user_id,high_score,updated_at"},
            headers=headers,
        )
        all_resp.raise_for_status()
        rank = _rank_for_user(all_resp.json(), user_id)

    if not rows:
        return {
            "display_name": "",
            "high_score": 0,
            "friendly_wins": 0,
            "rank": None,
            "updated_at": None,
        }

    row = rows[0]
    updated_at = row.get("updated_at")
    return {
        "display_name": str(row.get("display_name") or ""),
        "high_score": int(row.get("high_score") or 0),
        "friendly_wins": int(row.get("friendly_wins") or 0),
        "rank": rank,
        "updated_at": updated_at if isinstance(updated_at, str) else None,
    }


def _profile_via_postgres(user_id: str) -> dict[str, Any]:
    user_uuid = UUID(str(user_id))
    with _connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                cur.execute(
                    """
                    SELECT display_name, high_score, friendly_wins, updated_at
                    FROM public.leaderboard
                    WHERE user_id = %s
                    """,
                    (user_uuid,),
                )
            except Exception:
                conn.rollback()
                cur.execute(
                    """
                    SELECT display_name, high_score, updated_at
                    FROM public.leaderboard
                    WHERE user_id = %s
                    """,
                    (user_uuid,),
                )
            row = cur.fetchone()
            if row is None:
                return {
                    "display_name": "",
                    "high_score": 0,
                    "friendly_wins": 0,
                    "rank": None,
                    "updated_at": None,
                }

            cur.execute(
                """
                SELECT rank FROM (
                    SELECT user_id, RANK() OVER (ORDER BY high_score DESC, updated_at ASC) AS rank
                    FROM public.leaderboard
                ) ranked
                WHERE user_id = %s
                """,
                (user_uuid,),
            )
            rank_row = cur.fetchone()

    updated_at = row["updated_at"]
    return {
        "display_name": str(row["display_name"]),
        "high_score": int(row["high_score"]),
        "friendly_wins": int(row.get("friendly_wins") or 0),
        "rank": int(rank_row["rank"]) if rank_row else None,
        "updated_at": updated_at.isoformat() if isinstance(updated_at, datetime) else None,
    }


def get_profile(user_id: str) -> dict[str, Any]:
    if _rest_configured():
        try:
            return _profile_via_rest(user_id)
        except Exception:
            logger.exception("Profile REST read failed for user %s", user_id)
            if settings.leaderboard_database_url.strip():
                return _profile_via_postgres(user_id)
            raise

    return _profile_via_postgres(user_id)


def _increment_wins_via_rest(user_id: str, display_name: str) -> int:
    base = settings.supabase_url.strip().rstrip("/")
    headers = _rest_headers()

    with httpx.Client(timeout=15.0) as client:
        existing_resp = client.get(
            f"{base}/rest/v1/leaderboard",
            params={"user_id": f"eq.{user_id}", "select": "high_score,friendly_wins"},
            headers=headers,
        )
        existing_resp.raise_for_status()
        existing_rows = existing_resp.json()
        previous_wins = int(existing_rows[0].get("friendly_wins") or 0) if existing_rows else 0
        previous_high = int(existing_rows[0].get("high_score") or 0) if existing_rows else 0
        new_wins = previous_wins + 1

        upsert_resp = client.post(
            f"{base}/rest/v1/leaderboard",
            headers={**headers, "Prefer": "resolution=merge-duplicates,return=representation"},
            params={"on_conflict": "user_id"},
            json={
                "user_id": user_id,
                "display_name": display_name[:80],
                "high_score": previous_high,
                "friendly_wins": new_wins,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        upsert_resp.raise_for_status()

    return new_wins


def _increment_wins_via_postgres(user_id: str, display_name: str) -> int:
    user_uuid = UUID(str(user_id))
    with _connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO public.leaderboard (user_id, display_name, high_score, friendly_wins, updated_at)
                VALUES (%s, %s, 0, 1, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    friendly_wins = public.leaderboard.friendly_wins + 1
                RETURNING friendly_wins
                """,
                (user_uuid, display_name[:80]),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("Friendly win insert did not return a row.")
            conn.commit()
    return int(row["friendly_wins"])


def increment_friendly_wins(user_id: str, display_name: str) -> int:
    if _rest_configured():
        try:
            return _increment_wins_via_rest(user_id, display_name)
        except Exception:
            logger.exception("Friendly wins REST update failed for user %s", user_id)
            if settings.leaderboard_database_url.strip():
                return _increment_wins_via_postgres(user_id, display_name)
            raise

    return _increment_wins_via_postgres(user_id, display_name)
