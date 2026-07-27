"""AI-initiated trade offers and rumors."""

from __future__ import annotations

import json
import random

from sqlalchemy.orm import Session

from app.models import CareerSave, Player, Team, TradeOffer
from app.schemas import TradeInboxItem, TradeProposalRequest
from app.services.news_service import log_news
from app.services.trade_service import evaluate_trade, execute_trade


def _parse_ids(raw: str) -> list[int]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def _serialize_ids(ids: list[int]) -> str:
    return json.dumps(ids)


def generate_trade_rumors(db: Session, career: CareerSave) -> None:
    if random.random() > 0.25:
        return

    teams = db.query(Team).filter(Team.id != career.team_id).all()
    if not teams:
        return

    team = random.choice(teams)
    player = (
        db.query(Player)
        .filter(Player.team_id == team.id)
        .order_by(Player.overall_rating.desc())
        .first()
    )
    if not player:
        return

    log_news(
        db,
        career.season,
        "rumor",
        f"RUMOR: {team.abbreviation} listening to offers for {player.first_name} {player.last_name}.",
        career_id=career.id,
    )


def generate_ai_trade_offer(db: Session, career: CareerSave) -> TradeOffer | None:
    if random.random() > 0.15:
        return None

    ai_team = db.query(Team).filter(Team.id != career.team_id).order_by(Team.overall_rating.desc()).first()
    if not ai_team:
        return None

    ai_players = (
        db.query(Player)
        .filter(Player.team_id == ai_team.id)
        .order_by(Player.overall_rating.desc())
        .limit(5)
        .all()
    )
    user_players = (
        db.query(Player)
        .filter(Player.team_id == career.team_id)
        .order_by(Player.overall_rating.asc())
        .limit(5)
        .all()
    )
    if not ai_players or not user_players:
        return None

    send_player = random.choice(ai_players[:3])
    receive_player = random.choice(user_players[:3])

    offer = TradeOffer(
        career_id=career.id,
        from_team_id=ai_team.id,
        to_team_id=career.team_id,
        send_player_ids=_serialize_ids([send_player.id]),
        receive_player_ids=_serialize_ids([receive_player.id]),
        message=f"{ai_team.city} {ai_team.name} offer {send_player.first_name} {send_player.last_name} for {receive_player.first_name} {receive_player.last_name}.",
        is_rumor=False,
    )
    db.add(offer)
    log_news(
        db,
        career.season,
        "trade",
        f"TRADE OFFER: {offer.message}",
        career_id=career.id,
    )
    db.commit()
    return offer


def get_inbox(db: Session, career_id: int) -> list[TradeInboxItem]:
    offers = (
        db.query(TradeOffer)
        .filter(TradeOffer.career_id == career_id, TradeOffer.status == "pending")
        .order_by(TradeOffer.created_at.desc())
        .all()
    )
    items: list[TradeInboxItem] = []
    for offer in offers:
        from_team = db.query(Team).filter(Team.id == offer.from_team_id).first()
        items.append(
            TradeInboxItem(
                id=offer.id,
                from_team_name=f"{from_team.city} {from_team.name}" if from_team else "Unknown",
                message=offer.message,
                send_player_ids=_parse_ids(offer.send_player_ids),
                receive_player_ids=_parse_ids(offer.receive_player_ids),
                is_rumor=offer.is_rumor,
                created_at=offer.created_at,
            )
        )
    return items


def respond_to_offer(db: Session, career: CareerSave, offer_id: int, accept: bool) -> str:
    offer = (
        db.query(TradeOffer)
        .filter(TradeOffer.id == offer_id, TradeOffer.career_id == career.id, TradeOffer.status == "pending")
        .first()
    )
    if not offer:
        return "Offer not found"

    if not accept:
        offer.status = "rejected"
        db.commit()
        return "Trade offer rejected."

    request = TradeProposalRequest(
        partner_team_id=offer.from_team_id,
        send_player_ids=_parse_ids(offer.receive_player_ids),
        receive_player_ids=_parse_ids(offer.send_player_ids),
        send_pick_ids=_parse_ids(offer.receive_pick_ids),
        receive_pick_ids=_parse_ids(offer.send_pick_ids),
    )
    result = execute_trade(db, career, career.team_id, request)
    offer.status = "accepted" if result.success else "rejected"
    db.commit()
    return result.message
