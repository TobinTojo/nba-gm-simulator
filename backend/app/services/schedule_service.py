"""Season schedule generation and queries."""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import CareerSave, Game, Team
from app.schemas import GameSummary, ScheduleResponse

SEASON_LENGTH_DAYS = 170
GAMES_PER_TEAM = 82


def _date_for_day(season: str, day: int) -> str:
    year = int(season.split("-")[0])
    start = datetime(year, 10, 20)
    return (start + timedelta(days=day - 1)).strftime("%Y-%m-%d")


def ensure_career_schedule(db: Session, career: CareerSave) -> None:
    """Generate an 82-game schedule for the user's team plus league background games."""
    existing = (
        db.query(Game)
        .filter(Game.career_id == career.id, Game.season == career.season)
        .count()
    )
    if existing > 0:
        return

    teams = db.query(Team).all()
    user_team = career.team_id
    opponents = [t for t in teams if t.id != user_team]
    random.shuffle(opponents)

    # User team schedule: 82 games spread across season days
    user_game_days = sorted(random.sample(range(1, SEASON_LENGTH_DAYS + 1), GAMES_PER_TEAM))
    opp_cycle = opponents * 3
    random.shuffle(opp_cycle)

    for day, opponent in zip(user_game_days, opp_cycle[:GAMES_PER_TEAM]):
        is_home = random.random() > 0.5
        home_id = user_team if is_home else opponent.id
        away_id = opponent.id if is_home else user_team
        db.add(
            Game(
                season=career.season,
                season_day=day,
                game_date=_date_for_day(career.season, day),
                home_team_id=home_id,
                away_team_id=away_id,
                career_id=career.id,
            )
        )

    # Background league games on other days (simplified)
    background_days = [d for d in range(1, SEASON_LENGTH_DAYS + 1) if d not in user_game_days]
    for day in background_days[::3]:  # every 3rd non-user day
        t1, t2 = random.sample(teams, 2)
        if t1.id == user_team or t2.id == user_team:
            continue
        db.add(
            Game(
                season=career.season,
                season_day=day,
                game_date=_date_for_day(career.season, day),
                home_team_id=t1.id,
                away_team_id=t2.id,
                career_id=career.id,
            )
        )

    db.commit()


def get_team_schedule(db: Session, career: CareerSave, team_id: int) -> ScheduleResponse:
    ensure_career_schedule(db, career)

    games = (
        db.query(Game)
        .filter(
            Game.career_id == career.id,
            Game.season == career.season,
            ((Game.home_team_id == team_id) | (Game.away_team_id == team_id)),
        )
        .order_by(Game.season_day)
        .all()
    )

    team_map = {t.id: t for t in db.query(Team).all()}
    summaries: list[GameSummary] = []

    for game in games:
        is_home = game.home_team_id == team_id
        opponent = team_map[game.away_team_id if is_home else game.home_team_id]
        team_score = game.home_score if is_home else game.away_score
        opp_score = game.away_score if is_home else game.home_score
        result = None
        if game.is_played and team_score is not None and opp_score is not None:
            result = "W" if team_score > opp_score else "L"

        summaries.append(
            GameSummary(
                id=game.id,
                season_day=game.season_day,
                game_date=game.game_date,
                is_home=is_home,
                opponent_id=opponent.id,
                opponent_abbreviation=opponent.abbreviation,
                opponent_name=f"{opponent.city} {opponent.name}",
                team_score=team_score,
                opponent_score=opp_score,
                is_played=game.is_played,
                result=result,
            )
        )

    upcoming = [g for g in summaries if not g.is_played][:5]
    recent = [g for g in summaries if g.is_played][-5:][::-1]

    return ScheduleResponse(
        season=career.season,
        season_day=career.season_day,
        games=summaries,
        upcoming=upcoming,
        recent=recent,
    )


def get_games_for_day(db: Session, career: CareerSave, season_day: int) -> list[Game]:
    return (
        db.query(Game)
        .filter(
            Game.career_id == career.id,
            Game.season == career.season,
            Game.season_day == season_day,
            Game.is_played.is_(False),
        )
        .all()
    )


def get_next_user_game_day(db: Session, career: CareerSave, team_id: int) -> int | None:
    ensure_career_schedule(db, career)
    game = (
        db.query(Game)
        .filter(
            Game.career_id == career.id,
            Game.season == career.season,
            Game.is_played.is_(False),
            ((Game.home_team_id == team_id) | (Game.away_team_id == team_id)),
            Game.season_day >= career.season_day,
        )
        .order_by(Game.season_day)
        .first()
    )
    return game.season_day if game else None
