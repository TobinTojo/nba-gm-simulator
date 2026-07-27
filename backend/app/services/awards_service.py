"""End-of-season awards calculation."""

import random

from sqlalchemy.orm import Session

from app.models import Award, CareerSave, Player, Team
from app.services.analytics_service import get_team_analytics
from app.services.news_service import log_news


def compute_season_awards(db: Session, career: CareerSave) -> list[Award]:
    existing = (
        db.query(Award)
        .filter(Award.career_id == career.id, Award.season == career.season)
        .count()
    )
    if existing > 0:
        return db.query(Award).filter(Award.career_id == career.id, Award.season == career.season).all()

    players = (
        db.query(Player)
        .filter(Player.team_id.isnot(None), Player.is_free_agent.is_(False), Player.games_played > 0)
        .all()
    )
    if not players:
        return []

    awards: list[Award] = []

    # MVP — PER + team success
    mvp_scores = []
    for p in players:
        team = db.query(Team).filter(Team.id == p.team_id).first()
        team_factor = (team.wins / max(1, team.wins + team.losses)) if team else 0.5
        score = p.per * 2 + p.ppg + team_factor * 20
        mvp_scores.append((p, score))
    mvp = max(mvp_scores, key=lambda x: x[1])[0]
    awards.append(
        Award(career_id=career.id, season=career.season, award_type="MVP", player_id=mvp.id, team_id=mvp.team_id)
    )

    # DPOY — defense rating + team DRtg proxy
    dpoy_scores = []
    for p in players:
        if p.team_id:
            try:
                analytics = get_team_analytics(db, p.team_id)
                drtg_bonus = max(0, 120 - analytics.defensive_rating)
            except ValueError:
                drtg_bonus = 0
        else:
            drtg_bonus = 0
        score = p.defense * 1.2 + drtg_bonus + p.rpg
        dpoy_scores.append((p, score))
    dpoy = max(dpoy_scores, key=lambda x: x[1])[0]
    awards.append(
        Award(career_id=career.id, season=career.season, award_type="DPOY", player_id=dpoy.id, team_id=dpoy.team_id)
    )

    # All-NBA (top 5)
    all_nba = sorted(mvp_scores, key=lambda x: x[1], reverse=True)[:5]
    for i, (p, _) in enumerate(all_nba, 1):
        awards.append(
            Award(
                career_id=career.id,
                season=career.season,
                award_type=f"All-NBA {i}",
                player_id=p.id,
                team_id=p.team_id,
            )
        )

    for award in awards:
        db.add(award)
        player = db.query(Player).filter(Player.id == award.player_id).first()
        if player:
            log_news(
                db,
                career.season,
                "awards",
                f"AWARD: {player.first_name} {player.last_name} — {award.award_type} ({career.season})",
                career_id=career.id,
            )

    db.commit()
    return awards


def get_awards(db: Session, career_id: int, season: str | None = None) -> list[Award]:
    query = db.query(Award).filter(Award.career_id == career_id)
    if season:
        query = query.filter(Award.season == season)
    return query.order_by(Award.award_type).all()
