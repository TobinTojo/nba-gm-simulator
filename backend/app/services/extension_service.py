"""Contract extensions and option management."""

from sqlalchemy.orm import Session

from app.models import CareerSave, Contract, Player
from app.schemas import ContractExtensionRequest, ExtensionResult
from app.services.news_service import log_news
from app.services.salary_cap_service import sync_team_cap, validate_signing


class ExtensionServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def get_expiring_contracts(db: Session, team_id: int) -> list[Player]:
    return (
        db.query(Player)
        .filter(
            Player.team_id == team_id,
            Player.is_free_agent.is_(False),
            Player.years_remaining <= 1,
        )
        .order_by(Player.overall_rating.desc())
        .all()
    )


def extend_contract(
    db: Session,
    career: CareerSave,
    team_id: int,
    request: ContractExtensionRequest,
) -> ExtensionResult:
    player = db.query(Player).filter(Player.id == request.player_id, Player.team_id == team_id).first()
    if not player:
        raise ExtensionServiceError("Player not on your team", 404)

    valid, msg = validate_signing(db, team_id, request.salary)
    if not valid and player.years_remaining > 0:
        return ExtensionResult(success=False, player_name=f"{player.first_name} {player.last_name}", message=msg)

    # AI acceptance based on offer vs market value
    market = player.overall_rating * 0.4 + 2
    accepted = request.salary >= market * 0.85 and request.years >= 1

    if not accepted:
        return ExtensionResult(
            success=False,
            player_name=f"{player.first_name} {player.last_name}",
            message=f"{player.first_name} {player.last_name} wants ${market:.1f}M+ per year.",
        )

    player.salary = request.salary
    player.years_remaining = request.years

    contract = db.query(Contract).filter(Contract.player_id == player.id).first()
    if contract:
        contract.salary = request.salary
        contract.years_remaining = request.years
        contract.has_player_option = request.include_player_option
        contract.has_team_option = request.include_team_option
    else:
        from app.models import Contract as ContractModel

        db.add(
            ContractModel(
                player_id=player.id,
                team_id=team_id,
                salary=request.salary,
                years_remaining=request.years,
                has_player_option=request.include_player_option,
                has_team_option=request.include_team_option,
            )
        )

    sync_team_cap(db, team_id)
    log_news(
        db,
        career.season,
        "extension",
        f"EXTENSION: {player.first_name} {player.last_name} — {request.years}yr/${request.salary:.1f}M",
        career_id=career.id,
    )
    db.commit()

    return ExtensionResult(
        success=True,
        player_name=f"{player.first_name} {player.last_name}",
        message=f"Extended {player.first_name} {player.last_name}!",
        salary=request.salary,
        years=request.years,
    )


def process_options(db: Session, career: CareerSave) -> list[str]:
    """Exercise or decline options before contract year decrement."""
    events: list[str] = []
    for contract in db.query(Contract).filter(
        Contract.has_player_option.is_(True) | Contract.has_team_option.is_(True)
    ).all():
        player = db.query(Player).filter(Player.id == contract.player_id).first()
        if not player or player.years_remaining != 1:
            continue

        if contract.has_player_option and player.overall_rating > 78:
            player.is_free_agent = True
            player.team_id = None
            player.years_remaining = 0
            events.append(f"{player.first_name} {player.last_name} declined player option — FA")
        elif contract.has_team_option and player.overall_rating < 70:
            player.is_free_agent = True
            player.team_id = None
            player.years_remaining = 0
            events.append(f"Team declined option on {player.first_name} {player.last_name}")

    db.commit()
    return events
