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
