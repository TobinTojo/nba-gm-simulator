"""Player-related business logic."""

from __future__ import annotations

import random

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Player, PlayerRatingHistory, Team
from app.schemas import PlayerDetail, PlayerRatingPoint, PlayerSeasonStats


def _ensure_rating_history(db: Session, player: Player) -> list[PlayerRatingHistory]:
    history = (
        db.query(PlayerRatingHistory)
        .filter(PlayerRatingHistory.player_id == player.id)
        .order_by(PlayerRatingHistory.season)
        .all()
    )
    if history:
        return history

    seasons = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
    base = player.overall_rating - random.uniform(2, 8)
    entries: list[PlayerRatingHistory] = []
    for season in seasons:
        base = min(player.potential, base + random.uniform(0.5, 3.0))
        if season == settings.current_season:
            base = player.overall_rating
        entry = PlayerRatingHistory(
            player_id=player.id,
            season=season,
            overall_rating=round(base, 1),
            potential=player.potential,
        )
        db.add(entry)
        entries.append(entry)
    db.commit()
    return entries


def _ensure_season_stats(player: Player) -> PlayerSeasonStats:
    if player.games_played > 0:
        return PlayerSeasonStats(
            games_played=player.games_played,
            ppg=player.ppg,
            rpg=player.rpg,
            apg=player.apg,
            fg_pct=player.fg_pct,
            fg3_pct=player.fg3_pct,
            tpg=player.tpg,
            ts_pct=player.ts_pct,
            per=player.per,
        )

    ovr = player.overall_rating
    gp = random.randint(0, 20)
    return PlayerSeasonStats(
        games_played=gp,
        ppg=round(ovr / 4.5 + random.uniform(-3, 3), 1),
        rpg=round(ovr / 12 + random.uniform(-1, 2), 1),
        apg=round(ovr / 10 + random.uniform(-2, 3), 1),
        fg_pct=round(min(0.6, max(0.38, 0.4 + ovr / 300)), 3),
        fg3_pct=round(min(0.45, max(0.28, 0.3 + ovr / 400)), 3),
        tpg=round(max(0.5, 3.5 - ovr / 30 + random.uniform(-0.5, 0.5)), 1),
        ts_pct=round(min(0.72, max(0.48, 0.45 + ovr / 200)), 3),
        per=round(10 + ovr / 4 + random.uniform(-2, 2), 1),
    )


def get_player_detail(db: Session, player_id: int) -> PlayerDetail | None:
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        return None

    team = db.query(Team).filter(Team.id == player.team_id).first() if player.team_id else None
    history = _ensure_rating_history(db, player)
    rating_history = [
        PlayerRatingPoint(season=h.season, overall_rating=h.overall_rating, potential=h.potential)
        for h in history
    ]

    detail = PlayerDetail.model_validate(player)
    detail.team_name = f"{team.city} {team.name}" if team else "Free Agent"
    detail.team_abbreviation = team.abbreviation if team else "FA"
    detail.season_stats = _ensure_season_stats(player)
    detail.rating_history = rating_history
    return detail


def initialize_player_stats(db: Session, player: Player) -> None:
    """Seed initial season stats for a player."""
    if player.games_played > 0:
        return
    ovr = player.overall_rating
    player.games_played = 0
    player.ppg = round(ovr / 4.5 + random.uniform(-2, 2), 1)
    player.rpg = round(ovr / 12 + random.uniform(-1, 1), 1)
    player.apg = round(ovr / 10 + random.uniform(-1, 2), 1)
    player.fg_pct = round(min(0.6, max(0.38, 0.4 + ovr / 300)), 3)
    player.fg3_pct = round(min(0.45, max(0.28, 0.3 + ovr / 400)), 3)
    player.tpg = round(max(0.5, 3.5 - ovr / 30), 1)
    player.ts_pct = round(min(0.72, max(0.48, 0.45 + ovr / 200)), 3)
    player.per = round(10 + ovr / 4, 1)
    player.player_mood = round(random.uniform(65, 90), 1)
    player.development_trend = (
        "Rising" if player.age < 24 and player.potential > player.overall_rating + 3 else "Stable"
    )
