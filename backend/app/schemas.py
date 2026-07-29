"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TeamSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nba_id: int
    name: str
    abbreviation: str
    city: str
    conference: str
    division: str
    overall_rating: float
    wins: int
    losses: int
    salary_cap_space: float
    young_core_rating: str
    draft_assets_score: int
    championship_window: str
    difficulty_rating: int


class TeamDetail(TeamSummary):
    luxury_tax: float
    chemistry: float
    fan_happiness: float
    owner_expectations: str
    coach_philosophy: str
    championship_odds: float
    playoff_odds: float


class PlayerSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nba_id: int
    first_name: str
    last_name: str
    position: str
    age: int
    height: str
    weight: int
    overall_rating: float
    potential: float
    salary: float
    years_remaining: int
    is_starter: bool
    minutes_per_game: float
    is_g_league: bool = False
    injury_status: str = "Healthy"
    ppg: float = 0.0
    rpg: float = 0.0
    apg: float = 0.0
    fg_pct: float = 0.45
    fg3_pct: float = 0.35
    tpg: float = 0.0


class PlayerAttributes(BaseModel):
    shooting: float
    defense: float
    playmaking: float
    athleticism: float
    rebounding: float
    basketball_iq: float
    durability: float


class PlayerSeasonStats(BaseModel):
    games_played: int
    ppg: float
    rpg: float
    apg: float
    fg_pct: float
    fg3_pct: float
    tpg: float
    ts_pct: float
    per: float


class PlayerRatingPoint(BaseModel):
    season: str
    overall_rating: float
    potential: float


class PlayerDetail(PlayerSummary):
    shooting: float
    defense: float
    playmaking: float
    athleticism: float
    rebounding: float
    basketball_iq: float
    durability: float
    player_mood: float
    fatigue: float
    development_trend: str
    ts_pct: float
    per: float
    team_name: str = ""
    team_abbreviation: str = ""
    season_stats: PlayerSeasonStats | None = None
    rating_history: list[PlayerRatingPoint] = []


class CareerSaveSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slot: int
    name: str
    team_id: int
    season: str
    season_day: int
    phase: str = "regular_season"
    job_security: float = 75.0
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CareerSaveDetail(CareerSaveSummary):
    team: TeamSummary


class CreateCareerRequest(BaseModel):
    team_id: int
    career_name: str = Field(min_length=1, max_length=120)


class LoadCareerRequest(BaseModel):
    slot: int = Field(ge=1, le=10)


class HealthResponse(BaseModel):
    status: str
    app: str
    player_count: int = 0
    season: str = ""


class MessageResponse(BaseModel):
    message: str


class SeedResponse(BaseModel):
    message: str
    roster_source: str
    player_count: int


class TeamHubResponse(BaseModel):
    career: CareerSaveDetail
    team: TeamDetail
    roster: list[PlayerSummary]


class RosterPlayerUpdate(BaseModel):
    player_id: int
    is_starter: bool = False
    minutes_per_game: float = Field(ge=0, le=48)
    is_g_league: bool = False


class RosterUpdateRequest(BaseModel):
    players: list[RosterPlayerUpdate]


class StandingsEntry(BaseModel):
    team_id: int
    abbreviation: str
    city: str
    name: str
    conference: str
    division: str
    wins: int
    losses: int
    win_pct: float
    overall_rating: float
    seed: int | None = None


class StandingsResponse(BaseModel):
    season: str
    east: list[StandingsEntry]
    west: list[StandingsEntry]


class GameSummary(BaseModel):
    id: int
    season_day: int
    game_date: str
    is_home: bool
    opponent_id: int
    opponent_abbreviation: str
    opponent_name: str
    team_score: int | None
    opponent_score: int | None
    is_played: bool
    result: str | None = None


class ScheduleResponse(BaseModel):
    season: str
    season_day: int
    games: list[GameSummary]
    upcoming: list[GameSummary]
    recent: list[GameSummary]


class NewsItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    season: str
    transaction_type: str
    description: str
    created_at: datetime


class BoxScorePlayer(BaseModel):
    player_id: int
    name: str
    points: int
    rebounds: int
    assists: int
    minutes: float


class GameResult(BaseModel):
    game_id: int
    season_day: int
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    user_team_won: bool
    home_box_score: list[BoxScorePlayer]
    away_box_score: list[BoxScorePlayer]


SimulationMode = Literal["game", "week", "month", "all_star", "deadline", "playoffs", "season"]


class SimulationRequest(BaseModel):
    mode: SimulationMode = "game"


class SimulationResponse(BaseModel):
    mode: SimulationMode
    games_simulated: int
    days_advanced: int
    season_day: int
    season: str
    last_game: GameResult | None
    news: list[str]


# --- Phase 3 Schemas ---


class ContractSummary(BaseModel):
    player_id: int
    player_name: str
    salary: float
    years_remaining: int
    has_player_option: bool
    has_team_option: bool
    is_bird_rights: bool


class CapSheetResponse(BaseModel):
    team_id: int
    team_name: str
    salary_cap: float
    luxury_tax_line: float
    first_apron: float
    payroll: float
    cap_space: float
    luxury_tax: float
    over_cap: bool
    over_tax: bool
    roster_count: int
    expiring_contracts: int
    dead_money: float
    contracts: list[ContractSummary]


class TradeAsset(BaseModel):
    type: str
    id: int
    label: str


class TradeProposalRequest(BaseModel):
    partner_team_id: int
    send_player_ids: list[int] = []
    receive_player_ids: list[int] = []
    send_pick_ids: list[int] = []
    receive_pick_ids: list[int] = []


class TradeEvaluation(BaseModel):
    partner_team_id: int
    partner_team_name: str
    send_assets: list[TradeAsset]
    receive_assets: list[TradeAsset]
    fairness_score: float
    salary_legal: bool
    roster_fit_score: float
    value_gained: float
    accepted: bool
    reason: str


class TradeResult(BaseModel):
    success: bool
    evaluation: TradeEvaluation
    message: str


class DraftPickSummary(BaseModel):
    id: int
    season: str
    round_number: int
    pick_number: int | None
    team_id: int


class FreeAgentSummary(BaseModel):
    id: int
    first_name: str
    last_name: str
    position: str
    age: int
    overall_rating: float
    potential: float
    desired_salary: float


class FreeAgencyOfferRequest(BaseModel):
    player_id: int
    salary: float = Field(gt=0)
    years: int = Field(ge=1, le=5)


class SigningResult(BaseModel):
    success: bool
    player_id: int
    player_name: str
    message: str
    salary: float | None = None
    years: int | None = None


class PlayoffSeriesResult(BaseModel):
    round_name: str
    team_a: str
    team_b: str
    winner: str
    score: str
    games_played: int


class PlayoffBracket(BaseModel):
    season: str
    east_r1: list[dict]
    west_r1: list[dict]
    champion_id: int | None = None
    champion_name: str | None = None


class PlayoffSimResponse(BaseModel):
    round_name: str
    series_results: list[PlayoffSeriesResult]
    champion_id: int | None
    champion_name: str | None
    bracket: PlayoffBracket


class DraftProspectSummary(BaseModel):
    id: int
    first_name: str
    last_name: str
    position: str
    age: int
    height: str
    overall_rating: float
    potential: float
    scouting_report: str
    combine_score: float


class DraftBoardResponse(BaseModel):
    season: str
    prospects: list[DraftProspectSummary]
    team_picks: list[dict]


class DraftPickRequest(BaseModel):
    prospect_id: int
    pick_id: int


class DraftPickResult(BaseModel):
    pick_number: int
    team_name: str
    player_name: str
    position: str
    overall_rating: float


class OffseasonResponse(BaseModel):
    new_season: str
    retirements: list[str]
    free_agents: list[str]
    developments: list[str]
    message: str


class TeamAnalytics(BaseModel):
    team_id: int
    team_name: str
    offensive_rating: float
    defensive_rating: float
    net_rating: float
    pace: float
    true_shooting_pct: float
    effective_fg_pct: float
    rebounding_pct: float
    turnover_pct: float
    player_impact_estimate: float
    wins: int
    losses: int


# --- Phase 4 Schemas ---


class ContractExtensionRequest(BaseModel):
    player_id: int
    salary: float = Field(gt=0)
    years: int = Field(ge=1, le=5)
    include_player_option: bool = False
    include_team_option: bool = False


class ExtensionResult(BaseModel):
    success: bool
    player_name: str
    message: str
    salary: float | None = None
    years: int | None = None


class TradeInboxItem(BaseModel):
    id: int
    from_team_name: str
    message: str
    send_player_ids: list[int]
    receive_player_ids: list[int]
    is_rumor: bool
    created_at: datetime


class TradeInboxResponse(BaseModel):
    accept: bool


class AwardSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    season: str
    award_type: str
    player_id: int | None
    team_id: int | None
    player_name: str = ""


class CareerStatusResponse(BaseModel):
    job_security: float
    job_status: str
    owner_expectations: str
    phase: str


# --- Name Rush Game ---


class GameStatusResponse(BaseModel):
    season: str
    player_count: int
    timer_seconds: int = 30
    mode: str = "all_time"
    mode_label: str = "All-time basketball"


class GameStartRequest(BaseModel):
    mode: str = "all_time"


class GameStartResponse(BaseModel):
    initials: str
    initials_player_count: int = 0


class GameGuessRequest(BaseModel):
    initials: str = Field(min_length=2, max_length=2)
    guess: str = Field(min_length=2, max_length=80)
    used_player_ids: list[int] = Field(default_factory=list)
    mode: str = "all_time"
    time_remaining: int = Field(default=0, ge=0, le=60)


class GameGuessResponse(BaseModel):
    correct: bool
    game_over: bool
    points: int = 0
    reason: str = ""
    matched_name: str = ""
    matched_nba_id: int = 0
    next_initials: str = ""
    next_initials_player_count: int = 0
    matching_players: list[str] = Field(default_factory=list)


class InitialsRevealRequest(BaseModel):
    initials_list: list[str] = Field(default_factory=list, min_length=1, max_length=50)
    mode: str = "all_time"


class RevealPlayerEntry(BaseModel):
    full_name: str
    from_season: str = ""
    to_season: str = ""
    career_span: str = ""


class InitialsRevealEntry(BaseModel):
    initials: str
    players: list[RevealPlayerEntry]
    player_count: int


class InitialsRevealResponse(BaseModel):
    reveals: list[InitialsRevealEntry]


class LeaderboardEntry(BaseModel):
    rank: int
    display_name: str
    high_score: int
    updated_at: str | None = None
    is_you: bool = False


class LeaderboardResponse(BaseModel):
    enabled: bool = True
    entries: list[LeaderboardEntry] = Field(default_factory=list)


class SubmitScoreRequest(BaseModel):
    score: int = Field(ge=0, le=100000)


class SubmitScoreResponse(BaseModel):
    high_score: int
    is_new_best: bool
    rank: int | None = None


class ProfileResponse(BaseModel):
    display_name: str = ""
    high_score: int = 0
    friendly_wins: int = 0
    games_played: int = 0
    correct_answers: int = 0
    total_attempts: int = 0
    points_earned: int = 0
    accuracy: float = 0.0
    avg_points: float = 0.0
    friendly_games_played: int = 0
    friendly_points_earned: int = 0
    friendly_avg_points: float = 0.0
    rank: int | None = None
    updated_at: str | None = None


class CareerGameRequest(BaseModel):
    score: int = Field(ge=0, le=100000)
    correct: int = Field(ge=0, le=100000)
    attempts: int = Field(ge=0, le=100000)


class MultiplayerPlayerState(BaseModel):
    player_id: str
    display_name: str
    score: int = 0
    is_host: bool = False
    is_you: bool = False
    has_passed: bool = False
    avatar_url: str | None = None


class MultiplayerCreateRequest(BaseModel):
    total_rounds: int = 9
    era: str = "all_time"


class MultiplayerJoinRequest(BaseModel):
    code: str = Field(min_length=4, max_length=8)


class MultiplayerSetRoundsRequest(BaseModel):
    code: str = Field(min_length=4, max_length=8)
    total_rounds: int | None = None
    era: str | None = None


class MultiplayerStartRequest(BaseModel):
    code: str = Field(min_length=4, max_length=8)


class MultiplayerRematchRequest(BaseModel):
    code: str = Field(min_length=4, max_length=8)


class MultiplayerLeaveRequest(BaseModel):
    code: str = Field(min_length=4, max_length=8)


class MultiplayerPassRequest(BaseModel):
    code: str = Field(min_length=4, max_length=8)


class MultiplayerGuessRequest(BaseModel):
    code: str = Field(min_length=4, max_length=8)
    guess: str = Field(min_length=2, max_length=80)


class MultiplayerRoomResponse(BaseModel):
    code: str
    status: str
    max_players: int = 4
    total_rounds: int = 9
    era: str = "all_time"
    era_label: str = "All-time"
    round_seconds: int = 30
    countdown_seconds: int = 3
    round_index: int = 0
    round_number: int = 1
    time_left: int | None = None
    countdown_left: int | None = None
    current_initials: str = ""
    initials_player_count: int = 0
    players: list[MultiplayerPlayerState] = Field(default_factory=list)
    pass_count: int = 0
    you_passed: bool = False
    last_message: str = ""
    last_winner_id: str | None = None
    last_matched_name: str = ""
    winner_ids: list[str] = Field(default_factory=list)
    you_are_host: bool = False
    in_room: bool = False
    can_start: bool = False
    accepted: bool | None = None
    your_feedback: str | None = None

