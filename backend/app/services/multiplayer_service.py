"""In-memory private 1v1 multiplayer rooms."""

from __future__ import annotations

import secrets
import string
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from app.services.name_game_service import (
    count_players_for_initials,
    generate_initials_sequence,
    match_guess_for_initials,
)

ROOM_CODE_LENGTH = 6
TOTAL_ROUNDS = 10
ROOM_TTL_SECONDS = 60 * 60
CODE_ALPHABET = string.ascii_uppercase + string.digits


@dataclass
class RoomPlayer:
    player_id: str
    display_name: str


@dataclass
class MultiplayerRoom:
    code: str
    host: RoomPlayer
    sequence: list[str]
    guest: RoomPlayer | None = None
    status: str = "waiting"  # waiting | playing | finished
    round_index: int = 0
    host_score: int = 0
    guest_score: int = 0
    used_player_ids: list[int] = field(default_factory=list)
    last_message: str = "Waiting for opponent..."
    last_winner_id: str | None = None
    last_matched_name: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


_rooms: dict[str, MultiplayerRoom] = {}
_lock = threading.Lock()


class MultiplayerError(Exception):
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def _new_code() -> str:
    for _ in range(20):
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(ROOM_CODE_LENGTH))
        if code not in _rooms:
            return code
    raise MultiplayerError("Could not create a room code. Try again.", 500)


def _cleanup_expired_locked() -> None:
    now = time.time()
    expired = [code for code, room in _rooms.items() if now - room.updated_at > ROOM_TTL_SECONDS]
    for code in expired:
        del _rooms[code]


def _current_initials(room: MultiplayerRoom) -> str:
    if room.round_index >= len(room.sequence):
        return ""
    return room.sequence[room.round_index]


def serialize_room(room: MultiplayerRoom, viewer_id: str | None = None) -> dict[str, Any]:
    initials = _current_initials(room)
    you_are = None
    if viewer_id:
        if viewer_id == room.host.player_id:
            you_are = "host"
        elif room.guest and viewer_id == room.guest.player_id:
            you_are = "guest"

    winner_id = None
    if room.status == "finished":
        if room.host_score > room.guest_score:
            winner_id = room.host.player_id
        elif room.guest_score > room.host_score:
            winner_id = room.guest.player_id if room.guest else None

    return {
        "code": room.code,
        "status": room.status,
        "total_rounds": TOTAL_ROUNDS,
        "round_index": room.round_index,
        "round_number": min(room.round_index + 1, TOTAL_ROUNDS),
        "current_initials": initials,
        "initials_player_count": count_players_for_initials(initials) if initials else 0,
        "host": {
            "player_id": room.host.player_id,
            "display_name": room.host.display_name,
            "score": room.host_score,
        },
        "guest": (
            {
                "player_id": room.guest.player_id,
                "display_name": room.guest.display_name,
                "score": room.guest_score,
            }
            if room.guest
            else None
        ),
        "last_message": room.last_message,
        "last_winner_id": room.last_winner_id,
        "last_matched_name": room.last_matched_name,
        "winner_id": winner_id,
        "you_are": you_are,
    }


def create_room(player_id: str, display_name: str) -> dict[str, Any]:
    name = display_name.strip()[:40] or "Player 1"
    player_id = player_id.strip()
    if not player_id:
        raise MultiplayerError("Missing player id.")

    with _lock:
        _cleanup_expired_locked()
        code = _new_code()
        sequence = generate_initials_sequence(TOTAL_ROUNDS, "all_time")
        room = MultiplayerRoom(
            code=code,
            host=RoomPlayer(player_id=player_id, display_name=name),
            sequence=sequence,
            last_message="Share this code with a friend to start.",
        )
        _rooms[code] = room
        return serialize_room(room, player_id)


def join_room(code: str, player_id: str, display_name: str) -> dict[str, Any]:
    name = display_name.strip()[:40] or "Player 2"
    player_id = player_id.strip()
    room_code = code.strip().upper()
    if not player_id:
        raise MultiplayerError("Missing player id.")
    if not room_code:
        raise MultiplayerError("Enter a room code.")

    with _lock:
        _cleanup_expired_locked()
        room = _rooms.get(room_code)
        if room is None:
            raise MultiplayerError("Room not found.", 404)

        if player_id == room.host.player_id:
            room.updated_at = time.time()
            return serialize_room(room, player_id)

        if room.guest and room.guest.player_id == player_id:
            room.updated_at = time.time()
            return serialize_room(room, player_id)

        if room.guest is not None:
            raise MultiplayerError("This room is already full.")

        if room.status != "waiting":
            raise MultiplayerError("This match already started.")

        room.guest = RoomPlayer(player_id=player_id, display_name=name)
        room.status = "playing"
        room.round_index = 0
        room.host_score = 0
        room.guest_score = 0
        room.used_player_ids = []
        room.last_winner_id = None
        room.last_matched_name = ""
        room.last_message = f"{name} joined. Round 1 — go!"
        room.updated_at = time.time()
        return serialize_room(room, player_id)


def get_room(code: str, viewer_id: str | None = None) -> dict[str, Any]:
    room_code = code.strip().upper()
    with _lock:
        _cleanup_expired_locked()
        room = _rooms.get(room_code)
        if room is None:
            raise MultiplayerError("Room not found.", 404)
        room.updated_at = time.time()
        return serialize_room(room, viewer_id)


def submit_guess(code: str, player_id: str, guess: str) -> dict[str, Any]:
    room_code = code.strip().upper()
    player_id = player_id.strip()
    if not player_id:
        raise MultiplayerError("Missing player id.")

    with _lock:
        room = _rooms.get(room_code)
        if room is None:
            raise MultiplayerError("Room not found.", 404)
        if room.status != "playing":
            raise MultiplayerError("Match is not in progress.")

        is_host = player_id == room.host.player_id
        is_guest = bool(room.guest and player_id == room.guest.player_id)
        if not is_host and not is_guest:
            raise MultiplayerError("You are not in this room.", 403)

        initials = _current_initials(room)
        result = match_guess_for_initials(
            initials,
            guess,
            used_player_ids=room.used_player_ids,
            mode="all_time",
        )

        if not result.correct:
            room.last_message = result.reason or "Incorrect — keep trying!"
            room.updated_at = time.time()
            payload = serialize_room(room, player_id)
            payload["accepted"] = False
            payload["your_feedback"] = result.reason
            return payload

        # First correct answer wins the round.
        if is_host:
            room.host_score += 1
            winner_name = room.host.display_name
        else:
            room.guest_score += 1
            winner_name = room.guest.display_name if room.guest else "Player"

        room.used_player_ids.append(result.matched_nba_id)
        room.last_winner_id = player_id
        room.last_matched_name = result.matched_name
        room.round_index += 1

        if room.round_index >= TOTAL_ROUNDS:
            room.status = "finished"
            if room.host_score > room.guest_score:
                room.last_message = f"{room.host.display_name} wins {room.host_score}-{room.guest_score}!"
            elif room.guest_score > room.host_score:
                guest_name = room.guest.display_name if room.guest else "Guest"
                room.last_message = f"{guest_name} wins {room.guest_score}-{room.host_score}!"
            else:
                room.last_message = f"Draw! {room.host_score}-{room.guest_score}"
        else:
            room.last_message = (
                f"{winner_name} got {result.matched_name}! Round {room.round_index + 1} — go!"
            )

        room.updated_at = time.time()
        payload = serialize_room(room, player_id)
        payload["accepted"] = True
        payload["your_feedback"] = result.reason
        return payload
