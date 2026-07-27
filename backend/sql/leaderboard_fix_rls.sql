-- Run in Supabase SQL Editor if score submit returns 500.
-- Backend-only access: disable RLS so Render can read/write via Postgres URI.

ALTER TABLE public.leaderboard DISABLE ROW LEVEL SECURITY;

GRANT SELECT, INSERT, UPDATE, DELETE ON public.leaderboard TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.leaderboard TO service_role;
