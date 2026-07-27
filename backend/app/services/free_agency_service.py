"""Free agency pool, offers, and signings."""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models import CareerSave, Contract, FreeAgentOffer, Player, Team
from app.schemas import FreeAgentSummary, FreeAgencyOfferRequest, SigningResult
from app.services.news_service import log_news
from app.services.salary_cap_service import sync_team_cap, validate_signing
from app.services.seed_service import (
    _attributes_from_stats,
    _normalize_position,
    _overall_from_stats,
    _parse_player_name,
    fetch_season_stats_map,
    get_rostered_nba_ids,
    prior_season,
)

logger = logging.getLogger(__name__)

FAKE_FA_NBA_ID_MIN = 900_000
BUNDLED_FA_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / f"free_agents_{settings.current_season.replace('-', '_')}.json"
)


class FreeAgencyServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


MARKET_SIZE: dict[str, float] = {
    "LAL": 1.2, "NYK": 1.15, "BKN": 1.1, "GSW": 1.1, "MIA": 1.05,
    "CHI": 1.05, "PHI": 1.0, "BOS": 1.0, "DAL": 1.0, "HOU": 0.95,
}


def _desired_salary(overall: float) -> float:
    return round(overall * 0.35 + 2, 1)


def _merge_stats_maps(*maps: dict[int, dict[str, Any]]) -> dict[int, dict[str, Any]]:
    merged: dict[int, dict[str, Any]] = {}
    for stats_map in maps:
        for player_id, stats in stats_map.items():
            existing = merged.get(player_id)
            if not existing or float(stats.get("mpg", 0)) > float(existing.get("mpg", 0)):
                merged[player_id] = stats
    return merged


def _load_bundled_free_agents() -> list[dict[str, Any]]:
    if not BUNDLED_FA_PATH.exists():
        return []
    try:
        data = json.loads(BUNDLED_FA_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            logger.info("Loaded %d bundled free agents", len(data))
            return data
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        logger.warning("Failed to read bundled free agents: %s", exc)
    return []


def _build_free_agent_candidates(rostered_ids: set[int]) -> list[dict[str, Any]]:
    """NBA players with recent minutes who are not on a current roster."""
    current_stats = fetch_season_stats_map(settings.current_season)
    previous_stats = fetch_season_stats_map(prior_season(settings.current_season))
    merged = _merge_stats_maps(previous_stats, current_stats)

    candidates: list[dict[str, Any]] = []
    for nba_id, stats in merged.items():
        if nba_id in rostered_ids:
            continue
        games_played = int(stats.get("games_played", 0))
        mpg = float(stats.get("mpg", 0))
        if games_played < 10 or mpg < 8:
            continue
        first_name, last_name = _parse_player_name(str(stats.get("player_name", "Unknown Player")))
        candidates.append(
            {
                "nba_id": nba_id,
                "first_name": first_name,
                "last_name": last_name,
                "position": _normalize_position(str(stats.get("position", "SF"))),
                "stats": stats,
                "sort_key": mpg,
            }
        )

    candidates.sort(key=lambda item: item["sort_key"], reverse=True)
    return candidates


def _upsert_free_agent(db: Session, candidate: dict[str, Any]) -> None:
    stats = candidate["stats"]
    nba_id = int(candidate["nba_id"])
    player = db.query(Player).filter(Player.nba_id == nba_id).first()

    overall = _overall_from_stats(stats)
    stat_attrs = _attributes_from_stats(overall, stats)
    ppg = float(stat_attrs.pop("ppg"))
    rpg = float(stat_attrs.pop("rpg"))
    apg = float(stat_attrs.pop("apg"))
    ts_pct = float(stat_attrs.pop("ts_pct"))
    per = float(stat_attrs.pop("per"))

    if player:
        if player.team_id is not None and not player.is_free_agent:
            return
        player.team_id = None
        player.is_free_agent = True
        player.is_starter = False
        player.minutes_per_game = round(float(stats.get("mpg", 0)), 1)
        player.games_played = int(stats.get("games_played", 0))
        player.ppg = ppg
        player.rpg = rpg
        player.apg = apg
        player.fg_pct = float(stats.get("fg_pct", player.fg_pct or 0.45))
        player.fg3_pct = float(stats.get("fg3_pct", player.fg3_pct or 0.35))
        player.tpg = float(stats.get("tpg", player.tpg or 0.0))
        player.ts_pct = ts_pct
        player.per = per
        for key, value in stat_attrs.items():
            setattr(player, key, value)
        return

    db.add(
        Player(
            nba_id=nba_id,
            team_id=None,
            first_name=candidate["first_name"],
            last_name=candidate["last_name"],
            position=candidate.get("position", "SF"),
            age=int(candidate.get("age", 27)),
            height=str(candidate.get("height", "6-6")),
            weight=int(candidate.get("weight", 210)),
            salary=0.0,
            years_remaining=0,
            is_free_agent=True,
            is_starter=False,
            minutes_per_game=round(float(stats.get("mpg", 0)), 1),
            games_played=int(stats.get("games_played", 0)),
            ppg=ppg,
            rpg=rpg,
            apg=apg,
            fg_pct=float(stats.get("fg_pct", 0.45)),
            fg3_pct=float(stats.get("fg3_pct", 0.35)),
            tpg=float(stats.get("tpg", 0.0)),
            ts_pct=ts_pct,
            per=per,
            **stat_attrs,
        )
    )


def sync_real_free_agents(db: Session, count: int = 50) -> int:
    """Replace placeholder free agents with real NBA players not on a roster."""
    db.query(Player).filter(
        Player.is_free_agent.is_(True),
        Player.nba_id >= FAKE_FA_NBA_ID_MIN,
    ).delete(synchronize_session=False)
    db.commit()

    rostered_ids = get_rostered_nba_ids(db)
    candidates = _build_free_agent_candidates(rostered_ids)

    if len(candidates) < 15:
        bundled = _load_bundled_free_agents()
        bundled_ids = {int(item["nba_id"]) for item in candidates}
        for item in bundled:
            if int(item["nba_id"]) in rostered_ids or int(item["nba_id"]) in bundled_ids:
                continue
            candidates.append(item)
            bundled_ids.add(int(item["nba_id"]))
        candidates.sort(key=lambda item: float(item.get("stats", {}).get("mpg", item.get("sort_key", 0))), reverse=True)

    synced = 0
    for candidate in candidates[:count]:
        if int(candidate["nba_id"]) in rostered_ids:
            continue
        _upsert_free_agent(db, candidate)
        synced += 1

    db.commit()
    logger.info("Synced %d real free agents for %s", synced, settings.current_season)
    return synced


def generate_free_agents(db: Session, count: int = 50) -> None:
    """Ensure the free agent pool uses real NBA players."""
    real_count = (
        db.query(Player)
        .filter(Player.is_free_agent.is_(True), Player.nba_id < FAKE_FA_NBA_ID_MIN)
        .count()
    )
    fake_count = (
        db.query(Player)
        .filter(Player.is_free_agent.is_(True), Player.nba_id >= FAKE_FA_NBA_ID_MIN)
        .count()
    )
    if fake_count > 0 or real_count < min(count, 15):
        sync_real_free_agents(db, count=count)


def get_free_agents(db: Session) -> list[FreeAgentSummary]:
    generate_free_agents(db)
    players = (
        db.query(Player)
        .filter(Player.is_free_agent.is_(True), Player.nba_id < FAKE_FA_NBA_ID_MIN)
        .order_by(Player.overall_rating.desc())
        .all()
    )
    return [
        FreeAgentSummary(
            id=p.id,
            first_name=p.first_name,
            last_name=p.last_name,
            position=p.position,
            age=p.age,
            overall_rating=p.overall_rating,
            potential=p.potential,
            desired_salary=_desired_salary(p.overall_rating),
        )
        for p in players
    ]


def _acceptance_score(
    db: Session,
    player: Player,
    team: Team,
    salary: float,
    years: int,
) -> float:
    desired = _desired_salary(player.overall_rating)
    money_score = min(100, (salary / max(desired, 1)) * 60)
    success_score = min(100, (team.wins / max(1, team.wins + team.losses)) * 100 + 20)
    market = MARKET_SIZE.get(team.abbreviation, 0.9) * 20
    years_bonus = min(15, years * 3)
    title_bonus = team.championship_odds * 100
    mood = player.player_mood * 0.1
    return money_score + success_score * 0.25 + market + years_bonus + title_bonus + mood


def make_offer(
    db: Session,
    career: CareerSave,
    team_id: int,
    request: FreeAgencyOfferRequest,
) -> SigningResult:
    player = db.query(Player).filter(Player.id == request.player_id).first()
    if not player or not player.is_free_agent:
        raise FreeAgencyServiceError("Player is not a free agent")

    valid, msg = validate_signing(db, team_id, request.salary)
    if not valid:
        return SigningResult(
            success=False,
            player_id=player.id,
            player_name=f"{player.first_name} {player.last_name}",
            message=msg,
        )

    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise FreeAgencyServiceError("Team not found")

    score = _acceptance_score(db, player, team, request.salary, request.years)
    threshold = 85 + random.uniform(-8, 8)
    accepted = score >= threshold

    offer = FreeAgentOffer(
        career_id=career.id,
        player_id=player.id,
        team_id=team_id,
        salary=request.salary,
        years=request.years,
        status="accepted" if accepted else "rejected",
    )
    db.add(offer)

    if not accepted:
        db.commit()
        return SigningResult(
            success=False,
            player_id=player.id,
            player_name=f"{player.first_name} {player.last_name}",
            message=f"{player.first_name} {player.last_name} declined your offer.",
        )

    player.team_id = team_id
    player.is_free_agent = False
    player.salary = request.salary
    player.years_remaining = request.years
    player.is_starter = False
    player.minutes_per_game = 15.0

    contract = db.query(Contract).filter(Contract.player_id == player.id).first()
    if contract:
        contract.team_id = team_id
        contract.salary = request.salary
        contract.years_remaining = request.years
    else:
        db.add(
            Contract(
                player_id=player.id,
                team_id=team_id,
                salary=request.salary,
                years_remaining=request.years,
            )
        )

    sync_team_cap(db, team_id)
    log_news(
        db,
        career.season,
        "free_agency",
        f"SIGNED: {player.first_name} {player.last_name} to {team.abbreviation} "
        f"({request.years}yr/${request.salary:.1f}M)",
        career_id=career.id,
    )
    db.commit()

    return SigningResult(
        success=True,
        player_id=player.id,
        player_name=f"{player.first_name} {player.last_name}",
        message=f"Signed {player.first_name} {player.last_name}!",
        salary=request.salary,
        years=request.years,
    )
