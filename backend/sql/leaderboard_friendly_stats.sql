-- Run in Supabase SQL Editor to track friendly match averages separately from solo.

ALTER TABLE public.leaderboard
  ADD COLUMN IF NOT EXISTS friendly_games_played INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS friendly_points_earned INTEGER NOT NULL DEFAULT 0;
