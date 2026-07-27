"""Draft lottery, prospects, and draft night."""

from __future__ import annotations

import random

from sqlalchemy.orm import Session

from app.models import CareerSave, DraftPick, DraftProspect, Player, Team
from app.schemas import DraftBoardResponse, DraftPickResult, DraftProspectSummary
from app.services.news_service import log_news


def _next_season(season: str) -> str:
    start = int(season.split("-")[0])
    return f"{start + 1}-{start + 2}"


def generate_prospects(db: Session, career: CareerSave, count: int = 60) -> None:
    existing = (
        db.query(DraftProspect)
        .filter(DraftProspect.career_id == career.id, DraftProspect.season == _next_season(career.season))
        .count()
    )
    if existing >= count:
        return

    draft_season = _next_season(career.season)
    first_names = ["Cooper", "Dylan", "Matas", "Zaccharie", "Reed", "Rob", "Dalton", "Tyler"]
    last_names = ["Flagg", "Harper", "Buzelis", "Risacher", "Sheppard", "Dillingham", "Knecht", "Smith"]
    positions = ["PG", "SG", "SF", "PF", "C"]
    reports = [
        "Elite two-way potential with high basketball IQ.",
        "Explosive athlete with developing jump shot.",
        "Polished scorer who creates his own offense.",
        "Defensive anchor with limited offensive polish.",
        "High-upside project with great measurables.",
        "Ready-to-contribute floor spacer.",
    ]

    for i in range(count - existing):
        ovr = random.uniform(68, 88)
        pot = min(99, ovr + random.uniform(5, 15))
        db.add(
            DraftProspect(
                career_id=career.id,
                season=draft_season,
                first_name=random.choice(first_names),
                last_name=random.choice(last_names),
                position=random.choice(positions),
                age=random.randint(18, 22),
                height=f"{random.randint(6, 7)}-{random.randint(0, 11)}",
                overall_rating=round(ovr, 1),
                potential=round(pot, 1),
                scouting_report=random.choice(reports),
                combine_score=round(random.uniform(65, 95), 1),
            )
        )
    db.commit()


def run_lottery(db: Session, career: CareerSave) -> list[int]:
    """Return draft order (team ids) for lottery teams."""
    teams = db.query(Team).order_by(Team.wins.asc()).limit(14).all()
    lottery_teams = [t.id for t in teams]
    random.shuffle(lottery_teams)
    rest = [t.id for t in db.query(Team).order_by(Team.wins.asc()).all() if t.id not in lottery_teams]
    order = lottery_teams + rest

    draft_season = _next_season(career.season)
    for i, team_id in enumerate(order, 1):
        pick = (
            db.query(DraftPick)
            .filter(DraftPick.team_id == team_id, DraftPick.season == draft_season, DraftPick.round_number == 1)
            .first()
        )
        if pick:
            pick.pick_number = i

    db.commit()
    return order


def get_draft_board(db: Session, career: CareerSave) -> DraftBoardResponse:
    generate_prospects(db, career)
    draft_season = _next_season(career.season)

    prospects = (
        db.query(DraftProspect)
        .filter(
            DraftProspect.career_id == career.id,
            DraftProspect.season == draft_season,
            DraftProspect.drafted_by_team_id.is_(None),
        )
        .order_by(DraftProspect.overall_rating.desc())
        .all()
    )

    picks = (
        db.query(DraftPick)
        .filter(DraftPick.season == draft_season)
        .order_by(DraftPick.pick_number.nullslast(), DraftPick.round_number)
        .all()
    )

    team_map = {t.id: t for t in db.query(Team).all()}

    return DraftBoardResponse(
        season=draft_season,
        prospects=[
            DraftProspectSummary(
                id=p.id,
                first_name=p.first_name,
                last_name=p.last_name,
                position=p.position,
                age=p.age,
                height=p.height,
                overall_rating=p.overall_rating,
                potential=p.potential,
                scouting_report=p.scouting_report,
                combine_score=p.combine_score,
            )
            for p in prospects
        ],
        team_picks=[
            {
                "pick_id": pick.id,
                "pick_number": pick.pick_number,
                "round": pick.round_number,
                "team": team_map[pick.team_id].abbreviation if pick.team_id in team_map else "?",
                "team_id": pick.team_id,
            }
            for pick in picks
            if pick.pick_number
        ],
    )


def draft_player(
    db: Session,
    career: CareerSave,
    team_id: int,
    prospect_id: int,
    pick_id: int,
) -> DraftPickResult:
    prospect = db.query(DraftProspect).filter(DraftProspect.id == prospect_id).first()
    pick = db.query(DraftPick).filter(DraftPick.id == pick_id, DraftPick.team_id == team_id).first()

    if not prospect or not pick:
        raise ValueError("Invalid prospect or pick")
    if prospect.drafted_by_team_id:
        raise ValueError("Prospect already drafted")

    team = db.query(Team).filter(Team.id == team_id).first()
    player = Player(
        nba_id=800000 + prospect.id,
        team_id=team_id,
        first_name=prospect.first_name,
        last_name=prospect.last_name,
        position=prospect.position,
        age=prospect.age,
        height=prospect.height,
        overall_rating=prospect.overall_rating,
        potential=prospect.potential,
        salary=round(8.0 if pick.round_number == 1 else 2.0, 1),
        years_remaining=4 if pick.round_number == 1 else 2,
        is_starter=False,
        minutes_per_game=12.0,
    )
    db.add(player)
    db.flush()

    prospect.drafted_by_team_id = team_id
    prospect.pick_number = pick.pick_number

    from app.models import Contract

    db.add(
        Contract(
            player_id=player.id,
            team_id=team_id,
            salary=player.salary,
            years_remaining=player.years_remaining,
        )
    )

    log_news(
        db,
        career.season,
        "draft",
        f"DRAFT: {team.abbreviation} selects {prospect.first_name} {prospect.last_name} "
        f"#{pick.pick_number} ({prospect.position}, OVR {prospect.overall_rating:.0f})",
    )
    db.commit()

    return DraftPickResult(
        pick_number=pick.pick_number or 0,
        team_name=f"{team.city} {team.name}",
        player_name=f"{prospect.first_name} {prospect.last_name}",
        position=prospect.position,
        overall_rating=prospect.overall_rating,
    )


def auto_draft_remaining(db: Session, career: CareerSave, user_team_id: int) -> list[DraftPickResult]:
    """AI drafts all remaining picks; user team picks best available when it's their turn."""
    results: list[DraftPickResult] = []
    draft_season = _next_season(career.season)

    undrafted_picks = (
        db.query(DraftPick)
        .filter(DraftPick.season == draft_season, DraftPick.pick_number.isnot(None))
        .order_by(DraftPick.pick_number)
        .all()
    )

    for pick in undrafted_picks:
        already = (
            db.query(DraftProspect)
            .filter(DraftProspect.pick_number == pick.pick_number, DraftProspect.career_id == career.id)
            .first()
        )
        if already:
            continue

        available = (
            db.query(DraftProspect)
            .filter(
                DraftProspect.career_id == career.id,
                DraftProspect.season == draft_season,
                DraftProspect.drafted_by_team_id.is_(None),
            )
            .order_by(DraftProspect.overall_rating.desc())
            .all()
        )
        if not available:
            break

        prospect = available[0]
        try:
            result = draft_player(db, career, pick.team_id, prospect.id, pick.id)
            results.append(result)
        except ValueError:
            continue

    return results
