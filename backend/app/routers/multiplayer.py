"""Private 1v1 multiplayer routes."""

from fastapi import APIRouter, HTTPException, Query

from app.schemas import (
    MultiplayerCreateRequest,
    MultiplayerGuessRequest,
    MultiplayerJoinRequest,
    MultiplayerRoomResponse,
)
from app.services.multiplayer_service import (
    MultiplayerError,
    create_room,
    get_room,
    join_room,
    submit_guess,
)

router = APIRouter()


def _raise(exc: MultiplayerError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/multiplayer/create", response_model=MultiplayerRoomResponse)
def multiplayer_create(payload: MultiplayerCreateRequest) -> MultiplayerRoomResponse:
    try:
        room = create_room(payload.player_id, payload.display_name)
    except MultiplayerError as exc:
        _raise(exc)
    return MultiplayerRoomResponse(**room)


@router.post("/multiplayer/join", response_model=MultiplayerRoomResponse)
def multiplayer_join(payload: MultiplayerJoinRequest) -> MultiplayerRoomResponse:
    try:
        room = join_room(payload.code, payload.player_id, payload.display_name)
    except MultiplayerError as exc:
        _raise(exc)
    return MultiplayerRoomResponse(**room)


@router.get("/multiplayer/room/{code}", response_model=MultiplayerRoomResponse)
def multiplayer_get_room(
    code: str,
    player_id: str | None = Query(default=None),
) -> MultiplayerRoomResponse:
    try:
        room = get_room(code, player_id)
    except MultiplayerError as exc:
        _raise(exc)
    return MultiplayerRoomResponse(**room)


@router.post("/multiplayer/guess", response_model=MultiplayerRoomResponse)
def multiplayer_guess(payload: MultiplayerGuessRequest) -> MultiplayerRoomResponse:
    try:
        room = submit_guess(payload.code, payload.player_id, payload.guess)
    except MultiplayerError as exc:
        _raise(exc)
    return MultiplayerRoomResponse(**room)
