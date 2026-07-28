"""Online leaderboard routes."""

import logging

from fastapi import APIRouter, Header, HTTPException, Query

from app.schemas import (
    CareerGameRequest,
    LeaderboardResponse,
    LeaderboardEntry,
    ProfileResponse,
    SubmitScoreRequest,
    SubmitScoreResponse,
)
from app.services.auth_service import display_name_from_claims, require_auth_user
from app.services.leaderboard_service import (
    LeaderboardUnavailable,
    get_leaderboard,
    get_profile,
    leaderboard_enabled,
    record_career_game,
    submit_high_score,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _leaderboard_unavailable() -> HTTPException:
    return HTTPException(status_code=503, detail="Leaderboard is not configured yet.")


@router.get("/leaderboard", response_model=LeaderboardResponse)
def leaderboard_list(
    limit: int = Query(default=25, ge=1, le=100),
    authorization: str | None = Header(default=None),
) -> LeaderboardResponse:
    if not leaderboard_enabled():
        return LeaderboardResponse(entries=[], enabled=False)

    user_id: str | None = None
    if authorization:
        try:
            claims = require_auth_user(authorization)
            user_id = str(claims["sub"])
        except HTTPException:
            user_id = None

    try:
        entries = get_leaderboard(limit=limit, user_id=user_id)
    except LeaderboardUnavailable as exc:
        raise _leaderboard_unavailable() from exc

    return LeaderboardResponse(
        enabled=True,
        entries=[LeaderboardEntry(**entry) for entry in entries],
    )


@router.post("/leaderboard/submit", response_model=SubmitScoreResponse)
def leaderboard_submit(
    payload: SubmitScoreRequest,
    authorization: str | None = Header(default=None),
) -> SubmitScoreResponse:
    if not leaderboard_enabled():
        raise _leaderboard_unavailable()

    claims = require_auth_user(authorization)
    display_name = display_name_from_claims(claims)

    try:
        result = submit_high_score(str(claims["sub"]), display_name, payload.score)
    except LeaderboardUnavailable as exc:
        raise _leaderboard_unavailable() from exc
    except Exception as exc:
        logger.exception("Leaderboard submit failed for user %s", claims.get("sub"))
        raise HTTPException(status_code=500, detail="Could not save score.") from exc

    return SubmitScoreResponse(
        high_score=int(result["high_score"]),
        is_new_best=bool(result["is_new_best"]),
        rank=result.get("rank"),
    )


@router.get("/leaderboard/me", response_model=ProfileResponse)
def leaderboard_me(
    authorization: str | None = Header(default=None),
) -> ProfileResponse:
    if not leaderboard_enabled():
        raise _leaderboard_unavailable()

    claims = require_auth_user(authorization)
    display_name = display_name_from_claims(claims)

    try:
        profile = get_profile(str(claims["sub"]))
    except LeaderboardUnavailable as exc:
        raise _leaderboard_unavailable() from exc
    except Exception as exc:
        logger.exception("Profile read failed for user %s", claims.get("sub"))
        raise HTTPException(status_code=500, detail="Could not load profile.") from exc

    return ProfileResponse(
        display_name=str(profile.get("display_name") or display_name),
        high_score=int(profile.get("high_score") or 0),
        friendly_wins=int(profile.get("friendly_wins") or 0),
        games_played=int(profile.get("games_played") or 0),
        correct_answers=int(profile.get("correct_answers") or 0),
        total_attempts=int(profile.get("total_attempts") or 0),
        points_earned=int(profile.get("points_earned") or 0),
        accuracy=float(profile.get("accuracy") or 0),
        avg_points=float(profile.get("avg_points") or 0),
        rank=profile.get("rank"),
        updated_at=profile.get("updated_at"),
    )


@router.post("/leaderboard/career", response_model=ProfileResponse)
def leaderboard_career(
    payload: CareerGameRequest,
    authorization: str | None = Header(default=None),
) -> ProfileResponse:
    if not leaderboard_enabled():
        raise _leaderboard_unavailable()

    claims = require_auth_user(authorization)
    display_name = display_name_from_claims(claims)

    try:
        profile = record_career_game(
            str(claims["sub"]),
            display_name,
            payload.score,
            payload.correct,
            payload.attempts,
        )
    except LeaderboardUnavailable as exc:
        raise _leaderboard_unavailable() from exc
    except Exception as exc:
        logger.exception("Career record failed for user %s", claims.get("sub"))
        raise HTTPException(status_code=500, detail="Could not save career stats.") from exc

    return ProfileResponse(
        display_name=str(profile.get("display_name") or display_name),
        high_score=int(profile.get("high_score") or 0),
        friendly_wins=int(profile.get("friendly_wins") or 0),
        games_played=int(profile.get("games_played") or 0),
        correct_answers=int(profile.get("correct_answers") or 0),
        total_attempts=int(profile.get("total_attempts") or 0),
        points_earned=int(profile.get("points_earned") or 0),
        accuracy=float(profile.get("accuracy") or 0),
        avg_points=float(profile.get("avg_points") or 0),
        rank=profile.get("rank"),
        updated_at=profile.get("updated_at"),
    )
