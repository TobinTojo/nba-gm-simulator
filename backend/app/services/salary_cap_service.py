"""Salary cap calculations and transaction validation."""

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Contract, Player, Team
from app.schemas import CapSheetResponse, ContractSummary


def get_active_roster(db: Session, team_id: int) -> list[Player]:
    return (
        db.query(Player)
        .filter(
            Player.team_id == team_id,
            Player.is_g_league.is_(False),
            Player.is_free_agent.is_(False),
        )
        .all()
    )


def calculate_payroll(db: Session, team_id: int) -> float:
    return round(sum(p.salary for p in get_active_roster(db, team_id)), 2)


def sync_team_cap(db: Session, team_id: int) -> Team:
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise ValueError("Team not found")

    payroll = calculate_payroll(db, team_id)
    cap = settings.salary_cap_millions
    tax_line = settings.luxury_tax_line_millions

    team.salary_cap_space = round(cap - payroll, 2)
    team.luxury_tax = round(max(0.0, payroll - tax_line), 2)
    db.commit()
    db.refresh(team)
    return team


def get_cap_sheet(db: Session, team_id: int) -> CapSheetResponse:
    team = sync_team_cap(db, team_id)
    roster = get_active_roster(db, team_id)
    payroll = calculate_payroll(db, team_id)

    contracts: list[ContractSummary] = []
    for player in sorted(roster, key=lambda p: p.salary, reverse=True):
        contract = db.query(Contract).filter(Contract.player_id == player.id).first()
        contracts.append(
            ContractSummary(
                player_id=player.id,
                player_name=f"{player.first_name} {player.last_name}",
                salary=player.salary,
                years_remaining=player.years_remaining,
                has_player_option=contract.has_player_option if contract else False,
                has_team_option=contract.has_team_option if contract else False,
                is_bird_rights=contract.is_bird_rights if contract else False,
            )
        )

    expiring = sum(1 for p in roster if p.years_remaining <= 1)
    dead_money = 0.0  # placeholder for future buyouts

    return CapSheetResponse(
        team_id=team.id,
        team_name=f"{team.city} {team.name}",
        salary_cap=settings.salary_cap_millions,
        luxury_tax_line=settings.luxury_tax_line_millions,
        first_apron=settings.first_apron_millions,
        payroll=payroll,
        cap_space=team.salary_cap_space,
        luxury_tax=team.luxury_tax,
        over_cap=payroll > settings.salary_cap_millions,
        over_tax=payroll > settings.luxury_tax_line_millions,
        roster_count=len(roster),
        expiring_contracts=expiring,
        dead_money=dead_money,
        contracts=contracts,
    )


def validate_signing(db: Session, team_id: int, salary: float) -> tuple[bool, str]:
    sheet = get_cap_sheet(db, team_id)
    if sheet.roster_count >= settings.max_roster_size:
        return False, f"Roster full ({settings.max_roster_size} players max)"
    if salary > sheet.cap_space and sheet.over_cap:
        return False, "Signing would exceed salary cap without available exceptions"
    if salary > sheet.cap_space + 8.0:
        return False, f"Not enough cap space (${sheet.cap_space:.1f}M available)"
    return True, "OK"


def validate_trade_salary(
    db: Session,
    team_a_id: int,
    team_b_id: int,
    outgoing_a: float,
    incoming_a: float,
    outgoing_b: float,
    incoming_b: float,
) -> tuple[bool, str]:
    payroll_a = calculate_payroll(db, team_a_id) - outgoing_a + incoming_a
    payroll_b = calculate_payroll(db, team_b_id) - outgoing_b + incoming_b

    if payroll_a > settings.first_apron_millions + 10:
        return False, "Trade would put team over first apron"
    if payroll_b > settings.first_apron_millions + 10:
        return False, "Trade would put receiving team over first apron"
    return True, "Salary legal"
