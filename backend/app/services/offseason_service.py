"""Offseason progression: aging, development, contract expiration, season rollover."""

from __future__ import annotations

import random

from sqlalchemy.orm import Session

from app.models import CareerSave, Contract, Player, PlayerRatingHistory, Team
from app.schemas import OffseasonResponse
from app.services.free_agency_service import generate_free_agents
from app.services.news_service import log_news
from app.services.career_state_service import reset_career_records, sync_active_team_display
from app.services.extension_service import process_options
from app.services.awards_service import compute_season_awards
from app.services.schedule_service import ensure_career_schedule
from app.services.salary_cap_service import sync_team_cap


def _next_season(season: str) -> str:
    start = int(season.split("-")[0])
    return f"{start + 1}-{start + 2}"


def process_offseason(db: Session, career: CareerSave) -> OffseasonResponse:
    retirements: list[str] = []
    free_agents: list[str] = []
    developments: list[str] = []

    # Contract expiration
    players = db.query(Player).filter(Player.is_free_agent.is_(False), Player.team_id.isnot(None)).all()
    for player in players:
        player.years_remaining = max(0, player.years_remaining - 1)
        contract = db.query(Contract).filter(Contract.player_id == player.id).first()
        if contract:
            contract.years_remaining = player.years_remaining

        if player.years_remaining <= 0:
            player.is_free_agent = True
            player.team_id = None
            player.is_starter = False
            player.salary = 0.0
            free_agents.append(f"{player.first_name} {player.last_name}")
            if contract:
                db.delete(contract)

    # Retirements (age 38+ or low rating veterans)
    for player in db.query(Player).filter(Player.age >= 36).all():
        if player.overall_rating < 72 or player.age >= 38:
            if random.random() < 0.35:
                name = f"{player.first_name} {player.last_name}"
                retirements.append(name)
                if player.team_id:
                    team = db.query(Team).filter(Team.id == player.team_id).first()
                    log_news(db, career.season, "retirement", f"RETIREMENT: {name} ({team.abbreviation if team else 'FA'})")
                db.delete(player)

    option_events = process_options(db, career)

    # Player development
    for player in db.query(Player).filter(Player.team_id.isnot(None), Player.is_free_agent.is_(False)).all():
        player.age += 1
        old_ovr = player.overall_rating

        if player.age < 26 and player.potential > player.overall_rating:
            growth = random.uniform(0.5, 3.0) * (1 + player.minutes_per_game / 40)
            player.overall_rating = min(player.potential, player.overall_rating + growth)
            player.development_trend = "Rising"
        elif player.age >= 32:
            decline = random.uniform(0.5, 2.5)
            player.overall_rating = max(60, player.overall_rating - decline)
            player.development_trend = "Declining"
        else:
            player.development_trend = "Stable"

        if abs(player.overall_rating - old_ovr) >= 1:
            developments.append(
                f"{player.first_name} {player.last_name}: {old_ovr:.0f} → {player.overall_rating:.0f}"
            )

        db.add(
            PlayerRatingHistory(
                player_id=player.id,
                season=_next_season(career.season),
                overall_rating=player.overall_rating,
                potential=player.potential,
            )
        )

        player.games_played = 0
        player.ppg = player.rpg = player.apg = player.tpg = 0.0
        player.fatigue = 0.0
        if player.injury_status != "Healthy" and random.random() < 0.7:
            player.injury_status = "Healthy"

    reset_career_records(db, career.id)
    sync_active_team_display(db, career.id)
    for team in db.query(Team).all():
        sync_team_cap(db, team.id)

    compute_season_awards(db, career)

    generate_free_agents(db)

    new_season = _next_season(career.season)
    career.season = new_season
    career.season_day = 1
    career.phase = "regular_season"
    career.save_data = None

    ensure_career_schedule(db, career)

    log_news(
        db,
        new_season,
        "offseason",
        f"New season {new_season} begins! {len(free_agents)} players hit free agency.",
        career_id=career.id,
    )
    db.commit()

    return OffseasonResponse(
        new_season=new_season,
        retirements=retirements,
        free_agents=free_agents + option_events,
        developments=developments[:15],
        message=f"Offseason complete. Welcome to the {new_season} season!",
    )
