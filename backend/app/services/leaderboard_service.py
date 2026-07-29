"""Persistent online leaderboard (one high score per user)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from uuid import UUID

import httpx
import psycopg2
from psycopg2.extras import Json, RealDictCursor

from app.config import settings
from app.services.name_game_service import era_label, normalize_era

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


def _empty_profile() -> dict[str, Any]:
    return {
        "display_name": "",
        "high_score": 0,
        "friendly_wins": 0,
        "games_played": 0,
        "correct_answers": 0,
        "total_attempts": 0,
        "points_earned": 0,
        "accuracy": 0.0,
        "avg_points": 0.0,
        "friendly_games_played": 0,
        "friendly_points_earned": 0,
        "friendly_avg_points": 0.0,
        "era_stats": [],
        "rank": None,
        "updated_at": None,
    }


def _parse_era_blob(raw: Any) -> dict[str, Any]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return {}
    if not isinstance(raw, dict):
        return {}
    return {str(key): value for key, value in raw.items() if isinstance(value, dict)}


def _merge_era_stat(
    blob: dict[str, Any],
    era: str,
    score: int,
    correct: int,
    attempts: int,
) -> dict[str, Any]:
    key = normalize_era(era)
    previous = blob.get(key) if isinstance(blob.get(key), dict) else {}
    games = int(previous.get("games_played") or 0) + 1
    next_correct = int(previous.get("correct_answers") or 0) + max(0, correct)
    next_attempts = int(previous.get("total_attempts") or 0) + max(correct, attempts)
    next_points = int(previous.get("points_earned") or 0) + max(0, score)
    next_high = max(int(previous.get("high_score") or 0), max(0, score))
    updated = dict(blob)
    updated[key] = {
        "games_played": games,
        "correct_answers": next_correct,
        "total_attempts": next_attempts,
        "points_earned": next_points,
        "high_score": next_high,
    }
    return updated


def _era_stats_list(raw: Any) -> list[dict[str, Any]]:
    blob = _parse_era_blob(raw)
    entries: list[dict[str, Any]] = []
    for era_key, value in blob.items():
        games = int(value.get("games_played") or 0)
        if games <= 0:
            continue
        correct = int(value.get("correct_answers") or 0)
        attempts = int(value.get("total_attempts") or 0)
        points = int(value.get("points_earned") or 0)
        high = int(value.get("high_score") or 0)
        entries.append(
            {
                "era": normalize_era(era_key),
                "era_label": era_label(era_key),
                "games_played": games,
                "correct_answers": correct,
                "total_attempts": attempts,
                "points_earned": points,
                "high_score": high,
                "accuracy": round((correct / attempts) * 100, 1) if attempts > 0 else 0.0,
                "avg_points": round(points / games, 1) if games > 0 else 0.0,
            }
        )
    entries.sort(key=lambda row: (-float(row["avg_points"]), -int(row["high_score"]), row["era_label"]))
    return entries


def _with_career_rates(profile: dict[str, Any]) -> dict[str, Any]:
    games = int(profile.get("games_played") or 0)
    correct = int(profile.get("correct_answers") or 0)
    attempts = int(profile.get("total_attempts") or 0)
    points = int(profile.get("points_earned") or 0)
    friendly_games = int(profile.get("friendly_games_played") or 0)
    friendly_points = int(profile.get("friendly_points_earned") or 0)
    profile["games_played"] = games
    profile["correct_answers"] = correct
    profile["total_attempts"] = attempts
    profile["points_earned"] = points
    profile["friendly_games_played"] = friendly_games
    profile["friendly_points_earned"] = friendly_points
    profile["accuracy"] = round((correct / attempts) * 100, 1) if attempts > 0 else 0.0
    profile["avg_points"] = round(points / games, 1) if games > 0 else 0.0
    profile["friendly_avg_points"] = (
        round(friendly_points / friendly_games, 1) if friendly_games > 0 else 0.0
    )
    profile["era_stats"] = _era_stats_list(profile.get("solo_era_stats"))
    return profile


def _profile_via_rest(user_id: str) -> dict[str, Any]:
    base = settings.supabase_url.strip().rstrip("/")
    headers = _rest_headers()
    select_full = (
        "display_name,high_score,friendly_wins,games_played,correct_answers,"
        "total_attempts,points_earned,friendly_games_played,friendly_points_earned,"
        "solo_era_stats,updated_at"
    )

    with httpx.Client(timeout=15.0) as client:
        response = client.get(
            f"{base}/rest/v1/leaderboard",
            params={"user_id": f"eq.{user_id}", "select": select_full},
            headers=headers,
        )
        if response.status_code >= 400:
            response = client.get(
                f"{base}/rest/v1/leaderboard",
                params={
                    "user_id": f"eq.{user_id}",
                    "select": (
                        "display_name,high_score,friendly_wins,games_played,correct_answers,"
                        "total_attempts,points_earned,friendly_games_played,friendly_points_earned,updated_at"
                    ),
                },
                headers=headers,
            )
        if response.status_code >= 400:
            response = client.get(
                f"{base}/rest/v1/leaderboard",
                params={
                    "user_id": f"eq.{user_id}",
                    "select": "display_name,high_score,friendly_wins,updated_at",
                },
                headers=headers,
            )
        if response.status_code >= 400:
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
        return _empty_profile()

    row = rows[0]
    updated_at = row.get("updated_at")
    return _with_career_rates(
        {
            "display_name": str(row.get("display_name") or ""),
            "high_score": int(row.get("high_score") or 0),
            "friendly_wins": int(row.get("friendly_wins") or 0),
            "games_played": int(row.get("games_played") or 0),
            "correct_answers": int(row.get("correct_answers") or 0),
            "total_attempts": int(row.get("total_attempts") or 0),
            "points_earned": int(row.get("points_earned") or 0),
            "friendly_games_played": int(row.get("friendly_games_played") or 0),
            "friendly_points_earned": int(row.get("friendly_points_earned") or 0),
            "solo_era_stats": row.get("solo_era_stats") or {},
            "rank": rank,
            "updated_at": updated_at if isinstance(updated_at, str) else None,
        }
    )


def _profile_via_postgres(user_id: str) -> dict[str, Any]:
    user_uuid = UUID(str(user_id))
    with _connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                cur.execute(
                    """
                    SELECT display_name, high_score, friendly_wins, games_played,
                           correct_answers, total_attempts, points_earned,
                           friendly_games_played, friendly_points_earned,
                           solo_era_stats, updated_at
                    FROM public.leaderboard
                    WHERE user_id = %s
                    """,
                    (user_uuid,),
                )
            except Exception:
                conn.rollback()
                try:
                    cur.execute(
                        """
                        SELECT display_name, high_score, friendly_wins, games_played,
                               correct_answers, total_attempts, points_earned,
                               friendly_games_played, friendly_points_earned, updated_at
                        FROM public.leaderboard
                        WHERE user_id = %s
                        """,
                        (user_uuid,),
                    )
                except Exception:
                    conn.rollback()
                    try:
                        cur.execute(
                            """
                            SELECT display_name, high_score, friendly_wins, games_played,
                                   correct_answers, total_attempts, points_earned, updated_at
                            FROM public.leaderboard
                            WHERE user_id = %s
                            """,
                            (user_uuid,),
                        )
                    except Exception:
                        conn.rollback()
                        cur.execute(
                            """
                            SELECT display_name, high_score, friendly_wins, updated_at
                            FROM public.leaderboard
                            WHERE user_id = %s
                            """,
                            (user_uuid,),
                        )
            row = cur.fetchone()
            if row is None:
                return _empty_profile()

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
    return _with_career_rates(
        {
            "display_name": str(row["display_name"]),
            "high_score": int(row["high_score"]),
            "friendly_wins": int(row.get("friendly_wins") or 0),
            "games_played": int(row.get("games_played") or 0),
            "correct_answers": int(row.get("correct_answers") or 0),
            "total_attempts": int(row.get("total_attempts") or 0),
            "points_earned": int(row.get("points_earned") or 0),
            "friendly_games_played": int(row.get("friendly_games_played") or 0),
            "friendly_points_earned": int(row.get("friendly_points_earned") or 0),
            "solo_era_stats": row.get("solo_era_stats") or {},
            "rank": int(rank_row["rank"]) if rank_row else None,
            "updated_at": updated_at.isoformat() if isinstance(updated_at, datetime) else None,
        }
    )


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


def _record_career_via_rest(
    user_id: str,
    display_name: str,
    score: int,
    correct: int,
    attempts: int,
    era: str = "all_time",
) -> dict[str, Any]:
    base = settings.supabase_url.strip().rstrip("/")
    headers = _rest_headers()
    correct = max(0, correct)
    attempts = max(correct, attempts)
    resolved_era = normalize_era(era)

    with httpx.Client(timeout=15.0) as client:
        existing_resp = client.get(
            f"{base}/rest/v1/leaderboard",
            params={
                "user_id": f"eq.{user_id}",
                "select": (
                    "high_score,friendly_wins,games_played,correct_answers,"
                    "total_attempts,points_earned,solo_era_stats"
                ),
            },
            headers=headers,
        )
        if existing_resp.status_code >= 400:
            existing_resp = client.get(
                f"{base}/rest/v1/leaderboard",
                params={
                    "user_id": f"eq.{user_id}",
                    "select": (
                        "high_score,friendly_wins,games_played,correct_answers,"
                        "total_attempts,points_earned"
                    ),
                },
                headers=headers,
            )
        if existing_resp.status_code >= 400:
            existing_resp = client.get(
                f"{base}/rest/v1/leaderboard",
                params={"user_id": f"eq.{user_id}", "select": "high_score,friendly_wins"},
                headers=headers,
            )
        existing_resp.raise_for_status()
        existing_rows = existing_resp.json()
        previous = existing_rows[0] if existing_rows else {}
        previous_high = int(previous.get("high_score") or 0)
        new_high = max(previous_high, score)
        era_blob = _merge_era_stat(
            _parse_era_blob(previous.get("solo_era_stats")),
            resolved_era,
            score,
            correct,
            attempts,
        )
        payload = {
            "user_id": user_id,
            "display_name": display_name[:80],
            "high_score": new_high,
            "friendly_wins": int(previous.get("friendly_wins") or 0),
            "games_played": int(previous.get("games_played") or 0) + 1,
            "correct_answers": int(previous.get("correct_answers") or 0) + correct,
            "total_attempts": int(previous.get("total_attempts") or 0) + attempts,
            "points_earned": int(previous.get("points_earned") or 0) + score,
            "solo_era_stats": era_blob,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        upsert_resp = client.post(
            f"{base}/rest/v1/leaderboard",
            headers={**headers, "Prefer": "resolution=merge-duplicates,return=representation"},
            params={"on_conflict": "user_id"},
            json=payload,
        )
        if upsert_resp.status_code >= 400 and "solo_era_stats" in payload:
            payload.pop("solo_era_stats", None)
            upsert_resp = client.post(
                f"{base}/rest/v1/leaderboard",
                headers={**headers, "Prefer": "resolution=merge-duplicates,return=representation"},
                params={"on_conflict": "user_id"},
                json=payload,
            )
        upsert_resp.raise_for_status()

    return get_profile(user_id)


def _record_career_via_postgres(
    user_id: str,
    display_name: str,
    score: int,
    correct: int,
    attempts: int,
    era: str = "all_time",
) -> dict[str, Any]:
    user_uuid = UUID(str(user_id))
    correct = max(0, correct)
    attempts = max(correct, attempts)
    resolved_era = normalize_era(era)
    with _connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            existing_blob: dict[str, Any] = {}
            try:
                cur.execute(
                    "SELECT solo_era_stats FROM public.leaderboard WHERE user_id = %s",
                    (user_uuid,),
                )
                existing = cur.fetchone()
                existing_blob = _parse_era_blob((existing or {}).get("solo_era_stats"))
            except Exception:
                conn.rollback()
            era_blob = _merge_era_stat(existing_blob, resolved_era, score, correct, attempts)
            try:
                cur.execute(
                    """
                    INSERT INTO public.leaderboard (
                        user_id, display_name, high_score, friendly_wins,
                        games_played, correct_answers, total_attempts, points_earned,
                        solo_era_stats, updated_at
                    )
                    VALUES (%s, %s, %s, 0, 1, %s, %s, %s, %s, NOW())
                    ON CONFLICT (user_id) DO UPDATE SET
                        display_name = EXCLUDED.display_name,
                        high_score = GREATEST(public.leaderboard.high_score, EXCLUDED.high_score),
                        games_played = public.leaderboard.games_played + 1,
                        correct_answers = public.leaderboard.correct_answers + EXCLUDED.correct_answers,
                        total_attempts = public.leaderboard.total_attempts + EXCLUDED.total_attempts,
                        points_earned = public.leaderboard.points_earned + EXCLUDED.points_earned,
                        solo_era_stats = EXCLUDED.solo_era_stats,
                        updated_at = CASE
                            WHEN EXCLUDED.high_score > public.leaderboard.high_score THEN NOW()
                            ELSE public.leaderboard.updated_at
                        END
                    """,
                    (user_uuid, display_name[:80], score, correct, attempts, score, Json(era_blob)),
                )
            except Exception:
                conn.rollback()
                cur.execute(
                    """
                    INSERT INTO public.leaderboard (
                        user_id, display_name, high_score, friendly_wins,
                        games_played, correct_answers, total_attempts, points_earned, updated_at
                    )
                    VALUES (%s, %s, %s, 0, 1, %s, %s, %s, NOW())
                    ON CONFLICT (user_id) DO UPDATE SET
                        display_name = EXCLUDED.display_name,
                        high_score = GREATEST(public.leaderboard.high_score, EXCLUDED.high_score),
                        games_played = public.leaderboard.games_played + 1,
                        correct_answers = public.leaderboard.correct_answers + EXCLUDED.correct_answers,
                        total_attempts = public.leaderboard.total_attempts + EXCLUDED.total_attempts,
                        points_earned = public.leaderboard.points_earned + EXCLUDED.points_earned,
                        updated_at = CASE
                            WHEN EXCLUDED.high_score > public.leaderboard.high_score THEN NOW()
                            ELSE public.leaderboard.updated_at
                        END
                    """,
                    (user_uuid, display_name[:80], score, correct, attempts, score),
                )
            conn.commit()
    return get_profile(user_id)


def record_career_game(
    user_id: str,
    display_name: str,
    score: int,
    correct: int,
    attempts: int,
    era: str = "all_time",
) -> dict[str, Any]:
    if _rest_configured():
        try:
            return _record_career_via_rest(user_id, display_name, score, correct, attempts, era)
        except Exception:
            logger.exception("Career REST update failed for user %s", user_id)
            if settings.leaderboard_database_url.strip():
                return _record_career_via_postgres(
                    user_id, display_name, score, correct, attempts, era
                )
            raise

    return _record_career_via_postgres(user_id, display_name, score, correct, attempts, era)


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


def _record_friendly_game_via_rest(user_id: str, display_name: str, score: int) -> None:
    base = settings.supabase_url.strip().rstrip("/")
    headers = _rest_headers()
    score = max(0, score)

    with httpx.Client(timeout=15.0) as client:
        existing_resp = client.get(
            f"{base}/rest/v1/leaderboard",
            params={
                "user_id": f"eq.{user_id}",
                "select": "high_score,friendly_wins,friendly_games_played,friendly_points_earned",
            },
            headers=headers,
        )
        if existing_resp.status_code >= 400:
            existing_resp = client.get(
                f"{base}/rest/v1/leaderboard",
                params={"user_id": f"eq.{user_id}", "select": "high_score,friendly_wins"},
                headers=headers,
            )
        existing_resp.raise_for_status()
        existing_rows = existing_resp.json()
        previous = existing_rows[0] if existing_rows else {}
        payload = {
            "user_id": user_id,
            "display_name": display_name[:80],
            "high_score": int(previous.get("high_score") or 0),
            "friendly_wins": int(previous.get("friendly_wins") or 0),
            "friendly_games_played": int(previous.get("friendly_games_played") or 0) + 1,
            "friendly_points_earned": int(previous.get("friendly_points_earned") or 0) + score,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        upsert_resp = client.post(
            f"{base}/rest/v1/leaderboard",
            headers={**headers, "Prefer": "resolution=merge-duplicates,return=representation"},
            params={"on_conflict": "user_id"},
            json=payload,
        )
        upsert_resp.raise_for_status()


def _record_friendly_game_via_postgres(user_id: str, display_name: str, score: int) -> None:
    user_uuid = UUID(str(user_id))
    score = max(0, score)
    with _connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO public.leaderboard (
                    user_id, display_name, high_score, friendly_wins,
                    friendly_games_played, friendly_points_earned, updated_at
                )
                VALUES (%s, %s, 0, 0, 1, %s, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    friendly_games_played = public.leaderboard.friendly_games_played + 1,
                    friendly_points_earned = public.leaderboard.friendly_points_earned + EXCLUDED.friendly_points_earned
                """,
                (user_uuid, display_name[:80], score),
            )
            conn.commit()


def record_friendly_game(user_id: str, display_name: str, score: int) -> None:
    """Record one finished friendly match for averages (points = rounds won)."""
    if _rest_configured():
        try:
            _record_friendly_game_via_rest(user_id, display_name, score)
            return
        except Exception:
            logger.exception("Friendly career REST update failed for user %s", user_id)
            if settings.leaderboard_database_url.strip():
                _record_friendly_game_via_postgres(user_id, display_name, score)
                return
            raise

    _record_friendly_game_via_postgres(user_id, display_name, score)
