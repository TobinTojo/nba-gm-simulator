"""In-memory private multiplayer rooms (2–4 players)."""

from __future__ import annotations

import secrets
import string
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from app.services.name_game_service import (
    count_players_for_initials_era,
    era_label,
    generate_initials_sequence,
    match_guess_for_initials,
    normalize_era,
)

ROOM_CODE_LENGTH = 6
DEFAULT_ROUNDS = 9
ALLOWED_ROUNDS = frozenset({9, 12, 15})
MAX_PLAYERS = 4
ROUND_SECONDS = 30
COUNTDOWN_SECONDS = 3
ROOM_TTL_SECONDS = 60 * 60
CODE_ALPHABET = string.ascii_uppercase + string.digits
DEFAULT_ERA = "all_time"


@dataclass
class RoomPlayer:
    player_id: str
    display_name: str
    score: int = 0
    avatar_url: str | None = None


@dataclass
class MultiplayerRoom:
    code: str
    host_id: str
    players: list[RoomPlayer]
    total_rounds: int
    era: str
    sequence: list[str]
    status: str = "waiting"  # waiting | countdown | playing | finished
    is_public: bool = False
    round_index: int = 0
    used_player_ids: list[int] = field(default_factory=list)
    round_passes: set[str] = field(default_factory=set)
    rematch_ready: set[str] = field(default_factory=set)
    last_message: str = "Waiting for players..."
    last_winner_id: str | None = None
    last_matched_name: str = ""
    round_started_at: float | None = None
    countdown_started_at: float | None = None
    friendly_win_recorded: bool = False
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


def _build_sequence(total_rounds: int, era: str) -> list[str]:
    try:
        return generate_initials_sequence(total_rounds, "all_time", era)
    except ValueError as exc:
        raise MultiplayerError(str(exc)) from exc


def _find_player(room: MultiplayerRoom, player_id: str) -> RoomPlayer | None:
    for player in room.players:
        if player.player_id == player_id:
            return player
    return None


def _current_initials(room: MultiplayerRoom) -> str:
    if room.round_index >= len(room.sequence):
        return ""
    return room.sequence[room.round_index]


def _record_friendly_1v1_win(room: MultiplayerRoom, winners: list[RoomPlayer]) -> None:
    """Persist friendly match stats and a sole win when the match was exactly 2 players."""
    if room.friendly_win_recorded:
        return

    try:
        from app.services.leaderboard_service import (
            increment_friendly_wins,
            leaderboard_enabled,
            record_friendly_game,
        )

        if not leaderboard_enabled():
            return

        for player in room.players:
            record_friendly_game(player.player_id, player.display_name, player.score)

        if len(room.players) == 2 and len(winners) == 1:
            increment_friendly_wins(winners[0].player_id, winners[0].display_name)

        room.friendly_win_recorded = True
    except Exception:
        # Stats are best-effort; never block match completion.
        pass


def _closed_room_payload(room: MultiplayerRoom, message: str) -> dict[str, Any]:
    return {
        "code": room.code,
        "status": "closed",
        "max_players": MAX_PLAYERS,
        "total_rounds": room.total_rounds,
        "era": room.era,
        "era_label": era_label(room.era),
        "is_public": room.is_public,
        "round_seconds": ROUND_SECONDS,
        "countdown_seconds": COUNTDOWN_SECONDS,
        "round_index": room.round_index,
        "round_number": min(room.round_index + 1, room.total_rounds),
        "time_left": None,
        "countdown_left": None,
        "current_initials": "",
        "initials_player_count": 0,
        "players": [],
        "pass_count": 0,
        "you_passed": False,
        "last_message": message,
        "last_winner_id": None,
        "last_matched_name": "",
        "winner_ids": [],
        "you_are_host": False,
        "in_room": False,
        "can_start": False,
        "rematch_ready_count": 0,
        "you_ready_for_rematch": False,
    }


def leave_room(code: str, player_id: str) -> dict[str, Any]:
    """Remove a player from the lobby/match and sync for everyone else."""
    room_code = code.strip().upper()
    player_id = player_id.strip()
    if not player_id:
        raise MultiplayerError("Missing player id.")

    with _lock:
        _cleanup_expired_locked()
        room = _rooms.get(room_code)
        if room is None:
            raise MultiplayerError("Room not found.", 404)

        player = _find_player(room, player_id)
        if player is None:
            _sync_room_timers(room)
            return serialize_room(room, player_id)

        name = player.display_name

        # Leaving after the match ends closes the lobby for everyone.
        if room.status == "finished":
            del _rooms[room_code]
            return _closed_room_payload(room, f"{name} left. Room closed.")

        room.players = [entry for entry in room.players if entry.player_id != player_id]
        room.round_passes.discard(player_id)
        room.rematch_ready.discard(player_id)
        room.updated_at = time.time()

        if not room.players:
            del _rooms[room_code]
            return _closed_room_payload(room, f"{name} left. Room closed.")

        if room.host_id == player_id:
            room.host_id = room.players[0].player_id

        if room.status in {"playing", "countdown"} and len(room.players) < 2:
            room.countdown_started_at = None
            room.round_started_at = None
            _finish_match(room)
            room.last_message = f"{name} left. Match ended."
        else:
            room.last_message = f"{name} left ({len(room.players)}/{MAX_PLAYERS})."
            _sync_room_timers(room)

        return serialize_room(room, player_id)


def _finish_match(room: MultiplayerRoom) -> None:
    room.status = "finished"
    room.round_started_at = None
    room.round_passes.clear()
    room.rematch_ready.clear()
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

    _record_friendly_1v1_win(room, winners)


def _advance_round(room: MultiplayerRoom, message: str) -> None:
    room.round_index += 1
    room.last_winner_id = None
    room.last_matched_name = ""
    room.round_passes.clear()
    if room.round_index >= room.total_rounds:
        _finish_match(room)
    else:
        room.round_started_at = time.time()
        room.last_message = message


def _countdown_left(room: MultiplayerRoom) -> int | None:
    if room.status != "countdown" or room.countdown_started_at is None:
        return None
    elapsed = time.time() - room.countdown_started_at
    return max(0, int(COUNTDOWN_SECONDS - elapsed + 0.999))


def _maybe_begin_playing(room: MultiplayerRoom) -> bool:
    """Move from countdown into playing when the 3s ready timer ends."""
    if room.status != "countdown" or room.countdown_started_at is None:
        return False
    if time.time() - room.countdown_started_at < COUNTDOWN_SECONDS:
        return False

    room.status = "playing"
    room.countdown_started_at = None
    room.round_started_at = time.time()
    room.round_passes.clear()
    room.last_message = f"Round 1 of {room.total_rounds} ({era_label(room.era)}) — go!"
    room.updated_at = time.time()
    return True


def _sync_room_timers(room: MultiplayerRoom) -> None:
    _maybe_begin_playing(room)
    _maybe_expire_round(room)


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
        room.round_passes.clear()
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
    you_passed = bool(viewer_id and viewer_id in room.round_passes)

    winner_ids: list[str] = []
    if room.status == "finished" and room.players:
        top = max(player.score for player in room.players)
        winner_ids = [player.player_id for player in room.players if player.score == top]

    return {
        "code": room.code,
        "status": room.status,
        "max_players": MAX_PLAYERS,
        "total_rounds": room.total_rounds,
        "era": room.era,
        "era_label": era_label(room.era),
        "is_public": room.is_public,
        "round_seconds": ROUND_SECONDS,
        "countdown_seconds": COUNTDOWN_SECONDS,
        "round_index": room.round_index,
        "round_number": min(room.round_index + 1, room.total_rounds),
        "time_left": _time_left(room),
        "countdown_left": _countdown_left(room),
        "current_initials": initials,
        "initials_player_count": count_players_for_initials_era(
            initials,
            room.era,
            used_player_ids=room.used_player_ids,
        )
        if initials
        else 0,
        "players": [
            {
                "player_id": player.player_id,
                "display_name": player.display_name,
                "score": player.score,
                "is_host": player.player_id == room.host_id,
                "is_you": viewer_id == player.player_id,
                "has_passed": player.player_id in room.round_passes,
                "ready_for_rematch": player.player_id in room.rematch_ready,
                "avatar_url": player.avatar_url,
            }
            for player in room.players
        ],
        "pass_count": len(room.round_passes),
        "you_passed": you_passed,
        "last_message": room.last_message,
        "last_winner_id": room.last_winner_id,
        "last_matched_name": room.last_matched_name,
        "winner_ids": winner_ids,
        "you_are_host": you_are_host,
        "in_room": in_room,
        "can_start": you_are_host and room.status == "waiting" and len(room.players) >= 2,
        "rematch_ready_count": len(room.rematch_ready),
        "you_ready_for_rematch": bool(viewer_id and viewer_id in room.rematch_ready),
    }


def create_room(
    player_id: str,
    display_name: str,
    total_rounds: int | None = None,
    era: str | None = None,
    avatar_url: str | None = None,
    is_public: bool = False,
) -> dict[str, Any]:
    name = display_name.strip()[:40] or "Player 1"
    player_id = player_id.strip()
    if not player_id:
        raise MultiplayerError("Missing player id.")

    rounds = _normalize_rounds(total_rounds)
    resolved_era = normalize_era(era)
    sequence = _build_sequence(rounds, resolved_era)

    with _lock:
        _cleanup_expired_locked()
        code = _new_code()
        host = RoomPlayer(
            player_id=player_id,
            display_name=name,
            avatar_url=avatar_url,
        )
        visibility = "Public lobby open" if is_public else "Share this code. Waiting for players"
        room = MultiplayerRoom(
            code=code,
            host_id=player_id,
            players=[host],
            total_rounds=rounds,
            era=resolved_era,
            sequence=sequence,
            is_public=bool(is_public),
            last_message=f"{visibility} ({rounds} rounds · {era_label(resolved_era)}).",
        )
        _rooms[code] = room
        return serialize_room(room, player_id)


def list_public_lobbies() -> list[dict[str, Any]]:
    """Return open public waiting rooms with free seats."""
    with _lock:
        _cleanup_expired_locked()
        lobbies: list[dict[str, Any]] = []
        for room in _rooms.values():
            if not room.is_public or room.status != "waiting":
                continue
            if len(room.players) >= MAX_PLAYERS:
                continue
            host = next((p for p in room.players if p.player_id == room.host_id), room.players[0])
            lobbies.append(
                {
                    "code": room.code,
                    "host_name": host.display_name if host else "Host",
                    "player_count": len(room.players),
                    "max_players": MAX_PLAYERS,
                    "total_rounds": room.total_rounds,
                    "era": room.era,
                    "era_label": era_label(room.era),
                    "updated_at": room.updated_at,
                }
            )
        lobbies.sort(key=lambda item: item["updated_at"], reverse=True)
        return lobbies


def join_room(
    code: str,
    player_id: str,
    display_name: str,
    avatar_url: str | None = None,
) -> dict[str, Any]:
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
            existing.display_name = name
            if avatar_url:
                existing.avatar_url = avatar_url
            _sync_room_timers(room)
            room.updated_at = time.time()
            return serialize_room(room, player_id)

        if room.status != "waiting":
            raise MultiplayerError("This match already started.")

        if len(room.players) >= MAX_PLAYERS:
            raise MultiplayerError("This room is full (max 4 players).")

        room.players.append(
            RoomPlayer(player_id=player_id, display_name=name, avatar_url=avatar_url)
        )
        room.last_message = f"{name} joined ({len(room.players)}/{MAX_PLAYERS})."
        room.updated_at = time.time()
        return serialize_room(room, player_id)


def set_settings(
    code: str,
    player_id: str,
    total_rounds: int | None = None,
    era: str | None = None,
) -> dict[str, Any]:
    room_code = code.strip().upper()
    player_id = player_id.strip()

    with _lock:
        room = _rooms.get(room_code)
        if room is None:
            raise MultiplayerError("Room not found.", 404)
        if player_id != room.host_id:
            raise MultiplayerError("Only the host can change lobby settings.", 403)
        if room.status != "waiting":
            raise MultiplayerError("Settings can only be changed before the match starts.")

        if total_rounds is not None:
            room.total_rounds = _normalize_rounds(total_rounds)
        if era is not None:
            room.era = normalize_era(era)

        room.sequence = _build_sequence(room.total_rounds, room.era)
        room.last_message = (
            f"Host set {room.total_rounds} rounds · {era_label(room.era)}."
        )
        room.updated_at = time.time()
        return serialize_room(room, player_id)


def set_rounds(code: str, player_id: str, total_rounds: int) -> dict[str, Any]:
    return set_settings(code, player_id, total_rounds=total_rounds)


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
        room.status = "countdown"
        room.round_index = 0
        room.used_player_ids = []
        room.round_passes.clear()
        room.last_winner_id = None
        room.last_matched_name = ""
        room.round_started_at = None
        room.countdown_started_at = time.time()
        room.friendly_win_recorded = False
        room.rematch_ready.clear()
        room.last_message = "Get ready..."
        room.updated_at = time.time()
        return serialize_room(room, player_id)


def rematch(code: str, player_id: str) -> dict[str, Any]:
    """Any player can ready up; rematch starts only when every seated player opts in."""
    room_code = code.strip().upper()
    player_id = player_id.strip()

    with _lock:
        room = _rooms.get(room_code)
        if room is None:
            raise MultiplayerError("Room not found.", 404)
        if room.status != "finished":
            raise MultiplayerError("Rematch is only available after the match ends.")

        player = _find_player(room, player_id)
        if player is None:
            raise MultiplayerError("You are not in this room.", 403)

        present_ids = {entry.player_id for entry in room.players}
        if len(present_ids) < 2:
            raise MultiplayerError("Need at least 2 players to rematch.")

        # Drop ready flags for anyone who already left, then mark this player.
        room.rematch_ready.intersection_update(present_ids)
        room.rematch_ready.add(player_id)
        room.updated_at = time.time()

        ready_count = len(room.rematch_ready)
        needed = len(present_ids)

        # Start only when the ready set exactly matches every current player.
        if room.rematch_ready != present_ids:
            room.last_message = (
                f"{player.display_name} wants a rematch ({ready_count}/{needed})."
            )
            return serialize_room(room, player_id)

        room.sequence = _build_sequence(room.total_rounds, room.era)
        for entry in room.players:
            entry.score = 0
        room.status = "countdown"
        room.round_index = 0
        room.used_player_ids = []
        room.round_passes.clear()
        room.rematch_ready.clear()
        room.last_winner_id = None
        room.last_matched_name = ""
        room.round_started_at = None
        room.countdown_started_at = time.time()
        room.friendly_win_recorded = False
        room.last_message = "Rematch! Everyone is ready. Get ready..."
        return serialize_room(room, player_id)


def get_room(code: str, viewer_id: str | None = None) -> dict[str, Any]:
    room_code = code.strip().upper()
    with _lock:
        _cleanup_expired_locked()
        room = _rooms.get(room_code)
        if room is None:
            raise MultiplayerError("Room not found.", 404)
        _sync_room_timers(room)
        room.updated_at = time.time()
        return serialize_room(room, viewer_id)


def submit_pass(code: str, player_id: str) -> dict[str, Any]:
    room_code = code.strip().upper()
    player_id = player_id.strip()
    if not player_id:
        raise MultiplayerError("Missing player id.")

    with _lock:
        room = _rooms.get(room_code)
        if room is None:
            raise MultiplayerError("Room not found.", 404)

        _sync_room_timers(room)

        if room.status != "playing":
            raise MultiplayerError("Match is not in progress.")

        player = _find_player(room, player_id)
        if player is None:
            raise MultiplayerError("You are not in this room.", 403)

        room.round_passes.add(player_id)
        passed = len(room.round_passes)
        needed = len(room.players)
        room.updated_at = time.time()

        if passed >= needed:
            timed_out_initials = _current_initials(room)
            if room.round_index + 1 >= room.total_rounds:
                room.round_index += 1
                room.last_winner_id = None
                room.last_matched_name = ""
                room.round_passes.clear()
                _finish_match(room)
                room.last_message = f"Everyone passed on {timed_out_initials}. {room.last_message}"
            else:
                next_round = room.round_index + 2
                _advance_round(
                    room,
                    f"Everyone passed on {timed_out_initials}. Round {next_round} — go!",
                )
        else:
            room.last_message = f"{player.display_name} passed ({passed}/{needed})."

        return serialize_room(room, player_id)


def submit_guess(code: str, player_id: str, guess: str) -> dict[str, Any]:
    room_code = code.strip().upper()
    player_id = player_id.strip()
    if not player_id:
        raise MultiplayerError("Missing player id.")

    with _lock:
        room = _rooms.get(room_code)
        if room is None:
            raise MultiplayerError("Room not found.", 404)

        _sync_room_timers(room)

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
            era=room.era,
        )

        if not result.correct:
            # Keep incorrect feedback private to the guesser (do not broadcast via last_message).
            room.updated_at = time.time()
            payload = serialize_room(room, player_id)
            payload["accepted"] = False
            payload["your_feedback"] = result.reason or "Incorrect. Keep trying!"
            return payload

        player.score += 1
        room.used_player_ids.append(result.matched_nba_id)
        room.last_winner_id = player_id
        room.last_matched_name = result.matched_name
        room.round_passes.clear()

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
