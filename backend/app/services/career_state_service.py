"""Per-career team win/loss records."""

from sqlalchemy.orm import Session

from app.models import CareerTeamState, Team


def init_career_team_states(db: Session, career_id: int) -> None:
    existing = db.query(CareerTeamState).filter(CareerTeamState.career_id == career_id).count()
    if existing > 0:
        return
    for team in db.query(Team).all():
        db.add(CareerTeamState(career_id=career_id, team_id=team.id, wins=0, losses=0))
    db.commit()


def get_record(db: Session, career_id: int, team_id: int) -> tuple[int, int]:
    state = (
        db.query(CareerTeamState)
        .filter(CareerTeamState.career_id == career_id, CareerTeamState.team_id == team_id)
        .first()
    )
    if not state:
        init_career_team_states(db, career_id)
        state = (
            db.query(CareerTeamState)
            .filter(CareerTeamState.career_id == career_id, CareerTeamState.team_id == team_id)
            .first()
        )
    return (state.wins, state.losses) if state else (0, 0)


def apply_game_result(db: Session, career_id: int, home_id: int, away_id: int, home_won: bool) -> None:
    home = (
        db.query(CareerTeamState)
        .filter(CareerTeamState.career_id == career_id, CareerTeamState.team_id == home_id)
        .first()
    )
    away = (
        db.query(CareerTeamState)
        .filter(CareerTeamState.career_id == career_id, CareerTeamState.team_id == away_id)
        .first()
    )
    if not home or not away:
        init_career_team_states(db, career_id)
        return apply_game_result(db, career_id, home_id, away_id, home_won)

    if home_won:
        home.wins += 1
        away.losses += 1
    else:
        away.wins += 1
        home.losses += 1


def reset_career_records(db: Session, career_id: int) -> None:
    for state in db.query(CareerTeamState).filter(CareerTeamState.career_id == career_id).all():
        state.wins = 0
        state.losses = 0
    db.commit()


def sync_active_team_display(db: Session, career_id: int) -> None:
    """Copy career records onto Team rows for hub display compatibility."""
    for state in db.query(CareerTeamState).filter(CareerTeamState.career_id == career_id).all():
        team = db.query(Team).filter(Team.id == state.team_id).first()
        if team:
            team.wins = state.wins
            team.losses = state.losses
    db.commit()
