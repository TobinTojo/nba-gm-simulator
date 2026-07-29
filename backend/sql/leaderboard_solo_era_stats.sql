-- Per-era solo career stats (JSON object keyed by era id).

ALTER TABLE public.leaderboard
  ADD COLUMN IF NOT EXISTS solo_era_stats JSONB NOT NULL DEFAULT '{}'::jsonb;
