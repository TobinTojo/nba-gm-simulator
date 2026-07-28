-- Run once in Supabase SQL Editor (Dashboard → SQL → New query)

CREATE TABLE IF NOT EXISTS public.leaderboard (
  user_id UUID PRIMARY KEY,
  display_name TEXT NOT NULL,
  high_score INTEGER NOT NULL DEFAULT 0 CHECK (high_score >= 0),
  friendly_wins INTEGER NOT NULL DEFAULT 0 CHECK (friendly_wins >= 0),
  games_played INTEGER NOT NULL DEFAULT 0 CHECK (games_played >= 0),
  correct_answers INTEGER NOT NULL DEFAULT 0 CHECK (correct_answers >= 0),
  total_attempts INTEGER NOT NULL DEFAULT 0 CHECK (total_attempts >= 0),
  points_earned INTEGER NOT NULL DEFAULT 0 CHECK (points_earned >= 0),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.leaderboard
  ADD COLUMN IF NOT EXISTS friendly_wins INTEGER NOT NULL DEFAULT 0;

ALTER TABLE public.leaderboard
  ADD COLUMN IF NOT EXISTS games_played INTEGER NOT NULL DEFAULT 0;

ALTER TABLE public.leaderboard
  ADD COLUMN IF NOT EXISTS correct_answers INTEGER NOT NULL DEFAULT 0;

ALTER TABLE public.leaderboard
  ADD COLUMN IF NOT EXISTS total_attempts INTEGER NOT NULL DEFAULT 0;

ALTER TABLE public.leaderboard
  ADD COLUMN IF NOT EXISTS points_earned INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS leaderboard_high_score_idx
  ON public.leaderboard (high_score DESC, updated_at ASC);

ALTER TABLE public.leaderboard DISABLE ROW LEVEL SECURITY;
