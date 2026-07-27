"""Real NBA salary and contract data from ESPN."""

from __future__ import annotations

import json
import logging
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

ESPN_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NBA-GM-Simulator/1.0)"}

# ESPN site API team id by our Team.abbreviation
ESPN_TEAM_IDS: dict[str, int] = {
    "ATL": 1,
    "BOS": 2,
    "BKN": 17,
    "CHA": 30,
    "CHI": 4,
    "CLE": 5,
    "DAL": 6,
    "DEN": 7,
    "DET": 8,
    "GSW": 9,
    "HOU": 10,
    "IND": 11,
    "LAC": 12,
    "LAL": 13,
    "MEM": 29,
    "MIA": 14,
    "MIL": 15,
    "MIN": 16,
    "NOP": 3,
    "NYK": 18,
    "OKC": 25,
    "ORL": 19,
    "PHI": 20,
    "PHX": 21,
    "POR": 22,
    "SAC": 23,
    "SAS": 24,
    "TOR": 28,
    "UTA": 26,
    "WAS": 27,
}

BUNDLED_SALARIES_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / f"salaries_{settings.current_season.replace('-', '_')}.json"
)

# Approximate 2025-26 league minimum (millions) by years of service tier
MIN_SALARY_BY_AGE: list[tuple[int, float]] = [
    (23, 2.29),
    (25, 2.59),
    (30, 2.89),
    (99, 3.29),
]
TWO_WAY_SALARY_MILLIONS = 0.58


@dataclass(frozen=True)
class PlayerContractData:
    salary: float
    years_remaining: int
    has_player_option: bool = False
    has_team_option: bool = False
    is_bird_rights: bool = False


_search_cache: dict[str, PlayerContractData] = {}


def _season_end_year(season: str | None = None) -> int:
    label = season or settings.current_season
    return int(label.split("-")[0]) + 1


def _normalize_name_part(value: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return "".join(char for char in ascii_name.lower() if char.isalnum())


def _name_key(team_abbrev: str, first_name: str, last_name: str) -> str:
    return f"{team_abbrev}:{_normalize_name_part(first_name)}:{_normalize_name_part(last_name)}"


def _minimum_salary(age: int) -> float:
    for max_age, salary in MIN_SALARY_BY_AGE:
        if age <= max_age:
            return salary
    return MIN_SALARY_BY_AGE[-1][1]


def _parse_contracts(contracts: list[dict[str, Any]], end_year: int) -> PlayerContractData:
    if not contracts:
        return PlayerContractData(salary=_minimum_salary(25), years_remaining=1)

    current = next((c for c in contracts if c.get("season", {}).get("year") == end_year), None)
    if not current:
        current = max(contracts, key=lambda c: c.get("season", {}).get("year", 0))

    salary_raw = int(current.get("salary") or 0)
    is_current_season = current.get("season", {}).get("year") == end_year

    if salary_raw > 0:
        salary_m = round(salary_raw / 1_000_000, 2)
    elif is_current_season:
        # ESPN lists $0 for two-way and some non-guaranteed deals
        salary_m = TWO_WAY_SALARY_MILLIONS
    else:
        salary_m = _minimum_salary(25)

    future_years = [
        c
        for c in contracts
        if c.get("season", {}).get("year", 0) >= end_year and int(c.get("salary") or 0) > 0
    ]
    if salary_raw == 0 and is_current_season:
        years_remaining = 1
    else:
        years_remaining = max(1, len(future_years))

    option_type = int(current.get("optionType") or 0)
    bird_status = int(current.get("birdStatus") or 0)

    return PlayerContractData(
        salary=salary_m,
        years_remaining=years_remaining,
        has_player_option=option_type == 2,
        has_team_option=option_type == 1,
        is_bird_rights=bird_status >= 1,
    )


def _fetch_espn_team_roster(team_abbrev: str, espn_team_id: int, end_year: int) -> dict[str, PlayerContractData]:
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{espn_team_id}/roster"
    request = urllib.request.Request(url, headers=ESPN_HEADERS)
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode())

    results: dict[str, PlayerContractData] = {}
    for athlete in payload.get("athletes", []):
        first_name = str(athlete.get("firstName", ""))
        last_name = str(athlete.get("lastName", ""))
        if not first_name and not last_name:
            continue
        key = _name_key(team_abbrev, first_name, last_name)
        contracts = athlete.get("contracts") or []
        results[key] = _parse_contracts(contracts, end_year)
    return results


def _fetch_contract_by_espn_id(espn_id: str, end_year: int) -> PlayerContractData | None:
    detail_url = (
        f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/athletes/"
        f"{espn_id}/contracts/{end_year}?lang=en&region=us"
    )
    try:
        request = urllib.request.Request(detail_url, headers=ESPN_HEADERS)
        with urllib.request.urlopen(request, timeout=20) as response:
            detail = json.loads(response.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError):
        return None

    salary_raw = int(detail.get("salary") or 0)
    if salary_raw <= 0:
        return None

    years_remaining = max(1, int(detail.get("yearsRemaining") or 1))
    option_type = int(detail.get("optionType") or 0)
    bird_status = int(detail.get("birdStatus") or 0)

    return PlayerContractData(
        salary=round(salary_raw / 1_000_000, 2),
        years_remaining=years_remaining,
        has_player_option=option_type == 2,
        has_team_option=option_type == 1,
        is_bird_rights=bird_status >= 1,
    )


def _search_espn_athlete_id(first_name: str, last_name: str) -> str | None:
    import urllib.parse

    query = urllib.parse.quote(f"{first_name} {last_name}")
    url = f"https://site.api.espn.com/apis/search/v2?query={query}&limit=5"
    try:
        request = urllib.request.Request(url, headers=ESPN_HEADERS)
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None

    target = _normalize_name_part(first_name) + _normalize_name_part(last_name)
    for section in payload.get("results", []):
        if section.get("type") != "player":
            continue
        for item in section.get("contents", []):
            display = str(item.get("displayName", ""))
            parts = display.split()
            if len(parts) < 2:
                continue
            candidate = _normalize_name_part(parts[0]) + _normalize_name_part(" ".join(parts[1:]))
            if candidate != target:
                continue
            uid = str(item.get("uid", ""))
            if "~a:" in uid:
                return uid.rsplit("~a:", 1)[-1]
    return None


def _lookup_via_search(first_name: str, last_name: str, end_year: int) -> PlayerContractData | None:
    cache_key = f"{first_name}:{last_name}".lower()
    if cache_key in _search_cache:
        return _search_cache[cache_key]

    espn_id = _search_espn_athlete_id(first_name, last_name)
    if not espn_id:
        return None

    contract = _fetch_contract_by_espn_id(espn_id, end_year)
    if contract:
        _search_cache[cache_key] = contract
    return contract


def fetch_espn_contract_lookup() -> dict[str, PlayerContractData]:
    """Build name+team -> contract map from ESPN rosters."""
    end_year = _season_end_year()
    lookup: dict[str, PlayerContractData] = {}

    for team_abbrev, espn_team_id in ESPN_TEAM_IDS.items():
        try:
            lookup.update(_fetch_espn_team_roster(team_abbrev, espn_team_id, end_year))
            time.sleep(0.25)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("ESPN contract fetch failed for %s: %s", team_abbrev, exc)

    logger.info("Loaded %d player contracts from ESPN", len(lookup))
    return lookup


def _load_bundled_salaries() -> dict[int, PlayerContractData]:
    if not BUNDLED_SALARIES_PATH.exists():
        return {}
    try:
        raw = json.loads(BUNDLED_SALARIES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read bundled salaries: %s", exc)
        return {}

    results: dict[int, PlayerContractData] = {}
    for nba_id_str, payload in raw.items():
        try:
            nba_id = int(nba_id_str)
            results[nba_id] = PlayerContractData(
                salary=float(payload["salary"]),
                years_remaining=int(payload.get("years_remaining", 1)),
                has_player_option=bool(payload.get("has_player_option", False)),
                has_team_option=bool(payload.get("has_team_option", False)),
                is_bird_rights=bool(payload.get("is_bird_rights", False)),
            )
        except (TypeError, ValueError, KeyError):
            continue
    return results


_lookup_cache: ContractLookup | None = None


@dataclass
class ContractLookup:
    by_name: dict[str, PlayerContractData]
    by_nba_id: dict[int, PlayerContractData]
    source: str

    def for_player(
        self,
        team_abbrev: str,
        first_name: str,
        last_name: str,
        nba_id: int,
        age: int,
    ) -> PlayerContractData:
        key = _name_key(team_abbrev, first_name, last_name)
        if key in self.by_name:
            return self.by_name[key]

        searched = _lookup_via_search(first_name, last_name, _season_end_year())
        if searched:
            return searched

        if nba_id in self.by_nba_id:
            return self.by_nba_id[nba_id]

        logger.debug("No ESPN salary for %s %s (%s), using minimum", first_name, last_name, team_abbrev)
        return PlayerContractData(salary=_minimum_salary(age), years_remaining=1)


def get_contract_lookup(*, refresh: bool = False) -> ContractLookup:
    global _lookup_cache
    if refresh:
        _lookup_cache = None
        _search_cache.clear()

    if _lookup_cache is not None:
        return _lookup_cache

    by_nba_id = _load_bundled_salaries()
    by_name = fetch_espn_contract_lookup()
    source = "espn.com"
    if by_nba_id:
        source = "espn.com + bundled snapshot"

    _lookup_cache = ContractLookup(by_name=by_name, by_nba_id=by_nba_id, source=source)
    return _lookup_cache


def build_bundled_salary_file(players: list[dict[str, Any]], lookup: ContractLookup) -> dict[str, dict[str, Any]]:
    """Match roster players to contracts and return JSON-serializable salary map."""
    from app.services.seed_service import NBA_TEAMS

    abbrev_by_nba_team_id = {team["nba_id"]: team["abbreviation"] for team in NBA_TEAMS}
    output: dict[str, dict[str, Any]] = {}

    for player in players:
        team_abbrev = abbrev_by_nba_team_id.get(int(player["team_nba_id"]), "")
        if not team_abbrev:
            continue
        contract = lookup.for_player(
            team_abbrev,
            str(player.get("first_name", "")),
            str(player.get("last_name", "")),
            int(player["nba_id"]),
            int(player.get("age", 25)),
        )
        output[str(player["nba_id"])] = {
            "salary": contract.salary,
            "years_remaining": contract.years_remaining,
            "has_player_option": contract.has_player_option,
            "has_team_option": contract.has_team_option,
            "is_bird_rights": contract.is_bird_rights,
        }
    return output
