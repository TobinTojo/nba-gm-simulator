import { useEffect, useState } from 'react';
import { api } from '@/api/client';
import type { ProfileResponse } from '@/types';
import type { Session, User } from '@supabase/supabase-js';

interface CareerStatsPageProps {
  enabled: boolean;
  user: User | null;
  session: Session | null;
  authLoading: boolean;
  signInWithGoogle: () => Promise<void>;
  refreshKey?: number;
  onBack: () => void;
}

export function CareerStatsPage({
  enabled,
  user,
  session,
  authLoading,
  signInWithGoogle,
  refreshKey = 0,
  onBack,
}: CareerStatsPageProps) {
  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!session?.access_token) {
      setProfile(null);
      return;
    }
    setLoading(true);
    setError(null);
    void api
      .getProfile(session.access_token)
      .then(setProfile)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Could not load career stats.');
      })
      .finally(() => setLoading(false));
  }, [session?.access_token, refreshKey]);

  const displayName =
    profile?.display_name ||
    user?.user_metadata?.full_name ||
    user?.user_metadata?.name ||
    user?.email?.split('@')[0] ||
    'Player';

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-4 py-10 sm:px-6">
      <div className="animate-slide-up">
        <p className="text-xs font-semibold uppercase tracking-[0.35em] text-accent">Career</p>
        <h1 className="mt-2 font-display text-5xl tracking-wide text-white">Your Stats</h1>
        <p className="mt-3 text-slate-400">Solo run history tied to your Google account.</p>
      </div>

      <section className="card mt-8 p-6 sm:p-8 animate-slide-up">
        {!enabled ? (
          <p className="text-slate-400">Career stats need leaderboard sign-in configured.</p>
        ) : authLoading || loading ? (
          <p className="text-slate-400">Loading stats...</p>
        ) : !user ? (
          <div className="text-center">
            <p className="text-slate-300">Sign in to track games played, accuracy, and average points.</p>
            <button
              type="button"
              onClick={() => void signInWithGoogle()}
              className="btn-primary mt-6 px-8 py-3"
            >
              Sign in with Google
            </button>
          </div>
        ) : error ? (
          <p className="text-red-300">{error}</p>
        ) : (
          <>
            <p className="text-sm text-slate-400">
              Playing as <span className="text-white">{displayName}</span>
              {profile?.rank != null ? (
                <>
                  {' '}
                  · Rank <span className="text-accent">#{profile.rank}</span>
                </>
              ) : null}
            </p>

            <div className="mt-8 grid gap-4 sm:grid-cols-2">
              <StatCard label="Games played" value={String(profile?.games_played ?? 0)} />
              <StatCard label="Accuracy" value={`${profile?.accuracy ?? 0}%`} accent />
              <StatCard label="Avg points" value={String(profile?.avg_points ?? 0)} />
              <StatCard label="Best score" value={String(profile?.high_score ?? 0)} />
              <StatCard label="Friendly 1v1 wins" value={String(profile?.friendly_wins ?? 0)} />
              <StatCard label="Total points" value={String(profile?.points_earned ?? 0)} />
            </div>
          </>
        )}

        <button type="button" onClick={onBack} className="btn-ghost mt-8 px-6 py-3">
          Back to home
        </button>
      </section>
    </main>
  );
}

function StatCard({
  label,
  value,
  accent = false,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-court-950/50 px-4 py-5">
      <p className="text-[10px] uppercase tracking-[0.22em] text-slate-500">{label}</p>
      <p className={`mt-2 font-display text-4xl ${accent ? 'text-accent' : 'text-white'}`}>{value}</p>
    </div>
  );
}
