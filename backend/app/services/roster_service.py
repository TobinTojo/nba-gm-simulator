"""Roster management business logic."""

from sqlalchemy.orm import Session

from app.models import Player
from app.schemas import RosterPlayerUpdate, RosterUpdateRequest


class RosterServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def update_roster(db: Session, team_id: int, payload: RosterUpdateRequest) -> list[Player]:
    roster = db.query(Player).filter(Player.team_id == team_id).all()
    roster_ids = {p.id for p in roster}
    updates_by_id = {u.player_id: u for u in payload.players}

    for player_id in updates_by_id:
        if player_id not in roster_ids:
            raise RosterServiceError(f"Player {player_id} is not on this team")

    starter_count = sum(1 for u in payload.players if u.is_starter)
    if starter_count > 5:
        raise RosterServiceError("Cannot have more than 5 starters")

    for player in roster:
        update = updates_by_id.get(player.id)
        if not update:
            continue
        player.is_starter = update.is_starter
        player.minutes_per_game = max(0.0, min(48.0, update.minutes_per_game))
        player.is_g_league = update.is_g_league
        if update.is_g_league:
            player.is_starter = False
            player.minutes_per_game = 0.0

    db.commit()
    return (
        db.query(Player)
        .filter(Player.team_id == team_id)
        .order_by(Player.overall_rating.desc())
        .all()
    )


def set_starter(db: Session, team_id: int, player_id: int, is_starter: bool) -> Player:
    player = db.query(Player).filter(Player.id == player_id, Player.team_id == team_id).first()
    if not player:
        raise RosterServiceError("Player not found on team", 404)

    if is_starter:
        starters = (
            db.query(Player)
            .filter(Player.team_id == team_id, Player.is_starter.is_(True), Player.id != player_id)
            .count()
        )
        if starters >= 5:
            raise RosterServiceError("Already have 5 starters")

    player.is_starter = is_starter
    if is_starter and player.minutes_per_game < 20:
        player.minutes_per_game = 28.0
    db.commit()
    db.refresh(player)
    return player
