import { useCallback, useEffect, useState } from 'react';
import type { Session, User } from '@supabase/supabase-js';
import { api } from '@/api/client';
import type { SubmitScoreResponse } from '@/types';
import { PENDING_SCORE_KEY, supabase, supabaseEnabled } from '@/lib/supabase';

export function useLeaderboardAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [authLoading, setAuthLoading] = useState(supabaseEnabled);
  const [submitNotice, setSubmitNotice] = useState<string | null>(null);

  const submitScore = useCallback(async (score: number, accessToken: string) => {
    return api.submitLeaderboardScore(score, accessToken);
  }, []);

  const trySubmitPendingScore = useCallback(
    async (activeSession: Session | null): Promise<SubmitScoreResponse | null> => {
      if (!activeSession?.access_token) return null;
      const pending = sessionStorage.getItem(PENDING_SCORE_KEY);
      if (!pending) return null;

      sessionStorage.removeItem(PENDING_SCORE_KEY);
      const parsed = Number.parseInt(pending, 10);
      if (Number.isNaN(parsed) || parsed < 0) return null;

      const result = await submitScore(parsed, activeSession.access_token);
      setSubmitNotice(
        result.is_new_best
          ? `Score saved! New personal best — ${result.high_score} pts${result.rank ? ` (rank #${result.rank})` : ''}`
          : `Score saved. Your best remains ${result.high_score} pts`,
      );
      return result;
    },
    [submitScore],
  );

  useEffect(() => {
    if (!supabase) {
      setAuthLoading(false);
      return;
    }

    let mounted = true;

    void supabase.auth.getSession().then(async ({ data }) => {
      if (!mounted) return;
      setSession(data.session);
      setUser(data.session?.user ?? null);
      await trySubmitPendingScore(data.session);
      setAuthLoading(false);
    });

    const { data: subscription } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      setUser(nextSession?.user ?? null);
      void trySubmitPendingScore(nextSession);
    });

    return () => {
      mounted = false;
      subscription.subscription.unsubscribe();
    };
  }, [trySubmitPendingScore]);

  const signInWithGoogle = useCallback(async (pendingScore?: number) => {
    if (!supabase) return;
    if (pendingScore !== undefined) {
      sessionStorage.setItem(PENDING_SCORE_KEY, String(pendingScore));
    }
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: window.location.origin,
      },
    });
  }, []);

  const signOut = useCallback(async () => {
    if (!supabase) return;
    await supabase.auth.signOut();
  }, []);

  return {
    enabled: supabaseEnabled,
    user,
    session,
    authLoading,
    submitNotice,
    clearSubmitNotice: () => setSubmitNotice(null),
    signInWithGoogle,
    signOut,
    submitScore,
  };
}
