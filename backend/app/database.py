"""SQLAlchemy database setup."""

from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


PLAYER_MIGRATIONS = [
    ("is_g_league", "BOOLEAN DEFAULT 0"),
    ("player_mood", "FLOAT DEFAULT 75.0"),
    ("fatigue", "FLOAT DEFAULT 0.0"),
    ("injury_status", "VARCHAR(30) DEFAULT 'Healthy'"),
    ("development_trend", "VARCHAR(20) DEFAULT 'Stable'"),
    ("games_played", "INTEGER DEFAULT 0"),
    ("ppg", "FLOAT DEFAULT 0.0"),
    ("rpg", "FLOAT DEFAULT 0.0"),
    ("apg", "FLOAT DEFAULT 0.0"),
    ("ts_pct", "FLOAT DEFAULT 0.55"),
    ("per", "FLOAT DEFAULT 15.0"),
]

GAME_MIGRATIONS = [
    ("season_day", "INTEGER DEFAULT 1"),
    ("career_id", "INTEGER"),
    ("is_playoff", "BOOLEAN DEFAULT 0"),
    ("playoff_round", "VARCHAR(30)"),
]

CAREER_MIGRATIONS = [
    ("phase", "VARCHAR(30) DEFAULT 'regular_season'"),
    ("job_security", "FLOAT DEFAULT 75.0"),
]

TRANSACTION_MIGRATIONS = [("career_id", "INTEGER")]
AWARD_MIGRATIONS = [("career_id", "INTEGER")]
SEASON_RESULT_MIGRATIONS = [("career_id", "INTEGER")]

PLAYER_PHASE3_MIGRATIONS = [
    ("is_free_agent", "BOOLEAN DEFAULT 0"),
]

PLAYER_PHASE5_MIGRATIONS = [
    ("fg_pct", "FLOAT DEFAULT 0.45"),
    ("fg3_pct", "FLOAT DEFAULT 0.35"),
    ("tpg", "FLOAT DEFAULT 0.0"),
]


def _add_column_if_missing(table: str, column: str, definition: str) -> None:
    inspector = inspect(engine)
    if not inspector.has_table(table):
        return
    existing = {col["name"] for col in inspector.get_columns(table)}
    if column not in existing:
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))


def migrate_db() -> None:
    """Apply lightweight SQLite migrations for new columns."""
    for column, definition in PLAYER_MIGRATIONS:
        _add_column_if_missing("players", column, definition)
    for column, definition in PLAYER_PHASE3_MIGRATIONS:
        _add_column_if_missing("players", column, definition)
    for column, definition in PLAYER_PHASE5_MIGRATIONS:
        _add_column_if_missing("players", column, definition)
    for column, definition in GAME_MIGRATIONS:
        _add_column_if_missing("games", column, definition)
    for column, definition in CAREER_MIGRATIONS:
        _add_column_if_missing("career_saves", column, definition)
    for column, definition in TRANSACTION_MIGRATIONS:
        _add_column_if_missing("transactions", column, definition)
    for column, definition in AWARD_MIGRATIONS:
        _add_column_if_missing("awards", column, definition)
    for column, definition in SEASON_RESULT_MIGRATIONS:
        _add_column_if_missing("season_results", column, definition)


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    migrate_db()
