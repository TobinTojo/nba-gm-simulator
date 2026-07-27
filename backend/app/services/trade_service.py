"""Trade proposal evaluation and execution."""

from __future__ import annotations

import random
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import CareerSave, Contract, DraftPick, Player, Team
from app.schemas import TradeAsset, TradeEvaluation, TradeProposalRequest, TradeResult
from app.services.news_service import log_news
from app.services.salary_cap_service import calculate_payroll, sync_team_cap, validate_trade_salary


class TradeServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


@dataclass
class TradeSide:
    player_ids: list[int]
    pick_ids: list[int]


def _player_value(player: Player) -> float:
    age_factor = 1.1 if player.age < 25 else (0.9 if player.age > 32 else 1.0)
    pot_bonus = max(0, (player.potential - player.overall_rating) * 0.3)
    return (player.overall_rating + pot_bonus) * age_factor


def _pick_value(pick: DraftPick) -> float:
    base = 75.0 if pick.round_number == 1 else 45.0
    if pick.pick_number:
        return max(20.0, base - pick.pick_number * 0.5)
    return base


def _side_value(db: Session, player_ids: list[int], pick_ids: list[int]) -> float:
    total = 0.0
    for pid in player_ids:
        player = db.query(Player).filter(Player.id == pid).first()
        if player:
            total += _player_value(player)
    for pick_id in pick_ids:
        pick = db.query(DraftPick).filter(DraftPick.id == pick_id).first()
        if pick:
            total += _pick_value(pick)
    return total


def evaluate_trade(
    db: Session,
    career: CareerSave,
    user_team_id: int,
    request: TradeProposalRequest,
) -> TradeEvaluation:
    partner = db.query(Team).filter(Team.id == request.partner_team_id).first()
    if not partner:
        raise TradeServiceError("Partner team not found", 404)

    user_side = TradeSide(request.send_player_ids, request.send_pick_ids)
    partner_side = TradeSide(request.receive_player_ids, request.receive_pick_ids)

    if not user_side.player_ids and not user_side.pick_ids:
        raise TradeServiceError("Must send at least one asset")
    if not partner_side.player_ids and not partner_side.pick_ids:
        raise TradeServiceError("Must request at least one asset in return")

    # Validate ownership
    for pid in user_side.player_ids:
        p = db.query(Player).filter(Player.id == pid, Player.team_id == user_team_id).first()
        if not p:
            raise TradeServiceError(f"Player {pid} not on your roster")
    for pid in partner_side.player_ids:
        p = db.query(Player).filter(Player.id == pid, Player.team_id == partner.id).first()
        if not p:
            raise TradeServiceError(f"Player {pid} not on {partner.abbreviation}")

    user_value = _side_value(db, user_side.player_ids, user_side.pick_ids)
    partner_value = _side_value(db, partner_side.player_ids, partner_side.pick_ids)

    fairness = round(min(user_value, partner_value) / max(user_value, partner_value, 1) * 100, 1)

    outgoing_salary = sum(
        db.query(Player).filter(Player.id == pid).first().salary
        for pid in user_side.player_ids
        if db.query(Player).filter(Player.id == pid).first()
    )
    incoming_salary = sum(
        db.query(Player).filter(Player.id == pid).first().salary
        for pid in partner_side.player_ids
        if db.query(Player).filter(Player.id == pid).first()
    )
    partner_out = sum(
        db.query(Player).filter(Player.id == pid).first().salary
        for pid in partner_side.player_ids
        if db.query(Player).filter(Player.id == pid).first()
    )
    partner_in = outgoing_salary

    salary_ok, salary_msg = validate_trade_salary(
        db, user_team_id, partner.id, outgoing_salary, incoming_salary, partner_out, partner_in
    )

    user_team = db.query(Team).filter(Team.id == user_team_id).first()
    team_direction = "win_now" if user_team and user_team.overall_rating >= 82 else "rebuild"
    avg_age_out = 0.0
    if user_side.player_ids:
        ages = [db.query(Player).filter(Player.id == pid).first().age for pid in user_side.player_ids]
        avg_age_out = sum(ages) / len(ages)

    fit_score = 70.0
    if team_direction == "win_now" and avg_age_out < 26:
        fit_score -= 15
    if team_direction == "rebuild" and avg_age_out > 30:
        fit_score -= 10

    reasons: list[str] = []
    if fairness < 85:
        reasons.append(f"Value imbalance ({fairness}% fair)")
    if not salary_ok:
        reasons.append(salary_msg)
    if fit_score < 60:
        reasons.append("Poor roster fit for partner's timeline")

    # AI acceptance logic
    accept_threshold = 82 if partner.overall_rating >= 80 else 78
    if partner.id == user_team_id:
        accept_threshold = 100  # can't trade with self

    random_factor = random.uniform(-5, 5)
    ai_score = fairness * 0.5 + fit_score * 0.3 + (100 if salary_ok else 0) * 0.2 + random_factor
    accepted = ai_score >= accept_threshold and salary_ok and fairness >= 70

    if accepted:
        reason = f"{partner.city} {partner.name} accepts the trade."
    elif not salary_ok:
        reason = f"Rejected: {salary_msg}"
    elif fairness < 70:
        reason = f"Rejected: Offer too lopsided ({fairness}% fairness)."
    else:
        reason = f"Rejected: {partner.abbreviation} wants more value for their core players."

    send_assets = [
        TradeAsset(type="player", id=pid, label=_player_label(db, pid))
        for pid in user_side.player_ids
    ] + [
        TradeAsset(type="pick", id=pick_id, label=_pick_label(db, pick_id))
        for pick_id in user_side.pick_ids
    ]
    receive_assets = [
        TradeAsset(type="player", id=pid, label=_player_label(db, pid))
        for pid in partner_side.player_ids
    ] + [
        TradeAsset(type="pick", id=pick_id, label=_pick_label(db, pick_id))
        for pick_id in partner_side.pick_ids
    ]

    return TradeEvaluation(
        partner_team_id=partner.id,
        partner_team_name=f"{partner.city} {partner.name}",
        send_assets=send_assets,
        receive_assets=receive_assets,
        fairness_score=fairness,
        salary_legal=salary_ok,
        roster_fit_score=round(fit_score, 1),
        value_gained=round(partner_value - user_value, 1),
        accepted=accepted,
        reason=reason,
    )


def _player_label(db: Session, player_id: int) -> str:
    p = db.query(Player).filter(Player.id == player_id).first()
    return f"{p.first_name} {p.last_name}" if p else f"Player {player_id}"


def _pick_label(db: Session, pick_id: int) -> str:
    pick = db.query(DraftPick).filter(DraftPick.id == pick_id).first()
    if not pick:
        return f"Pick {pick_id}"
    return f"{pick.season} Round {pick.round_number}"


def execute_trade(
    db: Session,
    career: CareerSave,
    user_team_id: int,
    request: TradeProposalRequest,
) -> TradeResult:
    evaluation = evaluate_trade(db, career, user_team_id, request)
    if not evaluation.accepted:
        return TradeResult(success=False, evaluation=evaluation, message=evaluation.reason)

    partner_id = request.partner_team_id

    for pid in request.send_player_ids:
        player = db.query(Player).filter(Player.id == pid).first()
        if player:
            player.team_id = partner_id
            player.is_starter = False
            contract = db.query(Contract).filter(Contract.player_id == pid).first()
            if contract:
                contract.team_id = partner_id

    for pid in request.receive_player_ids:
        player = db.query(Player).filter(Player.id == pid).first()
        if player:
            player.team_id = user_team_id
            player.is_starter = False
            contract = db.query(Contract).filter(Contract.player_id == pid).first()
            if contract:
                contract.team_id = user_team_id

    for pick_id in request.send_pick_ids:
        pick = db.query(DraftPick).filter(DraftPick.id == pick_id).first()
        if pick:
            pick.team_id = partner_id

    for pick_id in request.receive_pick_ids:
        pick = db.query(DraftPick).filter(DraftPick.id == pick_id).first()
        if pick:
            pick.team_id = user_team_id

    sync_team_cap(db, user_team_id)
    sync_team_cap(db, partner_id)

    partner = db.query(Team).filter(Team.id == partner_id).first()
    desc = (
        f"TRADE: {evaluation.send_assets[0].label if evaluation.send_assets else 'Assets'} "
        f"to {partner.abbreviation} for "
        f"{evaluation.receive_assets[0].label if evaluation.receive_assets else 'Assets'}"
    )
    log_news(db, career.season, "trade", desc, career_id=career.id)

    db.commit()
    return TradeResult(success=True, evaluation=evaluation, message="Trade completed successfully!")


def get_team_picks(db: Session, team_id: int) -> list[DraftPick]:
    return (
        db.query(DraftPick)
        .filter(DraftPick.team_id == team_id)
        .order_by(DraftPick.season, DraftPick.round_number)
        .all()
    )
