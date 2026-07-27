-- Run once in Supabase SQL Editor (Dashboard → SQL → New query)

CREATE TABLE IF NOT EXISTS public.leaderboard (
  user_id UUID PRIMARY KEY,
  display_name TEXT NOT NULL,
  high_score INTEGER NOT NULL DEFAULT 0 CHECK (high_score >= 0),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS leaderboard_high_score_idx
  ON public.leaderboard (high_score DESC, updated_at ASC);
