"""Persistent online leaderboard (one high score per user)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg2
from psycopg2.extras import RealDictCursor

from app.config import settings


class LeaderboardUnavailable(Exception):
    pass


def leaderboard_enabled() -> bool:
    return bool(settings.leaderboard_database_url.strip())


def _connection():
    if not leaderboard_enabled():
        raise LeaderboardUnavailable("Leaderboard database is not configured.")
    return psycopg2.connect(settings.leaderboard_database_url, connect_timeout=10)


def submit_high_score(user_id: str, display_name: str, score: int) -> dict[str, Any]:
    user_uuid = UUID(str(user_id))
    with _connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT high_score FROM leaderboard WHERE user_id = %s",
                (user_uuid,),
            )
            existing = cur.fetchone()
            previous_high = int(existing["high_score"]) if existing else 0

            cur.execute(
                """
                INSERT INTO leaderboard (user_id, display_name, high_score, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    high_score = GREATEST(leaderboard.high_score, EXCLUDED.high_score),
                    updated_at = CASE
                        WHEN EXCLUDED.high_score > leaderboard.high_score THEN NOW()
                        ELSE leaderboard.updated_at
                    END
                RETURNING high_score
                """,
                (user_uuid, display_name[:80], score),
            )
            row = cur.fetchone()

            cur.execute(
                """
                SELECT rank FROM (
                    SELECT user_id, RANK() OVER (ORDER BY high_score DESC, updated_at ASC) AS rank
                    FROM leaderboard
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


def get_leaderboard(limit: int = 25, user_id: str | None = None) -> list[dict[str, Any]]:
    capped_limit = max(1, min(limit, 100))
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
                FROM leaderboard
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
