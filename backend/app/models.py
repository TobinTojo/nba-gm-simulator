"""SQLAlchemy ORM models."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nba_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    abbreviation: Mapped[str] = mapped_column(String(5), index=True)
    city: Mapped[str] = mapped_column(String(80))
    conference: Mapped[str] = mapped_column(String(10))
    division: Mapped[str] = mapped_column(String(20))
    overall_rating: Mapped[float] = mapped_column(Float, default=75.0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    salary_cap_space: Mapped[float] = mapped_column(Float, default=0.0)
    luxury_tax: Mapped[float] = mapped_column(Float, default=0.0)
    young_core_rating: Mapped[str] = mapped_column(String(5), default="C")
    draft_assets_score: Mapped[int] = mapped_column(Integer, default=50)
    championship_window: Mapped[str] = mapped_column(String(30), default="Unknown")
    difficulty_rating: Mapped[int] = mapped_column(Integer, default=3)
    chemistry: Mapped[float] = mapped_column(Float, default=75.0)
    fan_happiness: Mapped[float] = mapped_column(Float, default=70.0)
    owner_expectations: Mapped[str] = mapped_column(String(30), default="Playoffs")
    coach_philosophy: Mapped[str] = mapped_column(String(50), default="Balanced")
    championship_odds: Mapped[float] = mapped_column(Float, default=0.02)
    playoff_odds: Mapped[float] = mapped_column(Float, default=0.35)

    players: Mapped[list["Player"]] = relationship(back_populates="team")
    careers: Mapped[list["CareerSave"]] = relationship(back_populates="team")


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nba_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    position: Mapped[str] = mapped_column(String(10), default="SF")
    age: Mapped[int] = mapped_column(Integer, default=25)
    height: Mapped[str] = mapped_column(String(10), default="6-6")
    weight: Mapped[int] = mapped_column(Integer, default=200)
    overall_rating: Mapped[float] = mapped_column(Float, default=70.0)
    potential: Mapped[float] = mapped_column(Float, default=75.0)
    salary: Mapped[float] = mapped_column(Float, default=0.0)
    years_remaining: Mapped[int] = mapped_column(Integer, default=1)
    is_starter: Mapped[bool] = mapped_column(Boolean, default=False)
    minutes_per_game: Mapped[float] = mapped_column(Float, default=20.0)
    is_g_league: Mapped[bool] = mapped_column(Boolean, default=False)

    shooting: Mapped[float] = mapped_column(Float, default=70.0)
    defense: Mapped[float] = mapped_column(Float, default=70.0)
    playmaking: Mapped[float] = mapped_column(Float, default=70.0)
    athleticism: Mapped[float] = mapped_column(Float, default=70.0)
    rebounding: Mapped[float] = mapped_column(Float, default=70.0)
    basketball_iq: Mapped[float] = mapped_column(Float, default=70.0)
    durability: Mapped[float] = mapped_column(Float, default=80.0)

    player_mood: Mapped[float] = mapped_column(Float, default=75.0)
    fatigue: Mapped[float] = mapped_column(Float, default=0.0)
    injury_status: Mapped[str] = mapped_column(String(30), default="Healthy")
    development_trend: Mapped[str] = mapped_column(String(20), default="Stable")

    games_played: Mapped[int] = mapped_column(Integer, default=0)
    ppg: Mapped[float] = mapped_column(Float, default=0.0)
    rpg: Mapped[float] = mapped_column(Float, default=0.0)
    apg: Mapped[float] = mapped_column(Float, default=0.0)
    ts_pct: Mapped[float] = mapped_column(Float, default=0.55)
    fg_pct: Mapped[float] = mapped_column(Float, default=0.45)
    fg3_pct: Mapped[float] = mapped_column(Float, default=0.35)
    tpg: Mapped[float] = mapped_column(Float, default=0.0)
    per: Mapped[float] = mapped_column(Float, default=15.0)
    is_free_agent: Mapped[bool] = mapped_column(Boolean, default=False)

    team: Mapped["Team | None"] = relationship(back_populates="players")


class CareerSave(Base):
    __tablename__ = "career_saves"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    slot: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(120))
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    season: Mapped[str] = mapped_column(String(10), default="2025-26")
    season_day: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    save_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    phase: Mapped[str] = mapped_column(String(30), default="regular_season")
    job_security: Mapped[float] = mapped_column(Float, default=75.0)

    team: Mapped["Team"] = relationship(back_populates="careers")

    __table_args__ = (UniqueConstraint("slot", name="uq_career_slot"),)


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), unique=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    salary: Mapped[float] = mapped_column(Float, default=0.0)
    years_remaining: Mapped[int] = mapped_column(Integer, default=1)
    has_player_option: Mapped[bool] = mapped_column(Boolean, default=False)
    has_team_option: Mapped[bool] = mapped_column(Boolean, default=False)
    is_bird_rights: Mapped[bool] = mapped_column(Boolean, default=False)


class DraftPick(Base):
    __tablename__ = "draft_picks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    season: Mapped[str] = mapped_column(String(10))
    round_number: Mapped[int] = mapped_column(Integer)
    pick_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    original_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    is_protected: Mapped[bool] = mapped_column(Boolean, default=False)


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season: Mapped[str] = mapped_column(String(10))
    season_day: Mapped[int] = mapped_column(Integer, default=1)
    game_date: Mapped[str] = mapped_column(String(20))
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_played: Mapped[bool] = mapped_column(Boolean, default=False)
    career_id: Mapped[int | None] = mapped_column(ForeignKey("career_saves.id"), nullable=True)
    is_playoff: Mapped[bool] = mapped_column(Boolean, default=False)
    playoff_round: Mapped[str | None] = mapped_column(String(30), nullable=True)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    career_id: Mapped[int | None] = mapped_column(ForeignKey("career_saves.id"), nullable=True)
    season: Mapped[str] = mapped_column(String(10))
    transaction_type: Mapped[str] = mapped_column(String(30))
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SeasonResult(Base):
    __tablename__ = "season_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    career_id: Mapped[int | None] = mapped_column(ForeignKey("career_saves.id"), nullable=True)
    season: Mapped[str] = mapped_column(String(10))
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    playoff_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    made_playoffs: Mapped[bool] = mapped_column(Boolean, default=False)


class Award(Base):
    __tablename__ = "awards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    career_id: Mapped[int | None] = mapped_column(ForeignKey("career_saves.id"), nullable=True)
    season: Mapped[str] = mapped_column(String(10))
    award_type: Mapped[str] = mapped_column(String(50))
    player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)


class PlayerRatingHistory(Base):
    __tablename__ = "player_ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    season: Mapped[str] = mapped_column(String(10))
    overall_rating: Mapped[float] = mapped_column(Float)
    potential: Mapped[float] = mapped_column(Float)


class DraftProspect(Base):
    __tablename__ = "draft_prospects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    career_id: Mapped[int] = mapped_column(ForeignKey("career_saves.id"))
    season: Mapped[str] = mapped_column(String(10))
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    position: Mapped[str] = mapped_column(String(10))
    age: Mapped[int] = mapped_column(Integer, default=19)
    height: Mapped[str] = mapped_column(String(10), default="6-6")
    overall_rating: Mapped[float] = mapped_column(Float)
    potential: Mapped[float] = mapped_column(Float)
    scouting_report: Mapped[str] = mapped_column(Text, default="")
    combine_score: Mapped[float] = mapped_column(Float, default=75.0)
    drafted_by_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    pick_number: Mapped[int | None] = mapped_column(Integer, nullable=True)


class FreeAgentOffer(Base):
    __tablename__ = "free_agent_offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    career_id: Mapped[int] = mapped_column(ForeignKey("career_saves.id"))
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    salary: Mapped[float] = mapped_column(Float)
    years: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CareerTeamState(Base):
    __tablename__ = "career_team_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    career_id: Mapped[int] = mapped_column(ForeignKey("career_saves.id"))
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (UniqueConstraint("career_id", "team_id", name="uq_career_team"),)


class TradeOffer(Base):
    __tablename__ = "trade_offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    career_id: Mapped[int] = mapped_column(ForeignKey("career_saves.id"))
    from_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    to_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    send_player_ids: Mapped[str] = mapped_column(Text, default="[]")
    receive_player_ids: Mapped[str] = mapped_column(Text, default="[]")
    send_pick_ids: Mapped[str] = mapped_column(Text, default="[]")
    receive_pick_ids: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    is_rumor: Mapped[bool] = mapped_column(Boolean, default=False)
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

