"""League standings business logic."""

from sqlalchemy.orm import Session

from app.models import CareerTeamState, Team
from app.schemas import StandingsEntry, StandingsResponse
from app.services.career_state_service import init_career_team_states


def get_standings(db: Session, season: str, career_id: int | None = None) -> StandingsResponse:
    if career_id:
        init_career_team_states(db, career_id)

    teams = db.query(Team).all()
    state_map: dict[int, CareerTeamState] = {}
    if career_id:
        states = db.query(CareerTeamState).filter(CareerTeamState.career_id == career_id).all()
        state_map = {s.team_id: s for s in states}

    east: list[StandingsEntry] = []
    west: list[StandingsEntry] = []

    for team in teams:
        if career_id and team.id in state_map:
            wins, losses = state_map[team.id].wins, state_map[team.id].losses
        else:
            wins, losses = team.wins, team.losses

        entry = StandingsEntry(
            team_id=team.id,
            abbreviation=team.abbreviation,
            city=team.city,
            name=team.name,
            conference=team.conference,
            division=team.division,
            wins=wins,
            losses=losses,
            win_pct=round(wins / max(1, wins + losses), 3),
            overall_rating=team.overall_rating,
        )
        if team.conference == "East":
            east.append(entry)
        else:
            west.append(entry)

    east.sort(key=lambda t: (t.wins, t.overall_rating), reverse=True)
    west.sort(key=lambda t: (t.wins, t.overall_rating), reverse=True)

    for i, entry in enumerate(east, 1):
        entry.seed = i
    for i, entry in enumerate(west, 1):
        entry.seed = i

    return StandingsResponse(season=season, east=east, west=west)
