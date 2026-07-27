"""Team-related business logic."""

from sqlalchemy.orm import Session

from app.models import Player, Team
from app.schemas import TeamDetail, TeamSummary


def list_teams(db: Session) -> list[TeamSummary]:
    teams = db.query(Team).order_by(Team.city).all()
    return [TeamSummary.model_validate(t) for t in teams]


def get_team(db: Session, team_id: int) -> TeamDetail | None:
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        return None
    return TeamDetail.model_validate(team)


def get_team_roster(db: Session, team_id: int) -> list[Player]:
    return (
        db.query(Player)
        .filter(Player.team_id == team_id)
        .order_by(Player.overall_rating.desc())
        .all()
    )
