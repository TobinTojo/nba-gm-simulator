"""Seed and bootstrap NBA data for the simulator."""

from __future__ import annotations

import json
import logging
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.models import CareerSave, Contract, DraftPick, Player, Team

logger = logging.getLogger(__name__)

NBA_STATS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.nba.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.nba.com",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
}

# NBA team metadata (30 franchises)
NBA_TEAMS: list[dict[str, Any]] = [
    {"nba_id": 1610612737, "name": "Hawks", "abbreviation": "ATL", "city": "Atlanta", "conference": "East", "division": "Southeast"},
    {"nba_id": 1610612738, "name": "Celtics", "abbreviation": "BOS", "city": "Boston", "conference": "East", "division": "Atlantic"},
    {"nba_id": 1610612751, "name": "Nets", "abbreviation": "BKN", "city": "Brooklyn", "conference": "East", "division": "Atlantic"},
    {"nba_id": 1610612766, "name": "Hornets", "abbreviation": "CHA", "city": "Charlotte", "conference": "East", "division": "Southeast"},
    {"nba_id": 1610612741, "name": "Bulls", "abbreviation": "CHI", "city": "Chicago", "conference": "East", "division": "Central"},
    {"nba_id": 1610612739, "name": "Cavaliers", "abbreviation": "CLE", "city": "Cleveland", "conference": "East", "division": "Central"},
    {"nba_id": 1610612742, "name": "Mavericks", "abbreviation": "DAL", "city": "Dallas", "conference": "West", "division": "Southwest"},
    {"nba_id": 1610612743, "name": "Nuggets", "abbreviation": "DEN", "city": "Denver", "conference": "West", "division": "Northwest"},
    {"nba_id": 1610612765, "name": "Pistons", "abbreviation": "DET", "city": "Detroit", "conference": "East", "division": "Central"},
    {"nba_id": 1610612744, "name": "Warriors", "abbreviation": "GSW", "city": "Golden State", "conference": "West", "division": "Pacific"},
    {"nba_id": 1610612745, "name": "Rockets", "abbreviation": "HOU", "city": "Houston", "conference": "West", "division": "Southwest"},
    {"nba_id": 1610612754, "name": "Pacers", "abbreviation": "IND", "city": "Indiana", "conference": "East", "division": "Central"},
    {"nba_id": 1610612746, "name": "Clippers", "abbreviation": "LAC", "city": "LA", "conference": "West", "division": "Pacific"},
    {"nba_id": 1610612747, "name": "Lakers", "abbreviation": "LAL", "city": "Los Angeles", "conference": "West", "division": "Pacific"},
    {"nba_id": 1610612763, "name": "Grizzlies", "abbreviation": "MEM", "city": "Memphis", "conference": "West", "division": "Southwest"},
    {"nba_id": 1610612748, "name": "Heat", "abbreviation": "MIA", "city": "Miami", "conference": "East", "division": "Southeast"},
    {"nba_id": 1610612749, "name": "Bucks", "abbreviation": "MIL", "city": "Milwaukee", "conference": "East", "division": "Central"},
    {"nba_id": 1610612750, "name": "Timberwolves", "abbreviation": "MIN", "city": "Minnesota", "conference": "West", "division": "Northwest"},
    {"nba_id": 1610612740, "name": "Pelicans", "abbreviation": "NOP", "city": "New Orleans", "conference": "West", "division": "Southwest"},
    {"nba_id": 1610612752, "name": "Knicks", "abbreviation": "NYK", "city": "New York", "conference": "East", "division": "Atlantic"},
    {"nba_id": 1610612760, "name": "Thunder", "abbreviation": "OKC", "city": "Oklahoma City", "conference": "West", "division": "Northwest"},
    {"nba_id": 1610612753, "name": "Magic", "abbreviation": "ORL", "city": "Orlando", "conference": "East", "division": "Southeast"},
    {"nba_id": 1610612755, "name": "76ers", "abbreviation": "PHI", "city": "Philadelphia", "conference": "East", "division": "Atlantic"},
    {"nba_id": 1610612756, "name": "Suns", "abbreviation": "PHX", "city": "Phoenix", "conference": "West", "division": "Pacific"},
    {"nba_id": 1610612757, "name": "Trail Blazers", "abbreviation": "POR", "city": "Portland", "conference": "West", "division": "Northwest"},
    {"nba_id": 1610612758, "name": "Kings", "abbreviation": "SAC", "city": "Sacramento", "conference": "West", "division": "Pacific"},
    {"nba_id": 1610612759, "name": "Spurs", "abbreviation": "SAS", "city": "San Antonio", "conference": "West", "division": "Southwest"},
    {"nba_id": 1610612761, "name": "Raptors", "abbreviation": "TOR", "city": "Toronto", "conference": "East", "division": "Atlantic"},
    {"nba_id": 1610612762, "name": "Jazz", "abbreviation": "UTA", "city": "Utah", "conference": "West", "division": "Northwest"},
    {"nba_id": 1610612764, "name": "Wizards", "abbreviation": "WAS", "city": "Washington", "conference": "East", "division": "Southeast"},
]

TEAM_PROFILES: dict[str, dict[str, Any]] = {
    "DET": {"difficulty": 4, "young_core": "A", "cap_space": 18.0, "window": "2-4 Years", "draft_assets": 72},
    "BOS": {"difficulty": 2, "young_core": "B+", "cap_space": -5.0, "window": "Now", "draft_assets": 45},
    "LAL": {"difficulty": 3, "young_core": "B", "cap_space": 8.0, "window": "1-2 Years", "draft_assets": 38},
    "OKC": {"difficulty": 2, "young_core": "A+", "cap_space": 12.0, "window": "Now", "draft_assets": 85},
    "GSW": {"difficulty": 3, "young_core": "B-", "cap_space": -22.0, "window": "1-2 Years", "draft_assets": 40},
    "CHA": {"difficulty": 4, "young_core": "A-", "cap_space": 25.0, "window": "3-5 Years", "draft_assets": 68},
}


def _parse_player_name(player_name: str) -> tuple[str, str]:
    if ", " in player_name:
        last_name, first_name = player_name.split(", ", 1)
        return first_name.strip(), last_name.strip()
    parts = player_name.split()
    if not parts:
        return "Unknown", "Player"
    suffixes = {"JR", "JR.", "SR", "SR.", "II", "III", "IV", "V"}
    if len(parts) >= 3 and parts[-1].upper().rstrip(".") in {s.rstrip(".") for s in suffixes}:
        return " ".join(parts[:-2]), f"{parts[-2]} {parts[-1]}"
    if len(parts) >= 2:
        return " ".join(parts[:-1]), parts[-1]
    return parts[0], "Player"


def _fetch_rosters_from_stats_api() -> list[dict[str, Any]] | None:
    """Load current rosters from stats.nba.com without pandas/nba_api."""
    all_players: list[dict[str, Any]] = []

    for team_info in NBA_TEAMS:
        nba_id = team_info["nba_id"]
        params = urllib.parse.urlencode({"TeamID": nba_id, "Season": settings.current_season})
        url = f"https://stats.nba.com/stats/commonteamroster?{params}"
        try:
            request = urllib.request.Request(url, headers=NBA_STATS_HEADERS)
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode())

            result = payload["resultSets"][0]
            columns = {name: index for index, name in enumerate(result["headers"])}
            for row in result["rowSet"]:
                first_name, last_name = _parse_player_name(str(row[columns["PLAYER"]]))
                pos_idx = columns.get("POSITION", columns.get("POS"))
                position = _normalize_position(str(row[pos_idx] if pos_idx is not None else "SF"))
                age_idx = columns.get("AGE")
                height_idx = columns.get("HEIGHT")
                weight_idx = columns.get("WEIGHT")
                all_players.append(
                    {
                        "nba_id": int(row[columns["PLAYER_ID"]]),
                        "team_nba_id": nba_id,
                        "first_name": first_name,
                        "last_name": last_name,
                        "position": position,
                        "age": int(row[age_idx] if age_idx is not None else 25),
                        "height": str(row[height_idx] if height_idx is not None else "6-6"),
                        "weight": _parse_weight(row[weight_idx] if weight_idx is not None else 200),
                    }
                )
            time.sleep(0.6)
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Failed roster fetch for team %s: %s", nba_id, exc)
            continue

    if all_players:
        logger.info("Loaded %d players from stats.nba.com", len(all_players))
        return all_players
    return None


def _fetch_rosters_from_nba_api() -> list[dict[str, Any]] | None:
    """Attempt to load current rosters via nba_api."""
    try:
        from nba_api.stats.static import players as nba_players
        from nba_api.stats.static import teams as nba_teams
        from nba_api.stats.endpoints import commonteamroster

        team_map = {t["id"]: t for t in nba_teams.get_teams()}
        all_players: list[dict[str, Any]] = []
        player_lookup = {p["id"]: p for p in nba_players.get_players()}

        for team_info in NBA_TEAMS:
            nba_id = team_info["nba_id"]
            try:
                roster = commonteamroster.CommonTeamRoster(
                    team_id=nba_id,
                    season=settings.current_season,
                )
                df = roster.get_data_frames()[0]
                for _, row in df.iterrows():
                    pid = int(row["PLAYER_ID"])
                    pinfo = player_lookup.get(pid, {})
                    player_name = str(row.get("PLAYER", ""))
                    first_name, last_name = _parse_player_name(player_name)
                    if first_name == "Unknown":
                        pinfo = player_lookup.get(pid, {})
                        first_name = pinfo.get("first_name", "Unknown")
                        last_name = pinfo.get("last_name", "Player")
                    all_players.append(
                        {
                            "nba_id": pid,
                            "team_nba_id": nba_id,
                            "first_name": first_name,
                            "last_name": last_name,
                            "position": _normalize_position(str(row.get("POSITION", "SF"))),
                            "age": int(row.get("AGE", 25) or 25),
                            "height": str(row.get("HEIGHT", "6-6")),
                            "weight": _parse_weight(row.get("WEIGHT", 200)),
                        }
                    )
            except Exception as exc:
                logger.warning("Failed roster fetch for team %s: %s", nba_id, exc)
                continue

        if all_players:
            logger.info("Loaded %d players from nba_api", len(all_players))
            return all_players
    except Exception as exc:
        logger.warning("nba_api unavailable, using generated rosters: %s", exc)
    return None


BUNDLED_ROSTERS_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / f"rosters_{settings.current_season.replace('-', '_')}.json"
)


def _load_bundled_rosters() -> list[dict[str, Any]] | None:
    """Load shipped snapshot of real NBA rosters (works offline, no nba_api)."""
    if not BUNDLED_ROSTERS_PATH.exists():
        return None
    try:
        players = json.loads(BUNDLED_ROSTERS_PATH.read_text(encoding="utf-8"))
        if isinstance(players, list) and players:
            logger.info("Loaded %d players from bundled roster file", len(players))
            return players
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        logger.warning("Failed to read bundled rosters: %s", exc)
    return None


def fetch_roster_data() -> tuple[list[dict[str, Any]], str]:
    """Try roster sources in order; return players and source label."""
    sources: list[tuple[str, Callable[[], list[dict[str, Any]] | None]]] = [
        ("stats.nba.com (live)", _fetch_rosters_from_stats_api),
        (f"bundled {settings.current_season} snapshot", _load_bundled_rosters),
        ("nba_api", _fetch_rosters_from_nba_api),
    ]
    for label, loader in sources:
        try:
            players = loader()
            if players:
                return players, label
        except Exception as exc:
            logger.warning("Roster source %s failed: %s", label, exc)
            continue
    return _generate_fallback_rosters(), "random placeholders (no live data available)"


def _normalize_position(raw: str) -> str:
    """Map NBA roster position codes to PG/SG/SF/PF/C."""
    cleaned = raw.strip().upper().replace(" ", "")
    mapping = {
        "G": "PG",
        "F": "SF",
        "C": "C",
        "G-F": "SG",
        "F-G": "SG",
        "F-C": "PF",
        "C-F": "PF",
        "GF": "SG",
        "FC": "PF",
        "GUARD": "PG",
        "FORWARD": "SF",
        "CENTER": "C",
    }
    if cleaned in mapping:
        return mapping[cleaned]
    if cleaned in {"PG", "SG", "SF", "PF"}:
        return cleaned
    if cleaned.startswith("G"):
        return "SG"
    if cleaned.startswith("F"):
        return "PF"
    if cleaned.startswith("C"):
        return "C"
    return "SF"


def fetch_season_stats_map(season: str | None = None) -> dict[int, dict[str, float | int | str]]:
    """Fetch per-game stats for a season from stats.nba.com."""
    target_season = season or settings.current_season
    params = urllib.parse.urlencode(
        {
            "College": "",
            "Conference": "",
            "Country": "",
            "DateFrom": "",
            "DateTo": "",
            "Division": "",
            "DraftPick": "",
            "DraftYear": "",
            "GameScope": "",
            "GameSegment": "",
            "Height": "",
            "ISTRound": "",
            "ISTStanding": "",
            "LastNGames": "0",
            "LeagueID": "00",
            "Location": "",
            "MeasureType": "Base",
            "Month": "0",
            "OpponentTeamID": "0",
            "Outcome": "",
            "PORound": "0",
            "PaceAdjust": "N",
            "PerMode": "PerGame",
            "Period": "0",
            "PlayerExperience": "",
            "PlayerPosition": "",
            "PlusMinus": "N",
            "Rank": "N",
            "Season": target_season,
            "SeasonSegment": "",
            "SeasonType": "Regular Season",
            "ShotClockRange": "",
            "StarterBench": "",
            "TeamID": "0",
            "TwoWay": "0",
            "VsConference": "",
            "VsDivision": "",
            "Weight": "",
        }
    )
    url = f"https://stats.nba.com/stats/leaguedashplayerstats?{params}"
    try:
        request = urllib.request.Request(url, headers=NBA_STATS_HEADERS)
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode())
        result = payload["resultSets"][0]
        columns = {name: index for index, name in enumerate(result["headers"])}
        stats_map: dict[int, dict[str, float | int | str]] = {}
        for row in result["rowSet"]:
            player_id = int(row[columns["PLAYER_ID"]])
            fg_pct = float(row[columns["FG_PCT"]] or 0)
            fg3_pct = float(row[columns["FG3_PCT"]] or 0)
            ft_pct = float(row[columns["FT_PCT"]] or 0)
            stats_map[player_id] = {
                "player_name": str(row[columns["PLAYER_NAME"]]),
                "games_played": int(row[columns["GP"]] or 0),
                "mpg": float(row[columns["MIN"]] or 0),
                "ppg": float(row[columns["PTS"]] or 0),
                "rpg": float(row[columns["REB"]] or 0),
                "apg": float(row[columns["AST"]] or 0),
                "spg": float(row[columns["STL"]] or 0),
                "bpg": float(row[columns["BLK"]] or 0),
                "tpg": float(row[columns["TOV"]] or 0),
                "fg_pct": fg_pct,
                "fg3_pct": fg3_pct,
                "ft_pct": ft_pct,
                "ts_pct": round(min(0.75, max(0.45, fg_pct * 0.4 + fg3_pct * 0.35 + ft_pct * 0.25)), 3),
            }
        logger.info("Loaded season stats for %d players (%s)", len(stats_map), target_season)
        return stats_map
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Failed to fetch season stats for %s: %s", target_season, exc)
        return {}


def _fetch_season_stats_map() -> dict[int, dict[str, float | int | str]]:
    return fetch_season_stats_map(settings.current_season)


def prior_season(season: str) -> str:
    start_year = int(season.split("-")[0])
    prior = start_year - 1
    return f"{prior}-{str(start_year)[-2:]}"


def get_rostered_nba_ids(db: Session) -> set[int]:
    """NBA player IDs currently under contract on a team."""
    rostered = {
        int(p.nba_id)
        for p in db.query(Player.nba_id)
        .filter(Player.team_id.isnot(None), Player.is_free_agent.is_(False))
        .all()
    }
    if rostered:
        return rostered
    roster_players, _ = fetch_roster_data()
    return {int(p["nba_id"]) for p in roster_players}


def _overall_from_stats(stats: dict[str, float | int]) -> float:
    """Estimate overall rating from real per-game production."""
    mpg = float(stats.get("mpg", 0))
    if mpg < 3:
        return round(random.uniform(64, 70), 1)
    production = (
        float(stats.get("ppg", 0))
        + 0.7 * float(stats.get("rpg", 0))
        + 0.7 * float(stats.get("apg", 0))
        + 1.2 * float(stats.get("spg", 0))
        + 1.2 * float(stats.get("bpg", 0))
    )
    ovr = 58 + production * 0.82 + min(mpg, 36) * 0.35
    return round(min(99, max(60, ovr)), 1)


def _attributes_from_stats(overall: float, stats: dict[str, float | int]) -> dict[str, float]:
    """Derive attribute ratings anchored to real stat profile."""
    ppg = float(stats.get("ppg", 0))
    rpg = float(stats.get("rpg", 0))
    apg = float(stats.get("apg", 0))
    spg = float(stats.get("spg", 0))
    bpg = float(stats.get("bpg", 0))
    ts_pct = float(stats.get("ts_pct", 0.55))
    return {
        "overall_rating": overall,
        "potential": round(min(99, overall + random.uniform(0, 8)), 1),
        "shooting": round(min(99, max(55, overall + (ts_pct - 0.55) * 80)), 1),
        "defense": round(min(99, max(55, overall + spg * 2 + bpg * 2)), 1),
        "playmaking": round(min(99, max(55, overall + apg * 1.5)), 1),
        "athleticism": round(min(99, max(55, overall + random.uniform(-4, 4))), 1),
        "rebounding": round(min(99, max(55, overall + rpg * 1.8)), 1),
        "basketball_iq": round(min(99, max(55, overall + random.uniform(-3, 5))), 1),
        "durability": round(random.uniform(72, 92), 1),
        "ppg": ppg,
        "rpg": rpg,
        "apg": apg,
        "ts_pct": ts_pct,
        "per": round(10 + overall / 4 + ppg * 0.15, 1),
    }


def _assign_starters_by_minutes(db: Session, team_id: int) -> None:
    """Mark top-minute players as starters."""
    roster = (
        db.query(Player)
        .filter(Player.team_id == team_id)
        .order_by(Player.minutes_per_game.desc())
        .all()
    )
    for index, player in enumerate(roster):
        player.is_starter = index < 5 and player.minutes_per_game >= 10


def _parse_weight(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 200


def _generate_fallback_rosters() -> list[dict[str, Any]]:
    """Generate placeholder rosters when live roster fetch is unavailable."""
    logger.warning(
        "Using randomly generated placeholder rosters. "
        "Re-seed after fixing network access or install nba_api for real NBA players."
    )
    first_names = ["Jay", "Marcus", "Devin", "Tyler", "Chris", "Jordan", "Kyle", "Darius", "Cam", "Jalen"]
    last_names = ["Williams", "Johnson", "Brown", "Davis", "Miller", "Taylor", "Anderson", "Thomas", "Jackson", "White"]
    positions = ["PG", "SG", "SF", "PF", "C"]
    players: list[dict[str, Any]] = []
    pid = 100000

    for team in NBA_TEAMS:
        for i in range(15):
            pid += 1
            age = random.randint(20, 34)
            base = random.uniform(65, 88)
            players.append(
                {
                    "nba_id": pid,
                    "team_nba_id": team["nba_id"],
                    "first_name": random.choice(first_names),
                    "last_name": random.choice(last_names),
                    "position": positions[i % 5],
                    "age": age,
                    "height": f"{random.randint(6, 7)}-{random.randint(0, 11)}",
                    "weight": random.randint(185, 260),
                    "salary": round(random.uniform(1.0, 45.0), 2),
                    "base_rating": base,
                }
            )
    return players


def _derive_player_attributes(base_rating: float, age: int) -> dict[str, float]:
    variance = random.uniform(-8, 8)
    potential = min(99, base_rating + random.uniform(0, 15) if age < 24 else random.uniform(-5, 5))
    return {
        "overall_rating": round(max(60, min(99, base_rating + variance)), 1),
        "potential": round(max(60, min(99, potential)), 1),
        "shooting": round(base_rating + random.uniform(-10, 10), 1),
        "defense": round(base_rating + random.uniform(-10, 10), 1),
        "playmaking": round(base_rating + random.uniform(-10, 10), 1),
        "athleticism": round(base_rating + random.uniform(-10, 10), 1),
        "rebounding": round(base_rating + random.uniform(-10, 10), 1),
        "basketball_iq": round(base_rating + random.uniform(-8, 8), 1),
        "durability": round(random.uniform(70, 95), 1),
    }


def _team_profile(abbreviation: str) -> dict[str, Any]:
    return TEAM_PROFILES.get(
        abbreviation,
        {
            "difficulty": random.randint(2, 5),
            "young_core": random.choice(["A", "A-", "B+", "B", "B-", "C+"]),
            "cap_space": round(random.uniform(-30, 35), 1),
            "window": random.choice(["Now", "1-2 Years", "2-4 Years", "3-5 Years", "Rebuild"]),
            "draft_assets": random.randint(30, 90),
        },
    )


def is_database_seeded(db: Session) -> bool:
    return db.query(Team).count() > 0


def has_placeholder_rosters(db: Session) -> bool:
    """True when rosters came from the offline random-name fallback (IDs 100001–100450)."""
    return (
        db.query(Player)
        .filter(Player.nba_id >= 100001, Player.nba_id <= 100450, Player.team_id.isnot(None))
        .count()
        > 0
    )


def _populate_players(db: Session, team_by_nba_id: dict[int, Team]) -> tuple[str, int, bool]:
    """Create players and contracts from NBA roster data."""
    from app.services.contract_data_service import get_contract_lookup

    raw_players, roster_source = fetch_roster_data()
    season_stats = _fetch_season_stats_map()
    stats_applied = len(season_stats) > 0
    contract_lookup = get_contract_lookup(refresh=True)

    for pdata in raw_players:
        team = team_by_nba_id.get(pdata["team_nba_id"])
        if not team:
            continue

        age = pdata.get("age", 25)
        nba_id = int(pdata["nba_id"])
        player_stats = season_stats.get(nba_id)

        if player_stats and player_stats.get("mpg", 0) > 0:
            overall = _overall_from_stats(player_stats)
            stat_attrs = _attributes_from_stats(overall, player_stats)
            mpg = float(player_stats["mpg"])
            games_played = int(player_stats["games_played"])
            ppg = float(stat_attrs.pop("ppg"))
            rpg = float(stat_attrs.pop("rpg"))
            apg = float(stat_attrs.pop("apg"))
            ts_pct = float(stat_attrs.pop("ts_pct"))
            per = float(stat_attrs.pop("per"))
            fg_pct = float(player_stats.get("fg_pct", 0.45))
            fg3_pct = float(player_stats.get("fg3_pct", 0.35))
            tpg = float(player_stats.get("tpg", 0.0))
            is_starter = False
        else:
            base = pdata.get("base_rating", random.uniform(68, 85))
            stat_attrs = _derive_player_attributes(base, age)
            mpg = round(random.uniform(28, 36) if random.random() > 0.6 else random.uniform(8, 24), 1)
            games_played = 0
            ppg = rpg = apg = tpg = 0.0
            fg_pct = 0.45
            fg3_pct = 0.35
            ts_pct = 0.55
            per = round(10 + stat_attrs["overall_rating"] / 4, 1)
            is_starter = False

        contract = contract_lookup.for_player(
            team.abbreviation,
            str(pdata.get("first_name", "Unknown")),
            str(pdata.get("last_name", "Player")),
            nba_id,
            int(age),
        )

        player = Player(
            nba_id=nba_id,
            team_id=team.id,
            first_name=pdata.get("first_name", "Unknown"),
            last_name=pdata.get("last_name", "Player"),
            position=_normalize_position(str(pdata.get("position", "SF"))),
            age=age,
            height=str(pdata.get("height", "6-6")),
            weight=int(pdata.get("weight", 200)),
            salary=contract.salary,
            years_remaining=contract.years_remaining,
            is_starter=is_starter,
            minutes_per_game=round(mpg, 1),
            games_played=games_played,
            ppg=ppg,
            rpg=rpg,
            apg=apg,
            fg_pct=fg_pct,
            fg3_pct=fg3_pct,
            tpg=tpg,
            ts_pct=ts_pct,
            per=per,
            **stat_attrs,
        )
        db.add(player)
        db.flush()

        db.add(
            Contract(
                player_id=player.id,
                team_id=team.id,
                salary=player.salary,
                years_remaining=player.years_remaining,
                has_player_option=contract.has_player_option,
                has_team_option=contract.has_team_option,
                is_bird_rights=contract.is_bird_rights,
            )
        )

    player_count = db.query(Player).filter(Player.team_id.isnot(None)).count()
    return roster_source, player_count, stats_applied


def _finalize_team_ratings(db: Session, team_by_nba_id: dict[int, Team], *, reset_records: bool = False) -> None:
    for team in team_by_nba_id.values():
        _assign_starters_by_minutes(db, team.id)
        roster = db.query(Player).filter(Player.team_id == team.id).all()
        if roster:
            starters = [p for p in roster if p.is_starter] or sorted(
                roster, key=lambda p: p.overall_rating, reverse=True
            )[:5]
            team.overall_rating = round(sum(p.overall_rating for p in starters) / len(starters), 1)
        if reset_records:
            team.wins = 0
            team.losses = 0
        else:
            team.wins = max(0, min(82, int((team.overall_rating - 70) * 2.5 + random.randint(-5, 5))))
            team.losses = 82 - team.wins


def reload_rosters(db: Session) -> dict[str, str | int]:
    """Reset all players and contracts to current NBA roster data."""
    from app.models import Award, FreeAgentOffer, PlayerRatingHistory

    db.query(Award).delete()
    db.query(FreeAgentOffer).delete()
    db.query(PlayerRatingHistory).delete()
    db.query(Contract).delete()
    db.query(Player).delete()
    db.flush()

    teams = db.query(Team).all()
    team_by_nba_id = {team.nba_id: team for team in teams}
    roster_source, player_count, stats_applied = _populate_players(db, team_by_nba_id)
    _finalize_team_ratings(db, team_by_nba_id, reset_records=True)

    from app.services.salary_cap_service import sync_team_cap

    for team in team_by_nba_id.values():
        sync_team_cap(db, team.id)

    from app.services.free_agency_service import sync_real_free_agents

    sync_real_free_agents(db)
    db.commit()

    stats_note = f" with {settings.current_season} NBA stats" if stats_applied else ""
    logger.info(
        "Rosters reloaded with %d players from %s%s",
        player_count,
        roster_source,
        stats_note,
    )
    return {
        "message": f"Loaded {player_count} real NBA players from {roster_source}{stats_note}.",
        "roster_source": roster_source + (" + real stats" if stats_applied else ""),
        "player_count": player_count,
    }


def refresh_player_contracts(db: Session) -> dict[str, str | int]:
    """Update salaries on existing players from ESPN without wiping careers."""
    from app.models import Contract, Team
    from app.services.contract_data_service import get_contract_lookup
    from app.services.salary_cap_service import sync_team_cap

    contract_lookup = get_contract_lookup(refresh=True)
    updated = 0

    teams = {team.id: team for team in db.query(Team).all()}
    for player in db.query(Player).filter(Player.team_id.isnot(None)).all():
        team = teams.get(player.team_id)
        if not team:
            continue
        contract = contract_lookup.for_player(
            team.abbreviation,
            player.first_name,
            player.last_name,
            player.nba_id,
            player.age,
        )
        player.salary = contract.salary
        player.years_remaining = contract.years_remaining

        row = db.query(Contract).filter(Contract.player_id == player.id).first()
        if row:
            row.salary = contract.salary
            row.years_remaining = contract.years_remaining
            row.has_player_option = contract.has_player_option
            row.has_team_option = contract.has_team_option
            row.is_bird_rights = contract.is_bird_rights
        updated += 1

    for team in teams.values():
        sync_team_cap(db, team.id)

    db.commit()
    return {
        "message": f"Updated {updated} player contracts from {contract_lookup.source}.",
        "roster_source": contract_lookup.source,
        "player_count": updated,
    }


def seed_database(db: Session, force: bool = False) -> dict[str, str | int]:
    """Populate teams, players, contracts, and draft picks."""
    if is_database_seeded(db) and not force:
        return {"message": "Database already seeded. Use force=true to reload rosters.", "roster_source": "unchanged", "player_count": db.query(Player).count()}

    if force:
        from app.models import Award, CareerTeamState, DraftProspect, FreeAgentOffer, Game, PlayerRatingHistory, SeasonResult, TradeOffer, Transaction

        db.query(TradeOffer).delete()
        db.query(FreeAgentOffer).delete()
        db.query(DraftProspect).delete()
        db.query(CareerTeamState).delete()
        db.query(Game).delete()
        db.query(Transaction).delete()
        db.query(Award).delete()
        db.query(SeasonResult).delete()
        db.query(PlayerRatingHistory).delete()
        db.query(CareerSave).delete()
        db.query(Contract).delete()
        db.query(DraftPick).delete()
        db.query(Player).delete()
        db.query(Team).delete()
        db.commit()

    team_by_nba_id: dict[int, Team] = {}
    for info in NBA_TEAMS:
        profile = _team_profile(info["abbreviation"])
        team = Team(
            nba_id=info["nba_id"],
            name=info["name"],
            abbreviation=info["abbreviation"],
            city=info["city"],
            conference=info["conference"],
            division=info["division"],
            overall_rating=round(random.uniform(72, 92), 1),
            wins=random.randint(15, 55),
            losses=random.randint(15, 55),
            salary_cap_space=profile["cap_space"],
            luxury_tax=max(0, -profile["cap_space"]) if profile["cap_space"] < 0 else 0,
            young_core_rating=profile["young_core"],
            draft_assets_score=profile["draft_assets"],
            championship_window=profile["window"],
            difficulty_rating=profile["difficulty"],
            chemistry=round(random.uniform(65, 90), 1),
            fan_happiness=round(random.uniform(50, 95), 1),
            owner_expectations=random.choice(["Lottery", "Play-In", "Playoffs", "Conference Finals", "Championship"]),
            coach_philosophy=random.choice(["Pace & Space", "Defensive", "Balanced", "Motion Offense", "ISO Heavy"]),
            championship_odds=round(random.uniform(0.01, 0.25), 3),
            playoff_odds=round(random.uniform(0.1, 0.95), 3),
        )
        db.add(team)
        db.flush()
        team_by_nba_id[team.nba_id] = team

        start_year = int(settings.current_season.split("-")[0])
        for rnd in (1, 2):
            for year_offset in (1, 2, 3):
                year = start_year + year_offset
                db.add(
                    DraftPick(
                        team_id=team.id,
                        season=f"{year}-{str(year + 1)[-2:]}",
                        round_number=rnd,
                        original_team_id=team.id,
                    )
                )

    roster_source, player_count, stats_applied = _populate_players(db, team_by_nba_id)
    _finalize_team_ratings(db, team_by_nba_id)

    from app.services.salary_cap_service import sync_team_cap

    for team in team_by_nba_id.values():
        sync_team_cap(db, team.id)

    db.commit()
    stats_note = f" with {settings.current_season} NBA stats" if stats_applied else ""

    from app.services.free_agency_service import sync_real_free_agents

    sync_real_free_agents(db)

    logger.info(
        "Database seeded with %d teams, %d players from %s%s",
        len(team_by_nba_id),
        player_count,
        roster_source,
        stats_note,
    )
    return {
        "message": f"Database seeded with {player_count} players from {roster_source}{stats_note}.",
        "roster_source": roster_source + (" + real stats" if stats_applied else ""),
        "player_count": player_count,
    }
