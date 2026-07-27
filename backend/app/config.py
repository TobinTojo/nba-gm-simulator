"""Application configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    app_name: str = "NBA Initials"
    database_url: str = f"sqlite:///{DATA_DIR / 'nba_gm.db'}"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    # Optional: comma-separated list for production, e.g.
    # https://nba-initials.onrender.com,https://my-app.netlify.app
    cors_origins_extra: str = ""
    current_season: str = "2025-26"
    # "all_time" = every NBA player ever; "current" = active rosters only
    player_pool_mode: str = "all_time"
    game_timer_seconds: int = 30
    salary_cap_millions: float = 136.0
    luxury_tax_line_millions: float = 165.0
    first_apron_millions: float = 172.0
    min_team_salary_millions: float = 126.0
    max_roster_size: int = 15
    playoff_series_length: int = 7


settings = Settings()

if settings.cors_origins_extra.strip():
    settings.cors_origins.extend(
        origin.strip()
        for origin in settings.cors_origins_extra.split(",")
        if origin.strip()
    )
