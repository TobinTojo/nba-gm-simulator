"""Owner expectations and GM job security."""

from sqlalchemy.orm import Session

from app.models import CareerSave, Team
from app.services.career_state_service import get_record
from app.services.news_service import log_news

EXPECTATION_THRESHOLDS: dict[str, float] = {
    "Lottery": 0.25,
    "Play-In": 0.45,
    "Playoffs": 0.55,
    "Conference Finals": 0.70,
    "Championship": 0.80,
}


def evaluate_job_security(db: Session, career: CareerSave) -> float:
    team = db.query(Team).filter(Team.id == career.team_id).first()
    if not team:
        return career.job_security

    wins, losses = get_record(db, career.id, career.team_id)
    games = max(1, wins + losses)
    win_pct = wins / games
    expected = EXPECTATION_THRESHOLDS.get(team.owner_expectations, 0.45)

    security = career.job_security

    if win_pct >= expected + 0.1:
        security = min(100, security + 3)
    elif win_pct >= expected:
        security = min(100, security + 1)
    elif win_pct >= expected - 0.1:
        security = max(0, security - 2)
    else:
        security = max(0, security - 5)

    career.job_security = round(security, 1)
    db.commit()
    return career.job_security


def on_game_result(db: Session, career: CareerSave, won: bool) -> float:
    if won:
        career.job_security = min(100, career.job_security + 0.5)
    else:
        career.job_security = max(0, career.job_security - 0.8)
    db.commit()
    return career.job_security


def on_playoff_result(db: Session, career: CareerSave, made_playoffs: bool, won_title: bool) -> float:
    if won_title:
        career.job_security = 100
    elif made_playoffs:
        career.job_security = min(100, career.job_security + 10)
    else:
        career.job_security = max(0, career.job_security - 15)
        team = db.query(Team).filter(Team.id == career.team_id).first()
        if team and career.job_security < 30:
            log_news(
                db,
                career.season,
                "owner",
                f"OWNER: {team.city} {team.name} ownership is dissatisfied with progress.",
                career_id=career.id,
            )
    db.commit()
    return career.job_security


def get_status_label(security: float) -> str:
    if security >= 80:
        return "Secure"
    if security >= 60:
        return "Stable"
    if security >= 40:
        return "On Notice"
    if security >= 20:
        return "Hot Seat"
    return "Critical"
