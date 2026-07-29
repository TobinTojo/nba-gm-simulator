export interface HealthResponse {
  status: string;
  app: string;
  player_count: number;
  season: string;
}

export interface GameStatusResponse {
  season: string;
  player_count: number;
  timer_seconds: number;
  mode: PlayerPoolMode;
  mode_label: string;
}

export type PlayerPoolMode = 'all_time' | 'current';

export interface GameStartResponse {
  initials: string;
  initials_player_count: number;
}

export interface GameGuessResponse {
  correct: boolean;
  game_over: boolean;
  points: number;
  reason: string;
  matched_name: string;
  matched_nba_id: number;
  next_initials: string;
  next_initials_player_count: number;
  matching_players: string[];
}

export interface RevealPlayerEntry {
  full_name: string;
  from_season: string;
  to_season: string;
  career_span: string;
}

export interface InitialsRevealEntry {
  initials: string;
  players: RevealPlayerEntry[];
  player_count: number;
}

export interface InitialsRevealResponse {
  reveals: InitialsRevealEntry[];
}

export type GamePhase = 'idle' | 'playing' | 'gameover';

export interface SessionRound {
  initials: string;
  guess: string;
  matched_name: string;
  points: number;
  time_spent: number;
  success: boolean;
}

export interface RoundLog {
  initials: string;
  guess: string;
  points: number;
  matched_name: string;
}

export interface LeaderboardEntry {
  rank: number;
  display_name: string;
  high_score: number;
  updated_at: string | null;
  is_you: boolean;
}

export interface LeaderboardResponse {
  enabled: boolean;
  entries: LeaderboardEntry[];
}

export interface SubmitScoreResponse {
  high_score: number;
  is_new_best: boolean;
  rank: number | null;
}

export interface ProfileResponse {
  display_name: string;
  high_score: number;
  friendly_wins: number;
  games_played: number;
  correct_answers: number;
  total_attempts: number;
  points_earned: number;
  accuracy: number;
  avg_points: number;
  friendly_games_played: number;
  friendly_points_earned: number;
  friendly_avg_points: number;
  rank: number | null;
  updated_at: string | null;
}

export interface MultiplayerPlayerState {
  player_id: string;
  display_name: string;
  score: number;
  is_host: boolean;
  is_you: boolean;
  has_passed: boolean;
  ready_for_rematch?: boolean;
  avatar_url?: string | null;
}

export interface MultiplayerRoomResponse {
  code: string;
  status: 'waiting' | 'playing' | 'finished' | string;
  max_players: number;
  total_rounds: number;
  era: string;
  era_label: string;
  is_public?: boolean;
  round_seconds: number;
  countdown_seconds: number;
  round_index: number;
  round_number: number;
  time_left: number | null;
  countdown_left: number | null;
  current_initials: string;
  initials_player_count: number;
  players: MultiplayerPlayerState[];
  pass_count: number;
  you_passed: boolean;
  last_message: string;
  last_winner_id: string | null;
  last_matched_name: string;
  winner_ids: string[];
  you_are_host: boolean;
  in_room: boolean;
  can_start: boolean;
  rematch_ready_count?: number;
  you_ready_for_rematch?: boolean;
  accepted?: boolean | null;
  your_feedback?: string | null;
}

export interface PublicLobbyEntry {
  code: string;
  host_name: string;
  player_count: number;
  max_players: number;
  total_rounds: number;
  era: string;
  era_label: string;
  updated_at: number;
}

export interface PublicLobbyListResponse {
  lobbies: PublicLobbyEntry[];
}
