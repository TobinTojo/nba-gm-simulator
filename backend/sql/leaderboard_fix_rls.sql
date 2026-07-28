-- Run in Supabase SQL Editor if leaderboard submit still fails.

ALTER TABLE public.leaderboard DISABLE ROW LEVEL SECURITY;

GRANT USAGE ON SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.leaderboard TO postgres, service_role;
GRANT SELECT ON public.leaderboard TO anon, authenticated;
