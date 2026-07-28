-- Run in Supabase SQL Editor to track solo career stats.

ALTER TABLE public.leaderboard
  ADD COLUMN IF NOT EXISTS games_played INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS correct_answers INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS total_attempts INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS points_earned INTEGER NOT NULL DEFAULT 0;
