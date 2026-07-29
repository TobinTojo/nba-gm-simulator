-- Clear career / friendly / era stats for all users.
-- Keeps leaderboard high_score and display_name intact.

ALTER TABLE public.leaderboard
  ADD COLUMN IF NOT EXISTS solo_era_stats JSONB NOT NULL DEFAULT '{}'::jsonb;

UPDATE public.leaderboard
SET
  games_played = 0,
  correct_answers = 0,
  total_attempts = 0,
  points_earned = 0,
  friendly_wins = 0,
  friendly_games_played = 0,
  friendly_points_earned = 0,
  solo_era_stats = '{}'::jsonb;
