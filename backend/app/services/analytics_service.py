"""Team advanced analytics calculations."""

from sqlalchemy.orm import Session

from app.models import Player, Team
from app.schemas import TeamAnalytics


def _offensive_rating(players: list[Player]) -> float:
    if not players:
        return 110.0
    weights = [p.minutes_per_game for p in players]
    total = sum(weights) or 1
    score = sum(
        (p.shooting * 0.35 + p.playmaking * 0.25 + p.athleticism * 0.15 + p.basketball_iq * 0.25)
        * (w / total)
        for p, w in zip(players, weights)
    )
    return round(105 + (score - 75) * 0.4, 1)


def _defensive_rating(players: list[Player]) -> float:
    if not players:
        return 110.0
    weights = [p.minutes_per_game for p in players]
    total = sum(weights) or 1
    score = sum(
        (p.defense * 0.45 + p.rebounding * 0.25 + p.athleticism * 0.15 + p.basketball_iq * 0.15)
        * (w / total)
        for p, w in zip(players, weights)
    )
    return round(115 - (score - 75) * 0.4, 1)


def get_team_analytics(db: Session, team_id: int) -> TeamAnalytics:
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise ValueError("Team not found")

    players = (
        db.query(Player)
        .filter(Player.team_id == team_id, Player.is_g_league.is_(False), Player.is_free_agent.is_(False))
        .order_by(Player.minutes_per_game.desc())
        .limit(10)
        .all()
    )

    ortg = _offensive_rating(players)
    drtg = _defensive_rating(players)
    net = round(ortg - drtg, 1)
    pace = round(98 + (sum(p.athleticism for p in players) / max(1, len(players)) - 75) * 0.15, 1)

    avg_ts = sum(p.ts_pct for p in players) / max(1, len(players))
    efg = round(avg_ts * 0.92, 3)

    reb_pct = round(50 + (sum(p.rebounding for p in players) / max(1, len(players)) - 75) * 0.3, 1)
    tov_pct = round(15 - (sum(p.playmaking for p in players) / max(1, len(players)) - 75) * 0.08, 1)

    pie = round(sum(p.per for p in players) / max(1, len(players)), 1)

    return TeamAnalytics(
        team_id=team.id,
        team_name=f"{team.city} {team.name}",
        offensive_rating=ortg,
        defensive_rating=drtg,
        net_rating=net,
        pace=pace,
        true_shooting_pct=round(avg_ts, 3),
        effective_fg_pct=efg,
        rebounding_pct=reb_pct,
        turnover_pct=tov_pct,
        player_impact_estimate=pie,
        wins=team.wins,
        losses=team.losses,
    )


def get_league_analytics(db: Session) -> list[TeamAnalytics]:
    teams = db.query(Team).order_by(Team.wins.desc()).all()
    return [get_team_analytics(db, t.id) for t in teams]
