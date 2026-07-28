"""Private 1v1 multiplayer routes (Google sign-in required)."""

from fastapi import APIRouter, Header, HTTPException, Query

from app.schemas import (
    MultiplayerGuessRequest,
    MultiplayerJoinRequest,
    MultiplayerRoomResponse,
)
from app.services.auth_service import display_name_from_claims, require_auth_user
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
def multiplayer_create(authorization: str | None = Header(default=None)) -> MultiplayerRoomResponse:
    claims = require_auth_user(authorization)
    try:
        room = create_room(str(claims["sub"]), display_name_from_claims(claims))
    except MultiplayerError as exc:
        _raise(exc)
    return MultiplayerRoomResponse(**room)


@router.post("/multiplayer/join", response_model=MultiplayerRoomResponse)
def multiplayer_join(
    payload: MultiplayerJoinRequest,
    authorization: str | None = Header(default=None),
) -> MultiplayerRoomResponse:
    claims = require_auth_user(authorization)
    try:
        room = join_room(payload.code, str(claims["sub"]), display_name_from_claims(claims))
    except MultiplayerError as exc:
        _raise(exc)
    return MultiplayerRoomResponse(**room)


@router.get("/multiplayer/room/{code}", response_model=MultiplayerRoomResponse)
def multiplayer_get_room(
    code: str,
    authorization: str | None = Header(default=None),
) -> MultiplayerRoomResponse:
    claims = require_auth_user(authorization)
    try:
        room = get_room(code, str(claims["sub"]))
    except MultiplayerError as exc:
        _raise(exc)
    return MultiplayerRoomResponse(**room)


@router.post("/multiplayer/guess", response_model=MultiplayerRoomResponse)
def multiplayer_guess(
    payload: MultiplayerGuessRequest,
    authorization: str | None = Header(default=None),
) -> MultiplayerRoomResponse:
    claims = require_auth_user(authorization)
    try:
        room = submit_guess(payload.code, str(claims["sub"]), payload.guess)
    except MultiplayerError as exc:
        _raise(exc)
    return MultiplayerRoomResponse(**room)
