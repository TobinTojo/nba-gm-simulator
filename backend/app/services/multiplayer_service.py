"""In-memory private multiplayer rooms (2–4 players)."""

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
DEFAULT_ROUNDS = 9
ALLOWED_ROUNDS = frozenset({9, 12, 15})
MAX_PLAYERS = 4
ROUND_SECONDS = 30
ROOM_TTL_SECONDS = 60 * 60
CODE_ALPHABET = string.ascii_uppercase + string.digits


@dataclass
class RoomPlayer:
    player_id: str
    display_name: str
    score: int = 0


@dataclass
class MultiplayerRoom:
    code: str
    host_id: str
    players: list[RoomPlayer]
    total_rounds: int
    sequence: list[str]
    status: str = "waiting"  # waiting | playing | finished
    round_index: int = 0
    used_player_ids: list[int] = field(default_factory=list)
    last_message: str = "Waiting for players..."
    last_winner_id: str | None = None
    last_matched_name: str = ""
    round_started_at: float | None = None
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


def _normalize_rounds(total_rounds: int | None) -> int:
    if total_rounds is None:
        return DEFAULT_ROUNDS
    if total_rounds not in ALLOWED_ROUNDS:
        raise MultiplayerError("Rounds must be 9, 12, or 15.")
    return total_rounds


def _find_player(room: MultiplayerRoom, player_id: str) -> RoomPlayer | None:
    for player in room.players:
        if player.player_id == player_id:
            return player
    return None


def _current_initials(room: MultiplayerRoom) -> str:
    if room.round_index >= len(room.sequence):
        return ""
    return room.sequence[room.round_index]


def _finish_match(room: MultiplayerRoom) -> None:
    room.status = "finished"
    room.round_started_at = None
    if not room.players:
        room.last_message = "Match over."
        return

    top = max(player.score for player in room.players)
    winners = [player for player in room.players if player.score == top]
    if len(winners) == 1:
        room.last_message = f"{winners[0].display_name} wins with {top}!"
    else:
        names = ", ".join(player.display_name for player in winners)
        room.last_message = f"Draw between {names} at {top}!"


def _advance_round(room: MultiplayerRoom, message: str) -> None:
    room.round_index += 1
    room.last_winner_id = None
    room.last_matched_name = ""
    if room.round_index >= room.total_rounds:
        _finish_match(room)
    else:
        room.round_started_at = time.time()
        room.last_message = message


def _time_left(room: MultiplayerRoom) -> int | None:
    if room.status != "playing" or room.round_started_at is None:
        return None
    elapsed = time.time() - room.round_started_at
    return max(0, int(ROUND_SECONDS - elapsed))


def _maybe_expire_round(room: MultiplayerRoom) -> bool:
    if room.status != "playing" or room.round_started_at is None:
        return False
    if time.time() - room.round_started_at < ROUND_SECONDS:
        return False

    timed_out_initials = _current_initials(room)
    if room.round_index + 1 >= room.total_rounds:
        room.round_index += 1
        room.last_winner_id = None
        room.last_matched_name = ""
        _finish_match(room)
        room.last_message = f"Time's up on {timed_out_initials}. {room.last_message}"
    else:
        next_round = room.round_index + 2
        _advance_round(
            room,
            f"Time's up on {timed_out_initials} — nobody scored. Round {next_round} — go!",
        )
    room.updated_at = time.time()
    return True


def serialize_room(room: MultiplayerRoom, viewer_id: str | None = None) -> dict[str, Any]:
    initials = _current_initials(room)
    you_are_host = bool(viewer_id and viewer_id == room.host_id)
    in_room = bool(viewer_id and _find_player(room, viewer_id))

    winner_ids: list[str] = []
    if room.status == "finished" and room.players:
        top = max(player.score for player in room.players)
        winner_ids = [player.player_id for player in room.players if player.score == top]

    return {
        "code": room.code,
        "status": room.status,
        "max_players": MAX_PLAYERS,
        "total_rounds": room.total_rounds,
        "round_seconds": ROUND_SECONDS,
        "round_index": room.round_index,
        "round_number": min(room.round_index + 1, room.total_rounds),
        "time_left": _time_left(room),
        "current_initials": initials,
        "initials_player_count": count_players_for_initials(initials) if initials else 0,
        "players": [
            {
                "player_id": player.player_id,
                "display_name": player.display_name,
                "score": player.score,
                "is_host": player.player_id == room.host_id,
                "is_you": viewer_id == player.player_id,
            }
            for player in room.players
        ],
        "last_message": room.last_message,
        "last_winner_id": room.last_winner_id,
        "last_matched_name": room.last_matched_name,
        "winner_ids": winner_ids,
        "you_are_host": you_are_host,
        "in_room": in_room,
        "can_start": you_are_host and room.status == "waiting" and len(room.players) >= 2,
    }


def create_room(player_id: str, display_name: str, total_rounds: int | None = None) -> dict[str, Any]:
    name = display_name.strip()[:40] or "Player 1"
    player_id = player_id.strip()
    if not player_id:
        raise MultiplayerError("Missing player id.")

    rounds = _normalize_rounds(total_rounds)

    with _lock:
        _cleanup_expired_locked()
        code = _new_code()
        sequence = generate_initials_sequence(rounds, "all_time")
        host = RoomPlayer(player_id=player_id, display_name=name)
        room = MultiplayerRoom(
            code=code,
            host_id=player_id,
            players=[host],
            total_rounds=rounds,
            sequence=sequence,
            last_message=f"Share this code. Waiting for players ({rounds} rounds).",
        )
        _rooms[code] = room
        return serialize_room(room, player_id)


def join_room(code: str, player_id: str, display_name: str) -> dict[str, Any]:
    name = display_name.strip()[:40] or "Player"
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

        existing = _find_player(room, player_id)
        if existing:
            _maybe_expire_round(room)
            room.updated_at = time.time()
            return serialize_room(room, player_id)

        if room.status != "waiting":
            raise MultiplayerError("This match already started.")

        if len(room.players) >= MAX_PLAYERS:
            raise MultiplayerError("This room is full (max 4 players).")

        room.players.append(RoomPlayer(player_id=player_id, display_name=name))
        room.last_message = f"{name} joined ({len(room.players)}/{MAX_PLAYERS})."
        room.updated_at = time.time()
        return serialize_room(room, player_id)


def set_rounds(code: str, player_id: str, total_rounds: int) -> dict[str, Any]:
    room_code = code.strip().upper()
    player_id = player_id.strip()
    rounds = _normalize_rounds(total_rounds)

    with _lock:
        room = _rooms.get(room_code)
        if room is None:
            raise MultiplayerError("Room not found.", 404)
        if player_id != room.host_id:
            raise MultiplayerError("Only the host can change rounds.", 403)
        if room.status != "waiting":
            raise MultiplayerError("Rounds can only be changed before the match starts.")

        room.total_rounds = rounds
        room.sequence = generate_initials_sequence(rounds, "all_time")
        room.last_message = f"Host set the match to {rounds} rounds."
        room.updated_at = time.time()
        return serialize_room(room, player_id)


def start_match(code: str, player_id: str) -> dict[str, Any]:
    room_code = code.strip().upper()
    player_id = player_id.strip()

    with _lock:
        room = _rooms.get(room_code)
        if room is None:
            raise MultiplayerError("Room not found.", 404)
        if player_id != room.host_id:
            raise MultiplayerError("Only the host can start the match.", 403)
        if room.status != "waiting":
            raise MultiplayerError("Match already started.")
        if len(room.players) < 2:
            raise MultiplayerError("Need at least 2 players to start.")

        for player in room.players:
            player.score = 0
        room.status = "playing"
        room.round_index = 0
        room.used_player_ids = []
        room.last_winner_id = None
        room.last_matched_name = ""
        room.round_started_at = time.time()
        room.last_message = f"Match started — Round 1 of {room.total_rounds}!"
        room.updated_at = time.time()
        return serialize_room(room, player_id)


def get_room(code: str, viewer_id: str | None = None) -> dict[str, Any]:
    room_code = code.strip().upper()
    with _lock:
        _cleanup_expired_locked()
        room = _rooms.get(room_code)
        if room is None:
            raise MultiplayerError("Room not found.", 404)
        _maybe_expire_round(room)
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

        _maybe_expire_round(room)

        if room.status != "playing":
            raise MultiplayerError("Match is not in progress.")

        player = _find_player(room, player_id)
        if player is None:
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

        player.score += 1
        room.used_player_ids.append(result.matched_nba_id)
        room.last_winner_id = player_id
        room.last_matched_name = result.matched_name

        if room.round_index + 1 >= room.total_rounds:
            room.round_index += 1
            _finish_match(room)
            room.last_message = f"{player.display_name} got {result.matched_name}! {room.last_message}"
        else:
            next_round = room.round_index + 2
            _advance_round(
                room,
                f"{player.display_name} got {result.matched_name}! Round {next_round} — go!",
            )

        room.updated_at = time.time()
        payload = serialize_room(room, player_id)
        payload["accepted"] = True
        payload["your_feedback"] = result.reason
        return payload
