"""API routes for the Name Rush initials game."""

from fastapi import APIRouter, HTTPException, Query

from app.schemas import (
    GameGuessRequest,
    GameGuessResponse,
    GameStartRequest,
    GameStartResponse,
    GameStatusResponse,
    HealthResponse,
    InitialsRevealRequest,
    InitialsRevealResponse,
    InitialsRevealEntry,
    RevealPlayerEntry,
)
from app.services.name_game_service import (
    get_game_status,
    get_reveals_for_initials,
    refresh_player_pool,
    start_round,
    validate_guess,
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check(mode: str = Query(default="all_time")) -> HealthResponse:
    status = get_game_status(mode)
    return HealthResponse(
        status="ok",
        app="Name Rush",
        player_count=int(status["player_count"]),
        season=str(status["season"]),
    )


@router.get("/game/status", response_model=GameStatusResponse)
def game_status(mode: str = Query(default="all_time")) -> GameStatusResponse:
    status = get_game_status(mode)
    if int(status["player_count"]) == 0:
        count = refresh_player_pool(mode)
        status = get_game_status(mode)
        status["player_count"] = count
    return GameStatusResponse(
        season=str(status["season"]),
        player_count=int(status["player_count"]),
        timer_seconds=int(status["timer_seconds"]),
        mode=str(status["mode"]),
        mode_label=str(status["mode_label"]),
    )


@router.post("/game/start", response_model=GameStartResponse)
def game_start(payload: GameStartRequest | None = None) -> GameStartResponse:
    mode = payload.mode if payload else "all_time"
    if get_game_status(mode)["player_count"] == 0:
        refresh_player_pool(mode)
    if get_game_status(mode)["player_count"] == 0:
        detail = (
            "Could not load all-time basketball players."
            if mode == "all_time"
            else "Could not load current basketball players."
        )
        raise HTTPException(status_code=503, detail=detail)
    round_payload = start_round([], mode)
    return GameStartResponse(
        initials=str(round_payload["initials"]),
        initials_player_count=int(round_payload["initials_player_count"]),
    )


@router.post("/game/guess", response_model=GameGuessResponse)
def game_guess(payload: GameGuessRequest) -> GameGuessResponse:
    result = validate_guess(
        payload.initials,
        payload.guess,
        payload.used_player_ids,
        payload.mode,
        payload.time_remaining,
    )
    return GameGuessResponse(
        correct=result.correct,
        game_over=result.game_over,
        points=result.points,
        reason=result.reason,
        matched_name=result.matched_name,
        matched_nba_id=result.matched_nba_id,
        next_initials=result.next_initials,
        next_initials_player_count=result.next_initials_player_count,
        matching_players=list(result.matching_players),
    )


@router.post("/game/reveal", response_model=InitialsRevealResponse)
def reveal_initials(payload: InitialsRevealRequest) -> InitialsRevealResponse:
    reveals = get_reveals_for_initials(payload.initials_list, payload.mode)
    return InitialsRevealResponse(
        reveals=[
            InitialsRevealEntry(
                initials=str(entry["initials"]),
                players=[
                    RevealPlayerEntry(
                        full_name=str(player["full_name"]),
                        from_season=str(player.get("from_season", "")),
                        to_season=str(player.get("to_season", "")),
                        career_span=str(player.get("career_span", "")),
                    )
                    for player in entry["players"]
                ],
                player_count=int(entry["player_count"]),
            )
            for entry in reveals
        ]
    )


@router.post("/game/refresh-players")
def refresh_players(mode: str = Query(default="all_time")) -> dict[str, int | str]:
    count = refresh_player_pool(mode)
    status = get_game_status(mode)
    return {
        "player_count": count,
        "mode": str(status["mode"]),
        "message": f"Loaded {count} {status['mode_label']} players.",
    }
