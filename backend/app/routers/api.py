"""API route handlers."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    AwardSummary,
    CapSheetResponse,
    CareerSaveDetail,
    CareerStatusResponse,
    ContractExtensionRequest,
    CreateCareerRequest,
    DraftPickSummary,
    ExtensionResult,
    FreeAgencyOfferRequest,
    FreeAgentSummary,
    HealthResponse,
    LoadCareerRequest,
    MessageResponse,
    NewsItem,
    OffseasonResponse,
    PlayoffBracket,
    PlayoffSimResponse,
    PlayerDetail,
    PlayerSummary,
    RosterUpdateRequest,
    ScheduleResponse,
    SeedResponse,
    SigningResult,
    SimulationRequest,
    SimulationResponse,
    StandingsResponse,
    TeamAnalytics,
    TeamDetail,
    TeamHubResponse,
    TeamSummary,
    TradeEvaluation,
    TradeInboxItem,
    TradeProposalRequest,
    TradeResult,
)
from app.services.career_service import (
    CareerServiceError,
    create_career,
    delete_career,
    get_active_career,
    list_careers,
    load_career,
)
from app.services.news_service import get_news
from app.services.player_service import get_player_detail
from app.services.roster_service import RosterServiceError, update_roster
from app.services.schedule_service import get_team_schedule
from app.services.seed_service import has_placeholder_rosters, is_database_seeded, refresh_player_contracts, reload_rosters, seed_database
from app.services.simulation_service import SimulationServiceError, simulate
from app.services.standings_service import get_standings
from app.services.team_service import get_team, get_team_roster, list_teams
from app.services.salary_cap_service import get_cap_sheet
from app.services.trade_service import TradeServiceError, evaluate_trade, execute_trade, get_team_picks
from app.services.free_agency_service import FreeAgencyServiceError, get_free_agents, make_offer
from app.services.playoff_service import get_playoff_bracket, simulate_playoff_round
from app.services.offseason_service import process_offseason
from app.services.analytics_service import get_league_analytics, get_team_analytics
from app.services.awards_service import get_awards
from app.services.extension_service import ExtensionServiceError, extend_contract, get_expiring_contracts
from app.services.owner_service import get_status_label
from app.services.trade_inbox_service import get_inbox, respond_to_offer

router = APIRouter()


def _require_active_career(db: Session) -> CareerSaveDetail:
    career = get_active_career(db)
    if not career:
        raise HTTPException(status_code=404, detail="No active career. Start or load a career first.")
    return career


def _career_orm(db: Session, career_detail: CareerSaveDetail):
    from app.models import CareerSave

    career = db.query(CareerSave).filter(CareerSave.id == career_detail.id).first()
    if not career:
        raise HTTPException(status_code=404, detail="Career not found")
    return career


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app="NBA GM Simulator",
        database_seeded=is_database_seeded(db),
        has_placeholder_rosters=has_placeholder_rosters(db),
    )


@router.post("/seed", response_model=SeedResponse)
def seed_data(db: Session = Depends(get_db), force: bool = False) -> SeedResponse:
    result = seed_database(db, force=force)
    return SeedResponse(**result)


@router.post("/seed/salaries", response_model=SeedResponse)
def refresh_salaries(db: Session = Depends(get_db)) -> SeedResponse:
    if not is_database_seeded(db):
        result = seed_database(db)
    elif has_placeholder_rosters(db):
        raise HTTPException(
            status_code=400,
            detail="Placeholder rosters detected. Use Load Real NBA Rosters first — salary refresh cannot fix fake names.",
        )
    else:
        result = refresh_player_contracts(db)
    return SeedResponse(**result)


@router.post("/seed/rosters", response_model=SeedResponse)
def reload_real_rosters(db: Session = Depends(get_db)) -> SeedResponse:
    if not is_database_seeded(db):
        result = seed_database(db)
    else:
        result = reload_rosters(db)
    return SeedResponse(**result)


@router.get("/teams", response_model=list[TeamSummary])
def get_teams(db: Session = Depends(get_db)) -> list[TeamSummary]:
    if not is_database_seeded(db):
        seed_database(db)
    return list_teams(db)


@router.get("/teams/{team_id}", response_model=TeamDetail)
def get_team_by_id(team_id: int, db: Session = Depends(get_db)) -> TeamDetail:
    if not is_database_seeded(db):
        seed_database(db)
    team = get_team(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.get("/teams/{team_id}/roster", response_model=list[PlayerSummary])
def get_roster(team_id: int, db: Session = Depends(get_db)) -> list[PlayerSummary]:
    if not is_database_seeded(db):
        seed_database(db)
    team = get_team(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    roster = get_team_roster(db, team_id)
    return [PlayerSummary.model_validate(p) for p in roster]


@router.get("/players/{player_id}", response_model=PlayerDetail)
def get_player(player_id: int, db: Session = Depends(get_db)) -> PlayerDetail:
    player = get_player_detail(db, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@router.patch("/roster", response_model=list[PlayerSummary])
def patch_roster(payload: RosterUpdateRequest, db: Session = Depends(get_db)) -> list[PlayerSummary]:
    career = _require_active_career(db)
    try:
        roster = update_roster(db, career.team_id, payload)
        return [PlayerSummary.model_validate(p) for p in roster]
    except RosterServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/standings", response_model=StandingsResponse)
def standings(db: Session = Depends(get_db)) -> StandingsResponse:
    career = _require_active_career(db)
    return get_standings(db, career.season, career.id)


@router.get("/schedule", response_model=ScheduleResponse)
def schedule(db: Session = Depends(get_db)) -> ScheduleResponse:
    career = _require_active_career(db)
    from app.models import CareerSave

    career_orm = db.query(CareerSave).filter(CareerSave.id == career.id).first()
    if not career_orm:
        raise HTTPException(status_code=404, detail="Career not found")
    return get_team_schedule(db, career_orm, career.team_id)


@router.get("/news", response_model=list[NewsItem])
def news(db: Session = Depends(get_db), limit: int = 30) -> list[NewsItem]:
    career = get_active_career(db)
    if career:
        return get_news(db, career_id=career.id, limit=limit)
    return get_news(db, limit=limit)


@router.post("/simulation/advance", response_model=SimulationResponse)
def advance_simulation(
    payload: SimulationRequest, db: Session = Depends(get_db)
) -> SimulationResponse:
    from app.models import CareerSave

    career_detail = _require_active_career(db)
    career = db.query(CareerSave).filter(CareerSave.id == career_detail.id).first()
    if not career:
        raise HTTPException(status_code=404, detail="Career not found")
    try:
        return simulate(db, career, payload.mode)
    except SimulationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/careers", response_model=list[CareerSaveDetail])
def get_careers(db: Session = Depends(get_db)) -> list[CareerSaveDetail]:
    return list_careers(db)


@router.get("/careers/active", response_model=CareerSaveDetail | None)
def get_active(db: Session = Depends(get_db)) -> CareerSaveDetail | None:
    return get_active_career(db)


@router.post("/careers", response_model=CareerSaveDetail, status_code=201)
def start_career(payload: CreateCareerRequest, db: Session = Depends(get_db)) -> CareerSaveDetail:
    if not is_database_seeded(db):
        seed_database(db)
    try:
        return create_career(db, payload)
    except CareerServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/careers/load", response_model=CareerSaveDetail)
def load_save(payload: LoadCareerRequest, db: Session = Depends(get_db)) -> CareerSaveDetail:
    try:
        return load_career(db, payload.slot)
    except CareerServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.delete("/careers/{slot}", response_model=MessageResponse)
def remove_save(slot: int, db: Session = Depends(get_db)) -> MessageResponse:
    try:
        delete_career(db, slot)
        return MessageResponse(message=f"Save slot {slot} deleted")
    except CareerServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/hub", response_model=TeamHubResponse)
def get_team_hub(db: Session = Depends(get_db)) -> TeamHubResponse:
    from app.services.career_state_service import sync_active_team_display

    career = get_active_career(db)
    if not career:
        raise HTTPException(status_code=404, detail="No active career. Start or load a career first.")

    sync_active_team_display(db, career.id)

    team = get_team(db, career.team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    roster = get_team_roster(db, career.team_id)
    return TeamHubResponse(
        career=career,
        team=team,
        roster=[PlayerSummary.model_validate(p) for p in roster],
    )


# --- Phase 3 Endpoints ---


@router.get("/cap-sheet", response_model=CapSheetResponse)
def cap_sheet(db: Session = Depends(get_db)) -> CapSheetResponse:
    career = _require_active_career(db)
    return get_cap_sheet(db, career.team_id)


@router.get("/trades/picks", response_model=list[DraftPickSummary])
def my_draft_picks(db: Session = Depends(get_db)) -> list[DraftPickSummary]:
    career = _require_active_career(db)
    picks = get_team_picks(db, career.team_id)
    return [DraftPickSummary.model_validate(p) for p in picks]


@router.post("/trades/evaluate", response_model=TradeEvaluation)
def evaluate_trade_proposal(
    payload: TradeProposalRequest, db: Session = Depends(get_db)
) -> TradeEvaluation:
    career_detail = _require_active_career(db)
    career = _career_orm(db, career_detail)
    try:
        return evaluate_trade(db, career, career_detail.team_id, payload)
    except TradeServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/trades/execute", response_model=TradeResult)
def execute_trade_proposal(
    payload: TradeProposalRequest, db: Session = Depends(get_db)
) -> TradeResult:
    career_detail = _require_active_career(db)
    career = _career_orm(db, career_detail)
    try:
        return execute_trade(db, career, career_detail.team_id, payload)
    except TradeServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/free-agency", response_model=list[FreeAgentSummary])
def free_agents(db: Session = Depends(get_db)) -> list[FreeAgentSummary]:
    _require_active_career(db)
    return get_free_agents(db)


@router.post("/free-agency/offer", response_model=SigningResult)
def free_agency_offer(
    payload: FreeAgencyOfferRequest, db: Session = Depends(get_db)
) -> SigningResult:
    career_detail = _require_active_career(db)
    career = _career_orm(db, career_detail)
    try:
        return make_offer(db, career, career_detail.team_id, payload)
    except FreeAgencyServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/playoffs", response_model=PlayoffBracket)
def playoffs_bracket(db: Session = Depends(get_db)) -> PlayoffBracket:
    career_detail = _require_active_career(db)
    career = _career_orm(db, career_detail)
    return get_playoff_bracket(db, career)


@router.post("/playoffs/simulate", response_model=PlayoffSimResponse)
def simulate_playoffs(db: Session = Depends(get_db)) -> PlayoffSimResponse:
    career_detail = _require_active_career(db)
    career = _career_orm(db, career_detail)
    return simulate_playoff_round(db, career)


@router.post("/offseason/advance", response_model=OffseasonResponse)
def advance_offseason(db: Session = Depends(get_db)) -> OffseasonResponse:
    career_detail = _require_active_career(db)
    career = _career_orm(db, career_detail)
    return process_offseason(db, career)


@router.get("/analytics/team", response_model=TeamAnalytics)
def team_analytics(db: Session = Depends(get_db)) -> TeamAnalytics:
    career = _require_active_career(db)
    return get_team_analytics(db, career.team_id)


@router.get("/analytics/league", response_model=list[TeamAnalytics])
def league_analytics(db: Session = Depends(get_db)) -> list[TeamAnalytics]:
    _require_active_career(db)
    return get_league_analytics(db)


# --- Phase 4 Endpoints ---


@router.get("/career/status", response_model=CareerStatusResponse)
def career_status(db: Session = Depends(get_db)) -> CareerStatusResponse:
    career_detail = _require_active_career(db)
    career = _career_orm(db, career_detail)
    team = get_team(db, career.team_id)
    return CareerStatusResponse(
        job_security=career.job_security,
        job_status=get_status_label(career.job_security),
        owner_expectations=team.owner_expectations if team else "Playoffs",
        phase=career.phase,
    )


@router.get("/trades/inbox", response_model=list[TradeInboxItem])
def trade_inbox(db: Session = Depends(get_db)) -> list[TradeInboxItem]:
    career_detail = _require_active_career(db)
    return get_inbox(db, career_detail.id)


@router.post("/trades/inbox/{offer_id}/respond", response_model=MessageResponse)
def respond_trade_offer(offer_id: int, payload: TradeInboxResponse, db: Session = Depends(get_db)) -> MessageResponse:
    career_detail = _require_active_career(db)
    career = _career_orm(db, career_detail)
    message = respond_to_offer(db, career, offer_id, payload.accept)
    return MessageResponse(message=message)


@router.get("/contracts/expiring", response_model=list[PlayerSummary])
def expiring_contracts(db: Session = Depends(get_db)) -> list[PlayerSummary]:
    career = _require_active_career(db)
    players = get_expiring_contracts(db, career.team_id)
    return [PlayerSummary.model_validate(p) for p in players]


@router.post("/contracts/extend", response_model=ExtensionResult)
def contract_extension(payload: ContractExtensionRequest, db: Session = Depends(get_db)) -> ExtensionResult:
    career_detail = _require_active_career(db)
    career = _career_orm(db, career_detail)
    try:
        return extend_contract(db, career, career_detail.team_id, payload)
    except ExtensionServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/awards", response_model=list[AwardSummary])
def season_awards(db: Session = Depends(get_db), season: str | None = None) -> list[AwardSummary]:
    career_detail = _require_active_career(db)
    awards = get_awards(db, career_detail.id, season or career_detail.season)
    result: list[AwardSummary] = []
    from app.models import Player

    for award in awards:
        summary = AwardSummary.model_validate(award)
        if award.player_id:
            player = db.query(Player).filter(Player.id == award.player_id).first()
            if player:
                summary.player_name = f"{player.first_name} {player.last_name}"
        result.append(summary)
    return result
