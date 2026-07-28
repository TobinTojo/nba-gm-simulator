import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '@/api/client';
import { AboutSection } from '@/components/AboutSection';
import { CareerStatsPage } from '@/components/CareerStatsPage';
import { LandingHero } from '@/components/LandingHero';
import { SiteNav } from '@/components/SiteNav';
import { useLeaderboardAuth } from '@/hooks/useLeaderboardAuth';
import { LeaderboardPanel } from '@/LeaderboardPanel';
import { MultiplayerRoom } from '@/MultiplayerRoom';
import type { GamePhase, InitialsRevealEntry, SessionRound } from '@/types';

const DEFAULT_TIMER_SECONDS = 30;

type AppMode = 'home' | 'solo' | 'versus' | 'stats';

export function GamePage() {
  const {
    enabled: leaderboardEnabled,
    user,
    session,
    authLoading,
    signInWithGoogle,
    signOut,
    submitScore,
    submitNotice,
  } = useLeaderboardAuth();

  const [mode, setMode] = useState<AppMode>('home');
  const [phase, setPhase] = useState<GamePhase>('idle');
  const [initials, setInitials] = useState('');
  const [initialsPlayerCount, setInitialsPlayerCount] = useState(0);
  const [guess, setGuess] = useState('');
  const [score, setScore] = useState(0);
  const [streak, setStreak] = useState(0);
  const [timerSeconds, setTimerSeconds] = useState(DEFAULT_TIMER_SECONDS);
  const [timeLeft, setTimeLeft] = useState(DEFAULT_TIMER_SECONDS);
  const [usedPlayerIds, setUsedPlayerIds] = useState<number[]>([]);
  const [sessionRounds, setSessionRounds] = useState<SessionRound[]>([]);
  const [reveals, setReveals] = useState<InitialsRevealEntry[]>([]);
  const [message, setMessage] = useState('');
  const [playerCount, setPlayerCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timerGeneration, setTimerGeneration] = useState(0);
  const [leaderboardMessage, setLeaderboardMessage] = useState('');
  const [leaderboardRefreshKey, setLeaderboardRefreshKey] = useState(0);
  const [profileRefreshKey, setProfileRefreshKey] = useState(0);
  const [submittingScore, setSubmittingScore] = useState(false);
  const [correctFlash, setCorrectFlash] = useState<{ name: string; points: number } | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);
  const phaseRef = useRef<GamePhase>('idle');
  const timeLeftRef = useRef(timeLeft);
  const timerSecondsRef = useRef(timerSeconds);
  const initialsRef = useRef(initials);
  const guessRef = useRef(guess);
  const sessionRoundsRef = useRef(sessionRounds);
  const submittedScoreRef = useRef<number | null>(null);

  useEffect(() => {
    phaseRef.current = phase;
  }, [phase]);

  useEffect(() => {
    timeLeftRef.current = timeLeft;
  }, [timeLeft]);

  useEffect(() => {
    timerSecondsRef.current = timerSeconds;
  }, [timerSeconds]);

  useEffect(() => {
    initialsRef.current = initials;
  }, [initials]);

  useEffect(() => {
    guessRef.current = guess;
  }, [guess]);

  useEffect(() => {
    sessionRoundsRef.current = sessionRounds;
  }, [sessionRounds]);

  useEffect(() => {
    if (submitNotice) {
      setLeaderboardRefreshKey((value) => value + 1);
      setProfileRefreshKey((value) => value + 1);
    }
  }, [submitNotice]);

  useEffect(() => {
    void api
      .getGameStatus()
      .then((status) => {
        setPlayerCount(status.player_count);
        setTimerSeconds(status.timer_seconds);
        setTimeLeft(status.timer_seconds);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const loadReveals = useCallback(async (rounds: SessionRound[]) => {
    const initialsList = [...new Set(rounds.map((round) => round.initials))];
    if (initialsList.length === 0) {
      setReveals([]);
      return;
    }
    try {
      const response = await api.revealInitials(initialsList);
      setReveals(response.reveals);
    } catch {
      setReveals([]);
    }
  }, []);

  const finishGame = useCallback(
    async (reason: string, finalRound: SessionRound, priorRounds: SessionRound[]) => {
      const allRounds = [...priorRounds, finalRound];
      setSessionRounds(allRounds);
      setPhase('gameover');
      setMessage(reason);
      setLeaderboardMessage('');
      submittedScoreRef.current = null;
      await loadReveals(allRounds);
    },
    [loadReveals],
  );

  useEffect(() => {
    if (phase !== 'gameover' || !leaderboardEnabled || !session?.access_token) {
      return;
    }
    if (submittedScoreRef.current === score && score > 0) {
      return;
    }
    if (submittedScoreRef.current === -1 && score === 0) {
      return;
    }

    submittedScoreRef.current = score > 0 ? score : -1;
    setSubmittingScore(true);
    const rounds = sessionRoundsRef.current;
    const correct = rounds.filter((round) => round.success).length;
    const attempts = Math.max(rounds.length, 1);

    void api
      .recordCareerGame(score, correct, attempts, session.access_token)
      .then((profile) => {
        if (score > 0 && profile.high_score === score) {
          setLeaderboardMessage(
            profile.rank ? `New personal best! Rank #${profile.rank}` : 'New personal best saved!',
          );
        } else if (score > 0) {
          setLeaderboardMessage(`Your best score remains ${profile.high_score} pts`);
        } else {
          setLeaderboardMessage('Career stats updated.');
        }
        setLeaderboardRefreshKey((value) => value + 1);
        setProfileRefreshKey((value) => value + 1);
      })
      .catch((err: unknown) => {
        if (score > 0) {
          return submitScore(score, session.access_token)
            .then((result) => {
              if (result.is_new_best) {
                setLeaderboardMessage(
                  result.rank
                    ? `New personal best! Rank #${result.rank}`
                    : 'New personal best saved!',
                );
              } else {
                setLeaderboardMessage(`Your best score remains ${result.high_score} pts`);
              }
              setLeaderboardRefreshKey((value) => value + 1);
              setProfileRefreshKey((value) => value + 1);
            })
            .catch((inner: unknown) => {
              const message =
                inner instanceof Error
                  ? inner.message
                  : err instanceof Error
                    ? err.message
                    : 'Could not save score to the leaderboard.';
              setLeaderboardMessage(message);
              submittedScoreRef.current = null;
            });
        }
        const message = err instanceof Error ? err.message : 'Could not save career stats.';
        setLeaderboardMessage(message);
        submittedScoreRef.current = null;
        return undefined;
      })
      .finally(() => setSubmittingScore(false));
  }, [phase, score, session, submitScore, leaderboardEnabled]);

  const endGameOnTimeout = useCallback(() => {
    const spent = timerSecondsRef.current;
    void finishGame(
      "Time's up!",
      {
        initials: initialsRef.current,
        guess: guessRef.current.trim(),
        matched_name: '-',
        points: 0,
        time_spent: spent,
        success: false,
      },
      sessionRoundsRef.current,
    );
  }, [finishGame]);

  useEffect(() => {
    if (phase !== 'playing' || correctFlash) return;

    const interval = window.setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          window.clearInterval(interval);
          if (phaseRef.current === 'playing') {
            endGameOnTimeout();
          }
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => window.clearInterval(interval);
  }, [phase, endGameOnTimeout, timerGeneration, correctFlash]);

  useEffect(() => {
    if (phase === 'playing') {
      inputRef.current?.focus();
    }
  }, [phase, initials]);

  async function handleStart() {
    setError(null);
    setLoading(true);
    try {
      const status = await api.getGameStatus();
      setPlayerCount(status.player_count);
      setTimerSeconds(status.timer_seconds);
      const start = await api.startGame();
      setInitials(start.initials);
      setInitialsPlayerCount(start.initials_player_count);
      setGuess('');
      setScore(0);
      setStreak(0);
      setTimeLeft(status.timer_seconds);
      setUsedPlayerIds([]);
      setSessionRounds([]);
      setReveals([]);
      setMessage('');
      setLeaderboardMessage('');
      setCorrectFlash(null);
      submittedScoreRef.current = null;
      setTimerGeneration((n) => n + 1);
      setMode('solo');
      setPhase('playing');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start game');
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (phase !== 'playing' || submitting || !guess.trim() || correctFlash) return;

    setSubmitting(true);
    setError(null);
    const submittedTimeLeft = timeLeftRef.current;
    const timeSpent = timerSeconds - submittedTimeLeft;
    try {
      const result = await api.submitGuess(initials, guess.trim(), usedPlayerIds, submittedTimeLeft);

      if (!result.correct || result.game_over) {
        await finishGame(
          result.reason || 'Wrong answer. Game over.',
          {
            initials,
            guess: guess.trim(),
            matched_name: result.matched_name || '-',
            points: 0,
            time_spent: timeSpent,
            success: false,
          },
          sessionRounds,
        );
        return;
      }

      const round: SessionRound = {
        initials,
        guess: guess.trim(),
        matched_name: result.matched_name,
        points: result.points,
        time_spent: timeSpent,
        success: true,
      };

      setScore((prev) => prev + result.points);
      setStreak((prev) => prev + 1);
      setUsedPlayerIds((prev) => [...prev, result.matched_nba_id]);
      setSessionRounds((prev) => [...prev, round]);
      setGuess('');
      setCorrectFlash({ name: result.matched_name, points: result.points });
      setMessage(`+${result.points} for ${result.matched_name}`);
      setSubmitting(false);

      await new Promise((resolve) => window.setTimeout(resolve, 1100));

      setInitials(result.next_initials);
      setInitialsPlayerCount(result.next_initials_player_count);
      setTimeLeft(timerSeconds);
      setTimerGeneration((n) => n + 1);
      setCorrectFlash(null);
    } catch (err) {
      await finishGame(
        err instanceof Error ? err.message : 'Something went wrong.',
        {
          initials,
          guess: guess.trim(),
          matched_name: '-',
          points: 0,
          time_spent: timeSpent,
          success: false,
        },
        sessionRounds,
      );
    } finally {
      setSubmitting(false);
    }
  }

  function goHome() {
    setMode('home');
    setPhase('idle');
    setError(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function scrollAbout() {
    document.getElementById('about')?.scrollIntoView({ behavior: 'smooth' });
  }

  const timerPct = (timeLeft / timerSeconds) * 100;
  const lowTimeThreshold = Math.max(3, Math.floor(timerSeconds / 6));
  const initialsCountLabel =
    initialsPlayerCount === 1 ? '1 player has these initials' : `${initialsPlayerCount} players have these initials`;

  const revealsByInitials = new Map(reveals.map((entry) => [entry.initials, entry.players]));

  return (
    <div className="flex min-h-screen flex-col">
      <SiteNav
        mode={mode}
        onGoHome={goHome}
        onPlaySolo={() => void handleStart()}
        onPlayFriends={() => {
          setMode('versus');
          setPhase('idle');
        }}
        onOpenStats={() => {
          setMode('stats');
          setPhase('idle');
        }}
        onScrollAbout={scrollAbout}
        enabled={leaderboardEnabled}
        user={user}
        session={session}
        authLoading={authLoading}
        signInWithGoogle={signInWithGoogle}
        signOut={signOut}
        profileRefreshKey={profileRefreshKey}
      />

      {mode === 'stats' ? (
        <CareerStatsPage
          enabled={leaderboardEnabled}
          user={user}
          session={session}
          authLoading={authLoading}
          signInWithGoogle={() => signInWithGoogle()}
          refreshKey={profileRefreshKey}
          onBack={goHome}
        />
      ) : mode === 'home' ? (
        <>
          <LandingHero
            playerCount={playerCount}
            timerSeconds={timerSeconds}
            onPlaySolo={() => void handleStart()}
            onPlayFriends={() => setMode('versus')}
          />
          <AboutSection />
          {leaderboardEnabled && (
            <section className="border-t border-white/5 py-16">
              <div className="mx-auto max-w-6xl px-4 sm:px-6">
                <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.35em] text-accent">Standings</p>
                    <h2 className="mt-2 font-display text-4xl tracking-wide text-white">Leaderboard</h2>
                  </div>
                  {submitNotice && (
                    <p className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-300">
                      {submitNotice}
                    </p>
                  )}
                </div>
                <div className="mx-auto max-w-lg">
                  <LeaderboardPanel accessToken={session?.access_token} refreshKey={leaderboardRefreshKey} />
                </div>
              </div>
            </section>
          )}
          <footer className="border-t border-white/5 py-8 text-center text-xs text-slate-600">
            Faster answers = more points · Up to {timerSeconds} pts per correct guess
          </footer>
        </>
      ) : (
        <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-4 py-8 sm:px-6 sm:py-10">
          <section className="card flex flex-1 flex-col p-6 sm:p-8 animate-slide-up">
            {mode === 'versus' ? (
              <MultiplayerRoom
                onExit={goHome}
                onMatchFinished={() => setProfileRefreshKey((value) => value + 1)}
              />
            ) : loading && phase === 'idle' ? (
              <p className="text-center text-slate-400">Loading players...</p>
            ) : (
              <>
                {phase === 'playing' && (
                  <>
                    <div className="mb-8 flex items-center justify-between gap-4">
                      <div>
                        <p className="text-xs uppercase tracking-wider text-slate-500">Score</p>
                        <p className="font-display text-4xl text-white">{score}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-xs uppercase tracking-wider text-slate-500">Streak</p>
                        <p className="font-display text-4xl text-accent">{streak}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs uppercase tracking-wider text-slate-500">Time</p>
                        <p
                          className={`font-display text-4xl ${
                            timeLeft <= lowTimeThreshold ? 'text-red-400' : 'text-white'
                          }`}
                        >
                          {timeLeft}s
                        </p>
                      </div>
                    </div>

                    <div className="mb-8 h-2 overflow-hidden rounded-full bg-court-800">
                      <div
                        className={`h-full transition-all duration-1000 ease-linear ${
                          timeLeft <= lowTimeThreshold ? 'bg-red-500' : 'bg-accent'
                        }`}
                        style={{ width: `${timerPct}%` }}
                      />
                    </div>

                    <div className="mb-8 text-center">
                      <p className="text-sm uppercase tracking-widest text-slate-500">Initials</p>
                      <p className="mt-2 font-display text-7xl tracking-widest text-white sm:text-8xl">
                        {initials}
                      </p>
                      {initialsPlayerCount > 0 && (
                        <p className="mt-3 text-sm text-slate-400">{initialsCountLabel}</p>
                      )}
                      {correctFlash ? (
                        <div className="correct-flash mx-auto mt-5 max-w-md rounded-2xl border border-emerald-400/40 bg-emerald-500/15 px-4 py-4">
                          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-emerald-300">
                            Correct · +{correctFlash.points}
                          </p>
                          <p className="mt-2 text-xl font-semibold text-white sm:text-2xl">
                            {correctFlash.name}
                          </p>
                        </div>
                      ) : (
                        message && <p className="mt-3 text-sm text-emerald-400">{message}</p>
                      )}
                    </div>

                    <form onSubmit={(e) => void handleSubmit(e)} className="mt-auto">
                      <label htmlFor="guess" className="sr-only">
                        Player name
                      </label>
                      <input
                        ref={inputRef}
                        id="guess"
                        type="text"
                        value={guess}
                        onChange={(e) => setGuess(e.target.value)}
                        disabled={submitting || Boolean(correctFlash)}
                        autoComplete="off"
                        placeholder="Type full name (e.g. Michael Jordan)"
                        className="w-full rounded-xl border border-white/10 bg-court-950/80 px-4 py-4 text-lg text-white placeholder:text-slate-600 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30 disabled:opacity-50"
                      />
                      <button
                        type="submit"
                        disabled={submitting || !guess.trim() || Boolean(correctFlash)}
                        className="btn-primary mt-4 w-full py-3 text-lg disabled:opacity-50"
                      >
                        {submitting ? 'Checking...' : 'Submit'}
                      </button>
                    </form>
                  </>
                )}

                {phase === 'gameover' && (
                  <div className="flex flex-1 flex-col">
                    <div className="text-center">
                      <p className="text-sm uppercase tracking-wider text-red-400">Game Over</p>
                      <p className="mt-2 text-2xl font-bold text-white">{message}</p>
                      <p className="mt-4 font-display text-5xl text-accent">{score} pts</p>
                      <p className="mt-1 text-slate-400">{streak} correct in a row</p>

                      {leaderboardEnabled && (
                        <div className="mt-6 w-full max-w-md text-left">
                          {authLoading || submittingScore ? (
                            <p className="text-sm text-slate-400">Saving score...</p>
                          ) : user ? (
                            <div className="space-y-2">
                              <p className="text-sm text-slate-300">
                                Signed in as{' '}
                                <span className="text-white">
                                  {user.user_metadata?.user_name ??
                                    user.user_metadata?.full_name ??
                                    user.email ??
                                    'Player'}
                                </span>
                              </p>
                              {leaderboardMessage && (
                                <p className="text-sm text-emerald-400">{leaderboardMessage}</p>
                              )}
                            </div>
                          ) : (
                            <div className="space-y-3">
                              <p className="text-sm text-slate-400">
                                Sign in with Google to save this score to the leaderboard.
                              </p>
                              <button
                                type="button"
                                onClick={() => void signInWithGoogle(score)}
                                className="btn-primary w-full py-3"
                              >
                                Sign in with Google
                              </button>
                            </div>
                          )}

                          <div className="mt-6">
                            <LeaderboardPanel
                              accessToken={session?.access_token}
                              refreshKey={leaderboardRefreshKey}
                            />
                          </div>
                        </div>
                      )}
                    </div>

                    {sessionRounds.length > 0 && (
                      <div className="mt-8 space-y-6 border-t border-white/10 pt-6">
                        <p className="text-xs uppercase tracking-wider text-slate-500">Round Recap</p>
                        {sessionRounds.map((round, index) => {
                          const players = revealsByInitials.get(round.initials) ?? [];
                          return (
                            <div
                              key={`${round.initials}-${index}`}
                              className="rounded-xl border border-white/10 bg-court-950/50 p-4"
                            >
                              <div className="flex flex-wrap items-baseline justify-between gap-2">
                                <p className="font-display text-2xl tracking-widest text-white">
                                  {round.initials}
                                </p>
                                <p className="text-sm text-slate-400">
                                  {round.success
                                    ? `Answered in ${round.time_spent}s · +${round.points} pts`
                                    : round.guess
                                      ? `Failed after ${round.time_spent}s`
                                      : `Timed out after ${round.time_spent}s`}
                                </p>
                              </div>

                              <p className="mt-2 text-sm text-slate-300">
                                {round.success ? (
                                  <>
                                    <span className="text-emerald-400">✓</span> {round.matched_name}
                                  </>
                                ) : round.guess ? (
                                  <>
                                    <span className="text-red-400">✗</span> Guessed: {round.guess}
                                  </>
                                ) : (
                                  <span className="text-red-400">✗ No answer submitted</span>
                                )}
                              </p>

                              {players.length > 0 && (
                                <div className="mt-3">
                                  <p className="text-xs uppercase tracking-wider text-slate-500">
                                    {players.length === 1
                                      ? '1 valid player'
                                      : `${players.length} valid players`}
                                  </p>
                                  <ul className="mt-2 max-h-48 space-y-2 overflow-y-auto text-sm">
                                    {players.map((player) => (
                                      <li
                                        key={player.full_name}
                                        className={`flex items-start justify-between gap-3 ${
                                          round.success && player.full_name === round.matched_name
                                            ? 'text-emerald-400'
                                            : 'text-slate-400'
                                        }`}
                                      >
                                        <span
                                          className={
                                            round.success && player.full_name === round.matched_name
                                              ? 'font-medium'
                                              : ''
                                          }
                                        >
                                          {player.full_name}
                                        </span>
                                        <span className="shrink-0 text-xs text-slate-500">
                                          {player.career_span}
                                        </span>
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}

                    <div className="mx-auto mt-8 flex flex-wrap justify-center gap-3">
                      <button
                        type="button"
                        onClick={() => void handleStart()}
                        className="btn-primary px-8 py-3"
                      >
                        Play Again
                      </button>
                      <button type="button" onClick={goHome} className="btn-ghost px-8 py-3">
                        Back to home
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}

            {error && (
              <p className="mt-6 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                {error}
              </p>
            )}
          </section>
        </main>
      )}

      {mode === 'home' && error && (
        <p className="mx-auto mb-8 max-w-lg rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-center text-sm text-red-300">
          {error}
        </p>
      )}

      {mode === 'home' && loading && (
        <p className="sr-only" aria-live="polite">
          Loading players...
        </p>
      )}
    </div>
  );
}
