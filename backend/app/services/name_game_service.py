"""NBA initials name-guessing game logic."""

from __future__ import annotations

import json
import random
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from app.config import settings
from app.services.seed_service import NBA_TEAMS, fetch_roster_data

ALL_TIME_PLAYERS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "all_time_players.json"

VALID_PLAYER_MODES = frozenset({"current", "all_time"})

_players_cache: dict[str, list["GamePlayer"]] = {}
_initials_index: dict[str, dict[str, list["GamePlayer"]]] = {}
_active_mode: str = settings.player_pool_mode

# Minimum similarity (0–1) to accept a close spelling
FUZZY_MATCH_THRESHOLD = 0.8


@dataclass(frozen=True)
class GamePlayer:
    nba_id: int
    first_name: str
    last_name: str
    full_name: str
    initials: str
    team_abbrev: str
    from_season: str = ""
    to_season: str = ""
    from_year: int = 0
    to_year: int = 0


@dataclass(frozen=True)
class GuessResult:
    correct: bool
    game_over: bool
    points: int = 0
    reason: str = ""
    matched_name: str = ""
    matched_nba_id: int = 0
    next_initials: str = ""
    next_initials_player_count: int = 0
    matching_players: tuple[str, ...] = ()


def _normalize_mode(mode: str | None) -> str:
    candidate = (mode or settings.player_pool_mode or "all_time").strip().lower()
    if candidate not in VALID_PLAYER_MODES:
        return settings.player_pool_mode if settings.player_pool_mode in VALID_PLAYER_MODES else "all_time"
    return candidate


def _normalize_text(value: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9\s]", "", ascii_text.lower()).strip()


def _initial_letter(name: str) -> str:
    for char in name:
        if char.isalpha():
            return char.upper()
    return "?"


NAME_SUFFIXES = frozenset({"jr", "sr", "ii", "iii", "iv", "v", "2nd", "3rd"})


def _name_parts(full_name: str) -> list[str]:
    return [part for part in full_name.split() if part.strip()]


def _strip_name_suffixes(parts: list[str]) -> list[str]:
    trimmed = parts[:]
    while len(trimmed) > 1:
        last = trimmed[-1].lower().rstrip(".")
        if last in NAME_SUFFIXES:
            trimmed.pop()
        else:
            break
    return trimmed


def _initials_from_display_name(full_name: str) -> str:
    """Derive initials from the public display name (e.g. Yao Ming -> YM)."""
    parts = _strip_name_suffixes(_name_parts(full_name))
    if len(parts) >= 2:
        return f"{_initial_letter(parts[0])}{_initial_letter(parts[-1])}"
    if len(parts) == 1:
        letter = _initial_letter(parts[0])
        return f"{letter}{letter}" if letter != "?" else "??"
    return "??"


def _season_label(from_year: int) -> str:
    return f"{from_year}-{str(from_year + 1)[-2:]}"


def _career_seasons(pdata: dict) -> tuple[str, str]:
    from_season = str(pdata.get("from_season") or "").strip()
    to_season = str(pdata.get("to_season") or "").strip()
    if from_season and to_season:
        return from_season, to_season
    from_year = pdata.get("from_year")
    to_year = pdata.get("to_year")
    if isinstance(from_year, int) and isinstance(to_year, int):
        return _season_label(from_year), _season_label(to_year)
    return "", ""


def _career_years(pdata: dict, from_season: str, to_season: str) -> tuple[int, int]:
    from_year = pdata.get("from_year")
    to_year = pdata.get("to_year")
    if isinstance(from_year, int) and isinstance(to_year, int):
        return from_year, to_year
    try:
        start = int(from_season.split("-", 1)[0]) if from_season else 0
    except ValueError:
        start = 0
    try:
        end = int(to_season.split("-", 1)[0]) if to_season else start
    except ValueError:
        end = start
    return start, end


ERA_RANGES: dict[str, tuple[int, int]] = {
    "all_time": (1946, 2100),
    "60s": (1960, 1969),
    "70s": (1970, 1979),
    "80s": (1980, 1989),
    "90s": (1990, 1999),
    "2000s": (2000, 2009),
    "2010s": (2010, 2019),
    "2020s": (2020, 2029),
}

ERA_LABELS: dict[str, str] = {
    "all_time": "All-time",
    "60s": "1960s",
    "70s": "1970s",
    "80s": "1980s",
    "90s": "1990s",
    "2000s": "2000s",
    "2010s": "2010s",
    "2020s": "2020s",
}

VALID_ERAS = frozenset(ERA_RANGES.keys())


def normalize_era(era: str | None) -> str:
    key = (era or "all_time").strip().lower()
    if key in {"all", "alltime", "all-time"}:
        return "all_time"
    if key not in VALID_ERAS:
        return "all_time"
    return key


def era_label(era: str | None) -> str:
    return ERA_LABELS.get(normalize_era(era), "All-time")


def _player_in_era(player: GamePlayer, era: str) -> bool:
    resolved = normalize_era(era)
    if resolved == "all_time":
        return True
    start, end = ERA_RANGES[resolved]
    # Career overlaps the decade.
    return player.from_year <= end and player.to_year >= start


def _players_for_era(era: str | None = None, mode: str | None = None) -> list[GamePlayer]:
    resolved_mode = _ensure_cache(mode)
    players = _players_cache.get(resolved_mode) or []
    resolved_era = normalize_era(era)
    if resolved_era == "all_time":
        return players
    return [player for player in players if _player_in_era(player, resolved_era)]


def _initials_index_for_players(players: list[GamePlayer]) -> dict[str, list[GamePlayer]]:
    index: dict[str, list[GamePlayer]] = {}
    for player in players:
        index.setdefault(player.initials, []).append(player)
    return index


def format_career_span(from_season: str, to_season: str) -> str:
    if not from_season:
        return "Unknown"
    if not to_season or from_season == to_season:
        return from_season
    return f"{from_season} – {to_season}"


def _player_reveal_entry(player: GamePlayer) -> dict[str, str]:
    return {
        "full_name": player.full_name,
        "from_season": player.from_season,
        "to_season": player.to_season,
        "career_span": format_career_span(player.from_season, player.to_season),
    }


def _compute_speed_points(time_remaining: int) -> int:
    """Faster answers (more time left) earn more points."""
    timer = settings.game_timer_seconds
    clamped = max(0, min(time_remaining, timer))
    if clamped <= 0:
        return 1
    return max(1, clamped)


def _load_all_time_records() -> list[dict]:
    if not ALL_TIME_PLAYERS_PATH.exists():
        return []
    try:
        payload = json.loads(ALL_TIME_PLAYERS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def _build_current_player_pool() -> list[GamePlayer]:
    roster, _source = fetch_roster_data()
    abbrev_by_team = {team["nba_id"]: team["abbreviation"] for team in NBA_TEAMS}

    players: list[GamePlayer] = []
    for pdata in roster:
        first = str(pdata.get("first_name", "")).strip()
        last = str(pdata.get("last_name", "")).strip()
        if not first or not last:
            continue
        full_name = f"{first} {last}"
        team_abbrev = abbrev_by_team.get(int(pdata["team_nba_id"]), "NBA")
        players.append(
            GamePlayer(
                nba_id=int(pdata["nba_id"]),
                first_name=first,
                last_name=last,
                full_name=full_name,
                initials=_initials_from_display_name(full_name),
                team_abbrev=team_abbrev,
            )
        )
    return players


def _build_all_time_player_pool() -> list[GamePlayer]:
    records = _load_all_time_records()
    if not records:
        return []

    players: list[GamePlayer] = []
    for pdata in records:
        first = str(pdata.get("first_name", "")).strip()
        last = str(pdata.get("last_name", "")).strip()
        if not first or not last:
            continue
        full_name = str(pdata.get("full_name") or f"{first} {last}").strip()
        from_season, to_season = _career_seasons(pdata)
        from_year, to_year = _career_years(pdata, from_season, to_season)
        players.append(
            GamePlayer(
                nba_id=int(pdata["nba_id"]),
                first_name=first,
                last_name=last,
                full_name=full_name,
                initials=_initials_from_display_name(full_name),
                team_abbrev="NBA",
                from_season=from_season,
                to_season=to_season,
                from_year=from_year,
                to_year=to_year,
            )
        )
    return players


def _build_player_pool(mode: str) -> list[GamePlayer]:
    if mode == "current":
        return _build_current_player_pool()
    return _build_all_time_player_pool()


def _ensure_cache(mode: str | None = None) -> str:
    global _active_mode
    resolved_mode = _normalize_mode(mode)
    _active_mode = resolved_mode

    if resolved_mode in _players_cache and resolved_mode in _initials_index:
        return resolved_mode

    players = _build_player_pool(resolved_mode)
    index: dict[str, list[GamePlayer]] = {}
    for player in players:
        index.setdefault(player.initials, []).append(player)

    _players_cache[resolved_mode] = players
    _initials_index[resolved_mode] = index
    return resolved_mode


def refresh_player_pool(mode: str | None = None) -> int:
    resolved_mode = _normalize_mode(mode)
    _players_cache.pop(resolved_mode, None)
    _initials_index.pop(resolved_mode, None)
    _ensure_cache(resolved_mode)
    return len(_players_cache.get(resolved_mode) or [])


def _mode_label(mode: str) -> str:
    if mode == "current":
        return f"{settings.current_season} rosters"
    return "All-time NBA"


def _invalid_player_message(mode: str) -> str:
    if mode == "current":
        return "That player is not on a current NBA roster."
    return "That is not a valid NBA player."


def get_game_status(mode: str | None = None) -> dict[str, str | int]:
    resolved_mode = _ensure_cache(mode)
    players = _players_cache.get(resolved_mode) or []
    return {
        "mode": resolved_mode,
        "mode_label": _mode_label(resolved_mode),
        "season": settings.current_season,
        "player_count": len(players),
        "timer_seconds": settings.game_timer_seconds,
    }


def random_initials(used_player_ids: set[int] | None = None, mode: str | None = None) -> str:
    resolved_mode = _ensure_cache(mode)
    players = _players_cache.get(resolved_mode) or []
    used = used_player_ids or set()
    available = [player for player in players if player.nba_id not in used]
    pool = available or players
    return random.choice(pool).initials


def count_players_for_initials(initials: str, mode: str | None = None) -> int:
    resolved_mode = _ensure_cache(mode)
    initials_map = _initials_index.get(resolved_mode) or {}
    return len(initials_map.get(initials.strip().upper(), []))


def get_players_for_initials(initials: str, mode: str | None = None) -> list[GamePlayer]:
    resolved_mode = _ensure_cache(mode)
    initials_map = _initials_index.get(resolved_mode) or {}
    players = initials_map.get(initials.strip().upper(), [])
    return sorted(players, key=lambda player: (player.from_season or "9999", player.full_name))


def get_player_names_for_initials(initials: str, mode: str | None = None) -> list[str]:
    return [player.full_name for player in get_players_for_initials(initials, mode)]


def get_reveals_for_initials(initials_list: list[str], mode: str | None = None) -> list[dict[str, str | int | list[dict[str, str]]]]:
    seen: set[str] = set()
    reveals: list[dict[str, str | int | list[dict[str, str]]]] = []
    for raw in initials_list:
        key = raw.strip().upper()
        if not key or key in seen:
            continue
        seen.add(key)
        players = [_player_reveal_entry(player) for player in get_players_for_initials(key, mode)]
        reveals.append(
            {
                "initials": key,
                "players": players,
                "player_count": len(players),
            }
        )
    return reveals


def start_round(used_player_ids: list[int] | None = None, mode: str | None = None) -> dict[str, str | int]:
    resolved_mode = _ensure_cache(mode)
    used = set(used_player_ids or [])
    initials = random_initials(used, resolved_mode)
    return {
        "initials": initials,
        "initials_player_count": count_players_for_initials(initials, resolved_mode),
        "season": settings.current_season,
        "mode": resolved_mode,
    }


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def _player_name_variants(player: GamePlayer) -> list[str]:
    first = _normalize_text(player.first_name)
    last = _normalize_text(player.last_name)
    full = _normalize_text(player.full_name)
    stripped_parts = _strip_name_suffixes(_name_parts(player.full_name))
    without_suffix = _normalize_text(" ".join(stripped_parts))
    return [full, without_suffix, f"{first} {last}", f"{last} {first}", last, first]


def _fuzzy_match_player(guess: str, candidates: list[GamePlayer]) -> tuple[GamePlayer | None, float]:
    normalized = _normalize_text(guess)
    if not normalized or not candidates:
        return None, 0.0

    best_player: GamePlayer | None = None
    best_score = 0.0
    parts = normalized.split()

    for player in candidates:
        for variant in _player_name_variants(player):
            score = _similarity(normalized, variant)
            if score > best_score:
                best_score = score
                best_player = player

        if len(parts) >= 2:
            first_score = _similarity(parts[0], _normalize_text(player.first_name))
            last_score = _similarity(parts[-1], _normalize_text(player.last_name))
            combined = (first_score + last_score) / 2
            if combined > best_score:
                best_score = combined
                best_player = player

    return best_player, best_score


def generate_initials_sequence(
    length: int = 10,
    mode: str | None = None,
    era: str | None = None,
) -> list[str]:
    """Pre-generate a shared initials sequence for multiplayer matches."""
    players = _players_for_era(era, mode)
    if not players:
        raise ValueError(f"No players available for era '{normalize_era(era)}'.")
    initials_map = _initials_index_for_players(players)
    sequence: list[str] = []
    used: set[int] = set()
    for _ in range(max(1, length)):
        available = [player for player in players if player.nba_id not in used]
        pool = available or players
        initials = random.choice(pool).initials
        sequence.append(initials)
        candidates = [
            player for player in initials_map.get(initials, []) if player.nba_id not in used
        ]
        if candidates:
            used.add(random.choice(candidates).nba_id)
    return sequence


def count_players_for_initials_era(
    initials: str,
    era: str | None = None,
    mode: str | None = None,
    used_player_ids: list[int] | None = None,
) -> int:
    used = set(used_player_ids or [])
    initials_map = _initials_index_for_players(_players_for_era(era, mode))
    return len(
        [
            player
            for player in initials_map.get(initials.strip().upper(), [])
            if player.nba_id not in used
        ]
    )


def match_guess_for_initials(
    initials: str,
    guess: str,
    used_player_ids: list[int] | None = None,
    mode: str | None = None,
    era: str | None = None,
) -> GuessResult:
    """Validate a guess without advancing initials or ending the match on a miss."""
    players = _players_for_era(era, mode)
    initials_map = _initials_index_for_players(players)

    used = set(used_player_ids or [])
    target_initials = initials.strip().upper()
    normalized = _normalize_text(guess)

    if not normalized:
        return GuessResult(correct=False, game_over=False, reason="Enter a player name.")

    candidates = [player for player in initials_map.get(target_initials, []) if player.nba_id not in used]
    player, score = _fuzzy_match_player(guess, candidates)

    if player and score >= FUZZY_MATCH_THRESHOLD:
        reason = (
            "Correct!"
            if score >= 0.99
            else f"Close enough — counted as {player.full_name}."
        )
        return GuessResult(
            correct=True,
            game_over=False,
            matched_name=player.full_name,
            matched_nba_id=player.nba_id,
            reason=reason,
        )

    pool_player, pool_score = _fuzzy_match_player(guess, players)
    if pool_player and pool_score >= FUZZY_MATCH_THRESHOLD:
        if pool_player.initials != target_initials:
            return GuessResult(
                correct=False,
                game_over=False,
                reason=f"{pool_player.full_name} does not match {target_initials}.",
            )
        if pool_player.nba_id in used:
            return GuessResult(
                correct=False,
                game_over=False,
                reason=f"{pool_player.full_name} was already used this match — pick another.",
            )

    # Also catch already-used answers that fuzzy-matched outside unused candidates.
    used_candidates = [player for player in initials_map.get(target_initials, []) if player.nba_id in used]
    used_player, used_score = _fuzzy_match_player(guess, used_candidates)
    if used_player and used_score >= FUZZY_MATCH_THRESHOLD:
        return GuessResult(
            correct=False,
            game_over=False,
            reason=f"{used_player.full_name} was already used this match — pick another.",
        )

    return GuessResult(
        correct=False,
        game_over=False,
        reason=_invalid_player_message(_ensure_cache(mode)),
    )


def validate_guess(
    initials: str,
    guess: str,
    used_player_ids: list[int] | None = None,
    mode: str | None = None,
    time_remaining: int | None = None,
) -> GuessResult:
    resolved_mode = _ensure_cache(mode)
    players = _players_cache.get(resolved_mode) or []
    initials_map = _initials_index.get(resolved_mode) or {}

    used = set(used_player_ids or [])
    target_initials = initials.strip().upper()
    normalized = _normalize_text(guess)

    if not normalized:
        return GuessResult(
            correct=False,
            game_over=True,
            reason="Enter a player name.",
            matching_players=tuple(get_player_names_for_initials(target_initials, resolved_mode)),
        )

    candidates = [player for player in initials_map.get(target_initials, []) if player.nba_id not in used]
    player, score = _fuzzy_match_player(guess, candidates)

    if player and score >= FUZZY_MATCH_THRESHOLD:
        used.add(player.nba_id)
        points = _compute_speed_points(time_remaining if time_remaining is not None else 0)
        reason = (
            "Correct!"
            if score >= 0.99
            else f"Close enough — counted as {player.full_name}."
        )
        next_initials = random_initials(used, resolved_mode)
        return GuessResult(
            correct=True,
            game_over=False,
            points=points,
            matched_name=player.full_name,
            matched_nba_id=player.nba_id,
            next_initials=next_initials,
            next_initials_player_count=count_players_for_initials(next_initials, resolved_mode),
            reason=reason,
        )

    pool_player, pool_score = _fuzzy_match_player(guess, players)
    matching = tuple(get_player_names_for_initials(target_initials, resolved_mode))
    if pool_player and pool_score >= FUZZY_MATCH_THRESHOLD:
        if pool_player.initials != target_initials:
            return GuessResult(
                correct=False,
                game_over=True,
                reason=f"{pool_player.full_name} does not match {target_initials}.",
                matching_players=matching,
            )
        if pool_player.nba_id in used:
            return GuessResult(
                correct=False,
                game_over=True,
                reason=f"You already named {pool_player.full_name} this round.",
                matching_players=matching,
            )

    return GuessResult(
        correct=False,
        game_over=True,
        reason=_invalid_player_message(resolved_mode),
        matching_players=matching,
    )
