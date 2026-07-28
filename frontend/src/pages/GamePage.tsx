import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '@/api/client';
import { useLeaderboardAuth } from '@/hooks/useLeaderboardAuth';
import { LeaderboardPanel } from '@/LeaderboardPanel';
import type { GamePhase, InitialsRevealEntry, SessionRound } from '@/types';

const DEFAULT_TIMER_SECONDS = 30;

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
  const [submittingScore, setSubmittingScore] = useState(false);

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
    if (phase !== 'gameover' || !leaderboardEnabled || !session?.access_token || score <= 0) {
      return;
    }
    if (submittedScoreRef.current === score) {
      return;
    }

    submittedScoreRef.current = score;
    setSubmittingScore(true);
    void submitScore(score, session.access_token)
      .then((result) => {
        if (result.is_new_best) {
          setLeaderboardMessage(
            result.rank ? `New personal best! Rank #${result.rank}` : 'New personal best saved!',
          );
        } else {
          setLeaderboardMessage(`Your best score remains ${result.high_score} pts`);
        }
        setLeaderboardRefreshKey((value) => value + 1);
      })
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : 'Could not save score to the leaderboard.';
        setLeaderboardMessage(message);
        submittedScoreRef.current = null;
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
        matched_name: '—',
        points: 0,
        time_spent: spent,
        success: false,
      },
      sessionRoundsRef.current,
    );
  }, [finishGame]);

  useEffect(() => {
    if (phase !== 'playing') return;

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
  }, [phase, endGameOnTimeout, timerGeneration]);

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
      submittedScoreRef.current = null;
      setTimerGeneration((n) => n + 1);
      setPhase('playing');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start game');
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (phase !== 'playing' || submitting || !guess.trim()) return;

    setSubmitting(true);
    setError(null);
    const submittedTimeLeft = timeLeftRef.current;
    const timeSpent = timerSeconds - submittedTimeLeft;
    try {
      const result = await api.submitGuess(initials, guess.trim(), usedPlayerIds, submittedTimeLeft);

      if (!result.correct || result.game_over) {
        await finishGame(
          result.reason || 'Wrong answer — game over.',
          {
            initials,
            guess: guess.trim(),
            matched_name: result.matched_name || '—',
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
      setInitials(result.next_initials);
      setInitialsPlayerCount(result.next_initials_player_count);
      setGuess('');
      setTimeLeft(timerSeconds);
      setTimerGeneration((n) => n + 1);
      setMessage(`+${result.points} for ${result.matched_name} (${submittedTimeLeft}s left)`);
    } catch (err) {
      await finishGame(
        err instanceof Error ? err.message : 'Something went wrong.',
        {
          initials,
          guess: guess.trim(),
          matched_name: '—',
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

  const timerPct = (timeLeft / timerSeconds) * 100;
  const lowTimeThreshold = Math.max(3, Math.floor(timerSeconds / 6));
  const initialsCountLabel =
    initialsPlayerCount === 1 ? '1 player has these initials' : `${initialsPlayerCount} players have these initials`;

  const revealsByInitials = new Map(reveals.map((entry) => [entry.initials, entry.players]));

  return (
    <div className="mx-auto flex min-h-screen max-w-3xl flex-col px-4 py-10">
      <header className="mb-10 text-center">
        <p className="text-sm font-semibold uppercase tracking-[0.3em] text-accent">NBA Initials</p>
        <h1 className="mt-2 font-display text-4xl font-bold text-white sm:text-5xl">Name Rush</h1>
        <p className="mt-3 text-slate-400">All-time NBA · {playerCount || '…'} players</p>
      </header>

      <section className="card flex flex-1 flex-col p-6 sm:p-8">
        {loading && phase === 'idle' ? (
          <p className="text-center text-slate-400">Loading players...</p>
        ) : phase === 'idle' ? (
          <div className="flex flex-1 flex-col items-center justify-center text-center">
            <p className="max-w-md text-lg text-slate-300">
              You get <strong className="text-white">{timerSeconds} seconds</strong> per initials. Guess any NBA
              player in history from their <strong className="text-white">initials</strong>. Faster answers earn
              more points.
            </p>
            <ul className="mt-6 space-y-2 text-left text-sm text-slate-400">
              <li>✓ Answer fast → up to {timerSeconds} points per correct name</li>
              <li>✓ Correct name → new initials, timer resets to {timerSeconds}s</li>
              <li>✓ Close spelling still counts if it matches the initials</li>
              <li>✗ Wrong name or invalid player → game over</li>
              <li>✗ Time runs out → game over</li>
            </ul>
            <button type="button" onClick={() => void handleStart()} className="btn-primary mt-8 px-10 py-3 text-lg">
              Start Game
            </button>

            {leaderboardEnabled && (
              <div className="mt-10 w-full max-w-md">
                {submitNotice && (
                  <p className="mb-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
                    {submitNotice}
                  </p>
                )}
                <LeaderboardPanel accessToken={session?.access_token} refreshKey={leaderboardRefreshKey} />
              </div>
            )}
          </div>
        ) : (
          <>
            {phase === 'playing' && (
              <>
                <div className="mb-8 flex items-center justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-wider text-slate-500">Score</p>
                    <p className="text-3xl font-bold text-white">{score}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs uppercase tracking-wider text-slate-500">Streak</p>
                    <p className="text-3xl font-bold text-accent">{streak}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs uppercase tracking-wider text-slate-500">Time</p>
                    <p
                      className={`text-3xl font-bold ${timeLeft <= lowTimeThreshold ? 'text-red-400' : 'text-white'}`}
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
                  <p className="mt-2 font-display text-7xl font-bold tracking-widest text-white sm:text-8xl">
                    {initials}
                  </p>
                  {initialsPlayerCount > 0 && (
                    <p className="mt-3 text-sm text-slate-400">{initialsCountLabel}</p>
                  )}
                  {message && <p className="mt-3 text-sm text-emerald-400">{message}</p>}
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
                    disabled={submitting}
                    autoComplete="off"
                    placeholder="Type full name (e.g. Michael Jordan)"
                    className="w-full rounded-xl border border-court-600 bg-court-900 px-4 py-4 text-lg text-white placeholder:text-slate-600 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
                  />
                  <button
                    type="submit"
                    disabled={submitting || !guess.trim()}
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
                  <p className="mt-4 text-4xl font-bold text-accent">{score} pts</p>
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
                          <button
                            type="button"
                            onClick={() => void signOut()}
                            className="text-xs text-slate-500 underline hover:text-slate-300"
                          >
                            Sign out
                          </button>
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
                  <div className="mt-8 space-y-6 border-t border-court-700 pt-6">
                    <p className="text-xs uppercase tracking-wider text-slate-500">Round Recap</p>
                    {sessionRounds.map((round, index) => {
                      const players = revealsByInitials.get(round.initials) ?? [];
                      return (
                        <div
                          key={`${round.initials}-${index}`}
                          className="rounded-xl border border-court-700 bg-court-900/60 p-4"
                        >
                          <div className="flex flex-wrap items-baseline justify-between gap-2">
                            <p className="font-display text-2xl font-bold tracking-widest text-white">
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

                <button
                  type="button"
                  onClick={() => void handleStart()}
                  className="btn-primary mx-auto mt-8 px-8 py-3"
                >
                  Play Again
                </button>
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

      <p className="mt-6 text-center text-xs text-slate-600">
        Faster answers = more points · Up to {timerSeconds} pts per correct guess
      </p>
    </div>
  );
}
