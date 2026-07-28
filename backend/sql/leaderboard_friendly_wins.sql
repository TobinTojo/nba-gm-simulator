-- Run once in Supabase SQL Editor to track friendly 1v1 wins on profiles.

ALTER TABLE public.leaderboard
  ADD COLUMN IF NOT EXISTS friendly_wins INTEGER NOT NULL DEFAULT 0
  CHECK (friendly_wins >= 0);
