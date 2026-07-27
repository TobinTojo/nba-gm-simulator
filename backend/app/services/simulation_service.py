"""Game and season simulation engine."""

from __future__ import annotations

import random
from typing import Literal

from sqlalchemy.orm import Session

from app.models import CareerSave, Game, Player, Team
from app.schemas import BoxScorePlayer, GameResult, SimulationResponse
from app.services.news_service import log_news
from app.services.schedule_service import (
    SEASON_LENGTH_DAYS,
    ensure_career_schedule,
    get_games_for_day,
    get_next_user_game_day,
)

SimulationMode = Literal["game", "week", "month", "all_star", "deadline", "playoffs", "season"]

MODE_DAY_TARGETS: dict[SimulationMode, int | None] = {
    "game": None,
    "week": 7,
    "month": 30,
    "all_star": 60,
    "deadline": 100,
    "playoffs": 150,
    "season": SEASON_LENGTH_DAYS,
}

INJURY_TYPES = ["Healthy", "Day-to-Day", "Out 1-2 Weeks", "Out 1 Month", "Season Ending"]


class SimulationServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _team_strength(db: Session, team_id: int) -> float:
    players = (
        db.query(Player)
        .filter(Player.team_id == team_id, Player.is_g_league.is_(False), Player.injury_status == "Healthy")
        .order_by(Player.overall_rating.desc())
        .limit(10)
        .all()
    )
    if not players:
        team = db.query(Team).filter(Team.id == team_id).first()
        return team.overall_rating if team else 75.0

    starters = [p for p in players if p.is_starter][:5]
    bench = [p for p in players if not p.is_starter][:5]
    core = starters if starters else players[:5]

    starter_avg = sum(p.overall_rating for p in core) / len(core)
    bench_avg = sum(p.overall_rating for p in bench) / max(1, len(bench))
    team = db.query(Team).filter(Team.id == team_id).first()
    chemistry = team.chemistry if team else 75.0

    return starter_avg * 0.75 + bench_avg * 0.15 + chemistry * 0.1


def _simulate_score(home_strength: float, away_strength: float) -> tuple[int, int]:
    home_adv = 3.5
    base = 108 + random.gauss(0, 6)
    home_expected = base + (home_strength - away_strength) * 0.35 + home_adv
    away_expected = base + (away_strength - home_strength) * 0.35
    home_score = max(85, int(round(home_expected + random.gauss(0, 8))))
    away_score = max(85, int(round(away_expected + random.gauss(0, 8))))
    if home_score == away_score:
        home_score += random.choice([-1, 1])
    return home_score, away_score


def _generate_box_score(db: Session, team_id: int, team_score: int) -> list[BoxScorePlayer]:
    players = (
        db.query(Player)
        .filter(Player.team_id == team_id, Player.is_g_league.is_(False))
        .order_by(Player.minutes_per_game.desc())
        .limit(8)
        .all()
    )
    if not players:
        return []

    total_minutes = sum(p.minutes_per_game for p in players) or 1
    box: list[BoxScorePlayer] = []
    points_allocated = 0

    for i, player in enumerate(players):
        share = player.minutes_per_game / total_minutes
        pts = int(round(team_score * share * random.uniform(0.8, 1.2)))
        if i == len(players) - 1:
            pts = max(0, team_score - points_allocated)
        else:
            points_allocated += pts

        reb = max(0, int(round(player.rebounding / 15 + random.uniform(0, 4))))
        ast = max(0, int(round(player.playmaking / 18 + random.uniform(0, 4))))
        tov = max(0, int(round(random.uniform(0, 3) + (1.5 if ast > 5 else 0.5))))

        box.append(
            BoxScorePlayer(
                player_id=player.id,
                name=f"{player.first_name} {player.last_name}",
                points=pts,
                rebounds=reb,
                assists=ast,
                minutes=round(player.minutes_per_game + random.uniform(-2, 2), 1),
            )
        )

        gp = player.games_played + 1
        player.games_played = gp
        player.ppg = round(((player.ppg * (gp - 1)) + pts) / gp, 1)
        player.rpg = round(((player.rpg * (gp - 1)) + reb) / gp, 1)
        player.apg = round(((player.apg * (gp - 1)) + ast) / gp, 1)
        player.tpg = round(((player.tpg * (gp - 1)) + tov) / gp, 1)
        if pts > 0:
            made = pts * random.uniform(0.38, 0.52)
            player.fg_pct = round(min(0.65, max(0.35, made / max(pts * 1.8, 1))), 3)
            player.fg3_pct = round(min(0.5, max(0.25, player.fg3_pct + random.uniform(-0.02, 0.02))), 3)
        player.fatigue = min(100, player.fatigue + random.uniform(3, 8))

    return box


def _apply_random_injury(db: Session, team_id: int, season: str) -> str | None:
    if random.random() > 0.04:
        return None

    players = (
        db.query(Player)
        .filter(Player.team_id == team_id, Player.injury_status == "Healthy", Player.is_g_league.is_(False))
        .all()
    )
    if not players:
        return None

    player = random.choice(players)
    severity = random.choices(
        INJURY_TYPES[1:],
        weights=[50, 30, 15, 5],
    )[0]
    player.injury_status = severity
    team = db.query(Team).filter(Team.id == team_id).first()
    msg = f"INJURY: {player.first_name} {player.last_name} ({team.abbreviation}) — {severity}"
    log_news(db, season, "injury", msg, career_id=None)
    return msg


def _recover_injuries(db: Session) -> None:
    for player in db.query(Player).filter(Player.injury_status != "Healthy").all():
        if player.injury_status == "Day-to-Day" and random.random() < 0.5:
            player.injury_status = "Healthy"
        elif player.injury_status == "Out 1-2 Weeks" and random.random() < 0.15:
            player.injury_status = "Healthy"


def _play_game(db: Session, game: Game, user_team_id: int, season: str, career: CareerSave) -> GameResult | None:
    home = db.query(Team).filter(Team.id == game.home_team_id).first()
    away = db.query(Team).filter(Team.id == game.away_team_id).first()
    if not home or not away:
        return None

    home_str = _team_strength(db, home.id)
    away_str = _team_strength(db, away.id)
    home_score, away_score = _simulate_score(home_str, away_str)

    game.home_score = home_score
    game.away_score = away_score
    game.is_played = True

    home_won = home_score > away_score
    from app.services.career_state_service import apply_game_result, sync_active_team_display

    apply_game_result(db, career.id, home.id, away.id, home_won)
    sync_active_team_display(db, career.id)

    user_involved = user_team_id in (home.id, away.id)
    result: GameResult | None = None

    if user_involved:
        is_home = home.id == user_team_id
        user_team = home if is_home else away
        opp_team = away if is_home else home
        user_score = home_score if is_home else away_score
        opp_score = away_score if is_home else home_score
        won = user_score > opp_score

        from app.services.owner_service import on_game_result

        on_game_result(db, career, won)

        home_box = _generate_box_score(db, home.id, home_score)
        away_box = _generate_box_score(db, away.id, away_score)

        _apply_random_injury(db, user_team_id, season)
        headline = (
            f"{'W' if won else 'L'} {user_score}-{opp_score}: "
            f"{user_team.city} {user_team.name} vs {opp_team.city} {opp_team.name}"
        )
        log_news(db, season, "game", headline, career_id=career.id)

        result = GameResult(
            game_id=game.id,
            season_day=game.season_day,
            home_team=f"{home.city} {home.name}",
            away_team=f"{away.city} {away.name}",
            home_score=home_score,
            away_score=away_score,
            user_team_won=won,
            home_box_score=home_box,
            away_box_score=away_box,
        )

    db.commit()
    return result


def simulate(db: Session, career: CareerSave, mode: SimulationMode) -> SimulationResponse:
    ensure_career_schedule(db, career)
    user_team_id = career.team_id
    games_simulated = 0
    days_advanced = 0
    last_result: GameResult | None = None
    news: list[str] = []

    if mode == "game":
        next_day = get_next_user_game_day(db, career, user_team_id)
        if next_day is None:
            raise SimulationServiceError("No remaining games this season")

        day_games = get_games_for_day(db, career, next_day)
        for game in day_games:
            result = _play_game(db, game, user_team_id, career.season, career)
            if result:
                last_result = result
                news.append(
                    f"Day {next_day}: {result.home_team} {result.home_score} - "
                    f"{result.away_score} {result.away_team}"
                )
            games_simulated += 1

        _recover_injuries(db)
        career.season_day = next_day + 1
        days_advanced = 1

        from app.services.trade_inbox_service import generate_ai_trade_offer, generate_trade_rumors

        generate_trade_rumors(db, career)
        generate_ai_trade_offer(db, career)
        from app.services.owner_service import evaluate_job_security

        evaluate_job_security(db, career)

        db.commit()
        db.refresh(career)

        return SimulationResponse(
            mode=mode,
            games_simulated=games_simulated,
            days_advanced=days_advanced,
            season_day=career.season_day,
            season=career.season,
            last_game=last_result,
            news=news[-10:],
        )

    target = MODE_DAY_TARGETS[mode]
    target_day = min(SEASON_LENGTH_DAYS, career.season_day + (target or 0))

    current_day = career.season_day
    while current_day <= target_day:
        day_games = get_games_for_day(db, career, current_day)
        if not day_games:
            current_day += 1
            continue

        for game in day_games:
            result = _play_game(db, game, user_team_id, career.season, career)
            if result:
                last_result = result
                news.append(
                    f"Day {current_day}: {result.home_team} {result.home_score} - "
                    f"{result.away_score} {result.away_team}"
                )
            games_simulated += 1

        _recover_injuries(db)
        current_day += 1
        days_advanced += 1
        career.season_day = current_day

    # Weekly recap news
    if days_advanced >= 7 and random.random() < 0.6:
        from app.services.career_state_service import get_record

        team = db.query(Team).filter(Team.id == user_team_id).first()
        wins, losses = get_record(db, career.id, user_team_id)
        recap = (
            f"Weekly Recap: {team.city} {team.name} sit at {wins}-{losses}. "
            f"Power ranking movement pending."
        )
        log_news(db, career.season, "recap", recap, career_id=career.id)
        news.append(recap)

        from app.services.trade_inbox_service import generate_ai_trade_offer, generate_trade_rumors

        generate_trade_rumors(db, career)
        generate_ai_trade_offer(db, career)
        from app.services.owner_service import evaluate_job_security

        evaluate_job_security(db, career)

    db.commit()
    db.refresh(career)

    return SimulationResponse(
        mode=mode,
        games_simulated=games_simulated,
        days_advanced=days_advanced,
        season_day=career.season_day,
        season=career.season,
        last_game=last_result,
        news=news[-10:],
    )
