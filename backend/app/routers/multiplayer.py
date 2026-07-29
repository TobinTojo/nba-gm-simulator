"""Private multiplayer routes (Google sign-in required, 2–4 players)."""

from fastapi import APIRouter, Header, HTTPException

from app.schemas import (
    MultiplayerCreateRequest,
    MultiplayerGuessRequest,
    MultiplayerJoinRequest,
    MultiplayerLeaveRequest,
    MultiplayerPassRequest,
    MultiplayerRematchRequest,
    MultiplayerRoomResponse,
    MultiplayerSetRoundsRequest,
    MultiplayerStartRequest,
)
from app.services.auth_service import (
    avatar_url_from_claims,
    display_name_from_claims,
    require_auth_user,
)
from app.services.multiplayer_service import (
    MultiplayerError,
    create_room,
    get_room,
    join_room,
    leave_room,
    rematch,
    set_settings,
    start_match,
    submit_guess,
    submit_pass,
)

router = APIRouter()


def _raise(exc: MultiplayerError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/multiplayer/create", response_model=MultiplayerRoomResponse)
def multiplayer_create(
    payload: MultiplayerCreateRequest,
    authorization: str | None = Header(default=None),
) -> MultiplayerRoomResponse:
    claims = require_auth_user(authorization)
    try:
        room = create_room(
            str(claims["sub"]),
            display_name_from_claims(claims),
            payload.total_rounds,
            payload.era,
            avatar_url_from_claims(claims),
        )
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
        room = join_room(
            payload.code,
            str(claims["sub"]),
            display_name_from_claims(claims),
            avatar_url_from_claims(claims),
        )
    except MultiplayerError as exc:
        _raise(exc)
    return MultiplayerRoomResponse(**room)


@router.post("/multiplayer/rounds", response_model=MultiplayerRoomResponse)
def multiplayer_set_rounds(
    payload: MultiplayerSetRoundsRequest,
    authorization: str | None = Header(default=None),
) -> MultiplayerRoomResponse:
    claims = require_auth_user(authorization)
    try:
        room = set_settings(
            payload.code,
            str(claims["sub"]),
            total_rounds=payload.total_rounds,
            era=payload.era,
        )
    except MultiplayerError as exc:
        _raise(exc)
    return MultiplayerRoomResponse(**room)


@router.post("/multiplayer/start", response_model=MultiplayerRoomResponse)
def multiplayer_start(
    payload: MultiplayerStartRequest,
    authorization: str | None = Header(default=None),
) -> MultiplayerRoomResponse:
    claims = require_auth_user(authorization)
    try:
        room = start_match(payload.code, str(claims["sub"]))
    except MultiplayerError as exc:
        _raise(exc)
    return MultiplayerRoomResponse(**room)


@router.post("/multiplayer/rematch", response_model=MultiplayerRoomResponse)
def multiplayer_rematch(
    payload: MultiplayerRematchRequest,
    authorization: str | None = Header(default=None),
) -> MultiplayerRoomResponse:
    claims = require_auth_user(authorization)
    try:
        room = rematch(payload.code, str(claims["sub"]))
    except MultiplayerError as exc:
        _raise(exc)
    return MultiplayerRoomResponse(**room)


@router.post("/multiplayer/leave", response_model=MultiplayerRoomResponse)
def multiplayer_leave(
    payload: MultiplayerLeaveRequest,
    authorization: str | None = Header(default=None),
) -> MultiplayerRoomResponse:
    claims = require_auth_user(authorization)
    try:
        room = leave_room(payload.code, str(claims["sub"]))
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


@router.post("/multiplayer/pass", response_model=MultiplayerRoomResponse)
def multiplayer_pass(
    payload: MultiplayerPassRequest,
    authorization: str | None = Header(default=None),
) -> MultiplayerRoomResponse:
    claims = require_auth_user(authorization)
    try:
        room = submit_pass(payload.code, str(claims["sub"]))
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
