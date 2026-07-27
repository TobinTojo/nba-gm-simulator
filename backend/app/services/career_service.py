"""Career save and load business logic."""

from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import (
    Award,
    CareerSave,
    CareerTeamState,
    DraftProspect,
    FreeAgentOffer,
    Game,
    Player,
    SeasonResult,
    Team,
    TradeOffer,
    Transaction,
)
from app.schemas import CareerSaveDetail, CreateCareerRequest
from app.services.player_service import initialize_player_stats
from app.services.schedule_service import ensure_career_schedule
from app.services.news_service import log_news
from app.services.career_state_service import init_career_team_states, sync_active_team_display

SINGLE_SAVE_SLOT = 1


class CareerServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _delete_career_data(db: Session, career_id: int) -> None:
    db.query(TradeOffer).filter(TradeOffer.career_id == career_id).delete(synchronize_session=False)
    db.query(FreeAgentOffer).filter(FreeAgentOffer.career_id == career_id).delete(synchronize_session=False)
    db.query(DraftProspect).filter(DraftProspect.career_id == career_id).delete(synchronize_session=False)
    db.query(CareerTeamState).filter(CareerTeamState.career_id == career_id).delete(synchronize_session=False)
    db.query(Game).filter(Game.career_id == career_id).delete(synchronize_session=False)
    db.query(Transaction).filter(Transaction.career_id == career_id).delete(synchronize_session=False)
    db.query(Award).filter(Award.career_id == career_id).delete(synchronize_session=False)
    db.query(SeasonResult).filter(SeasonResult.career_id == career_id).delete(synchronize_session=False)


def _purge_all_careers(db: Session) -> None:
    for career in list(db.query(CareerSave).all()):
        _delete_career_data(db, career.id)
        db.delete(career)
    db.flush()


def reset_league_for_new_career(db: Session) -> None:
    """Delete every career save and restore NBA rosters to baseline."""
    from app.services.seed_service import reload_rosters

    _purge_all_careers(db)
    db.commit()
    reload_rosters(db)


def list_careers(db: Session) -> list[CareerSaveDetail]:
    careers = (
        db.query(CareerSave)
        .options(joinedload(CareerSave.team))
        .order_by(CareerSave.updated_at.desc())
        .all()
    )
    return [CareerSaveDetail.model_validate(c) for c in careers]


def get_active_career(db: Session) -> CareerSaveDetail | None:
    career = (
        db.query(CareerSave)
        .options(joinedload(CareerSave.team))
        .filter(CareerSave.is_active.is_(True))
        .order_by(CareerSave.updated_at.desc())
        .first()
    )
    if not career:
        return None
    return CareerSaveDetail.model_validate(career)


def create_career(db: Session, payload: CreateCareerRequest) -> CareerSaveDetail:
    team = db.query(Team).filter(Team.id == payload.team_id).first()
    if not team:
        raise CareerServiceError("Team not found", 404)

    from app.services.seed_service import has_placeholder_rosters

    if has_placeholder_rosters(db):
        raise CareerServiceError(
            "Placeholder rosters detected. Go to Settings → Load Real NBA Rosters before starting a career.",
            400,
        )

    reset_league_for_new_career(db)

    if db.query(CareerSave).filter(CareerSave.slot == SINGLE_SAVE_SLOT).first():
        _purge_all_careers(db)
        db.commit()

    career = CareerSave(
        slot=SINGLE_SAVE_SLOT,
        name=payload.career_name,
        team_id=team.id,
        season=settings.current_season,
        season_day=1,
        is_active=True,
    )
    db.add(career)
    db.commit()
    db.refresh(career)

    roster = db.query(Player).filter(Player.team_id == team.id).all()
    for player in roster:
        initialize_player_stats(db, player)
    db.commit()

    ensure_career_schedule(db, career)
    init_career_team_states(db, career.id)
    sync_active_team_display(db, career.id)
    log_news(
        db,
        career.season,
        "career",
        f"New career started: {payload.career_name} takes over the {team.city} {team.name}.",
        career_id=career.id,
    )

    career = (
        db.query(CareerSave)
        .options(joinedload(CareerSave.team))
        .filter(CareerSave.id == career.id)
        .one()
    )
    return CareerSaveDetail.model_validate(career)


def load_career(db: Session, slot: int = SINGLE_SAVE_SLOT) -> CareerSaveDetail:
    career = (
        db.query(CareerSave)
        .options(joinedload(CareerSave.team))
        .filter(CareerSave.slot == slot)
        .first()
    )
    if not career:
        raise CareerServiceError("No saved career found. Start a new career first.", 404)

    db.query(CareerSave).filter(CareerSave.is_active.is_(True)).update({"is_active": False})
    career.is_active = True
    db.commit()
    db.refresh(career)

    ensure_career_schedule(db, career)
    sync_active_team_display(db, career.id)

    career = (
        db.query(CareerSave)
        .options(joinedload(CareerSave.team))
        .filter(CareerSave.id == career.id)
        .one()
    )
    return CareerSaveDetail.model_validate(career)


def delete_career(db: Session, slot: int = SINGLE_SAVE_SLOT) -> None:
    career = db.query(CareerSave).filter(CareerSave.slot == slot).first()
    if not career:
        raise CareerServiceError("No saved career found.", 404)
    reset_league_for_new_career(db)
