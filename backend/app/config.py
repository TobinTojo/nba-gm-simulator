"""Application configuration."""

from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _parse_cors_origins_extra(value: str) -> list[str]:
    if not value.strip():
        return []
    origins: list[str] = []
    for origin in value.split(","):
        cleaned = origin.strip().rstrip("/")
        if cleaned:
            origins.append(cleaned)
    return origins


class Settings(BaseSettings):
    app_name: str = "Name Rush"
    database_url: str = f"sqlite:///{DATA_DIR / 'nba_gm.db'}"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://namerushball.netlify.app",
    ]
    # Comma-separated production frontend URLs, e.g.
    # https://namerushball.netlify.app
    cors_origins_extra: str = ""
    # Regex for deployed Netlify frontends, e.g. https://namerushball.netlify.app
    cors_origin_regex: str = r"https://.*\.netlify\.app"
    leaderboard_database_url: str = ""
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""
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

    @model_validator(mode="after")
    def merge_cors_origins(self) -> "Settings":
        existing = set(self.cors_origins)
        for origin in _parse_cors_origins_extra(self.cors_origins_extra):
            if origin not in existing:
                self.cors_origins.append(origin)
                existing.add(origin)
        return self


settings = Settings()
