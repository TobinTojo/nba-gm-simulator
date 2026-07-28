import { useEffect, useRef, useState } from 'react';
import { api } from '@/api/client';
import { useLeaderboardAuth } from '@/hooks/useLeaderboardAuth';
import { WinnerConfetti } from '@/WinnerConfetti';
import type { MultiplayerRoomResponse } from '@/types';

const ROUND_OPTIONS = [9, 12, 15] as const;
const ERA_OPTIONS = [
  { value: 'all_time', label: 'All-time' },
  { value: '60s', label: '1960s' },
  { value: '70s', label: '1970s' },
  { value: '80s', label: '1980s' },
  { value: '90s', label: '1990s' },
  { value: '2000s', label: '2000s' },
  { value: '2010s', label: '2010s' },
  { value: '2020s', label: '2020s' },
] as const;

interface MultiplayerRoomProps {
  onExit: () => void;
  onMatchFinished?: () => void;
}

export function MultiplayerRoom({ onExit, onMatchFinished }: MultiplayerRoomProps) {
  const { enabled, user, session, authLoading, signInWithGoogle, signOut } = useLeaderboardAuth();
  const [joinCode, setJoinCode] = useState('');
  const [selectedRounds, setSelectedRounds] = useState<(typeof ROUND_OPTIONS)[number]>(9);
  const [selectedEra, setSelectedEra] = useState<(typeof ERA_OPTIONS)[number]['value']>('all_time');
  const [room, setRoom] = useState<MultiplayerRoomResponse | null>(null);
  const [guess, setGuess] = useState('');
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [displayTime, setDisplayTime] = useState(30);
  const [displayCountdown, setDisplayCountdown] = useState(3);
  const inputRef = useRef<HTMLInputElement>(null);

  const accessToken = session?.access_token;
  const playerId = user?.id ?? '';
  const displayName =
    user?.user_metadata?.full_name ??
    user?.user_metadata?.name ??
    user?.user_metadata?.user_name ??
    user?.email?.split('@')[0] ??
    'Player';

  useEffect(() => {
    if (!room || room.status === 'finished' || !accessToken) return;

    const intervalMs = room.status === 'countdown' ? 250 : 800;
    const interval = window.setInterval(() => {
      void api
        .getMultiplayerRoom(room.code, accessToken)
        .then((next) => setRoom(next))
        .catch(() => {
          /* keep last known room state while polling */
        });
    }, intervalMs);

    return () => window.clearInterval(interval);
  }, [room?.code, room?.status, accessToken]);

  const finishedNotifiedRef = useRef(false);

  useEffect(() => {
    if (room?.status === 'finished') {
      if (!finishedNotifiedRef.current) {
        finishedNotifiedRef.current = true;
        onMatchFinished?.();
      }
    } else {
      finishedNotifiedRef.current = false;
    }
  }, [room?.status, onMatchFinished]);

  useEffect(() => {
    if (room?.status === 'playing') {
      inputRef.current?.focus();
    }
  }, [room?.status, room?.current_initials]);

  useEffect(() => {
    if (room?.status !== 'playing' || room.time_left == null) {
      setDisplayTime(room?.round_seconds ?? 30);
      return;
    }
    const base = room.time_left;
    const startedAt = Date.now();
    setDisplayTime(base);
    const interval = window.setInterval(() => {
      const elapsed = Math.floor((Date.now() - startedAt) / 1000);
      setDisplayTime(Math.max(0, base - elapsed));
    }, 200);
    return () => window.clearInterval(interval);
  }, [room?.status, room?.time_left, room?.round_index, room?.round_seconds]);

  useEffect(() => {
    if (room?.status !== 'countdown' || room.countdown_left == null) {
      setDisplayCountdown(room?.countdown_seconds ?? 3);
      return;
    }
    const base = room.countdown_left;
    const startedAt = Date.now();
    setDisplayCountdown(base);
    const interval = window.setInterval(() => {
      const elapsed = Math.floor((Date.now() - startedAt) / 1000);
      setDisplayCountdown(Math.max(0, base - elapsed));
    }, 100);
    return () => window.clearInterval(interval);
  }, [room?.status, room?.countdown_left, room?.countdown_seconds]);

  async function handleCreate() {
    if (!accessToken) return;
    setBusy(true);
    setError(null);
    try {
      const created = await api.createMultiplayerRoom(accessToken, selectedRounds, selectedEra);
      setRoom(created);
      setFeedback('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create room.');
    } finally {
      setBusy(false);
    }
  }

  async function handleJoin() {
    if (!accessToken) return;
    if (!joinCode.trim()) {
      setError('Enter a room code.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const joined = await api.joinMultiplayerRoom(joinCode.trim().toUpperCase(), accessToken);
      setRoom(joined);
      setFeedback('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not join room.');
    } finally {
      setBusy(false);
    }
  }

  async function updateLobbySettings(next: { totalRounds?: number; era?: string }) {
    if (!room || !accessToken || !room.you_are_host || room.status !== 'waiting') return;
    setBusy(true);
    setError(null);
    try {
      const updated = await api.setMultiplayerSettings(room.code, accessToken, next);
      setRoom(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update settings.');
    } finally {
      setBusy(false);
    }
  }

  async function handleStart() {
    if (!room || !accessToken) return;
    setBusy(true);
    setError(null);
    try {
      const started = await api.startMultiplayerMatch(room.code, accessToken);
      setRoom(started);
      setFeedback('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not start match.');
    } finally {
      setBusy(false);
    }
  }

  async function handlePass() {
    if (!room || !accessToken || room.status !== 'playing' || busy || room.you_passed) return;
    setBusy(true);
    setError(null);
    try {
      const next = await api.passMultiplayerRound(room.code, accessToken);
      setRoom(next);
      setFeedback(
        next.pass_count >= next.players.length
          ? 'Everyone passed — skipping round.'
          : `Passed (${next.pass_count}/${next.players.length})`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not pass.');
    } finally {
      setBusy(false);
    }
  }

  async function handleGuess(event: React.FormEvent) {
    event.preventDefault();
    if (!room || !accessToken || room.status !== 'playing' || busy || !guess.trim()) return;

    setBusy(true);
    setError(null);
    try {
      const next = await api.submitMultiplayerGuess(room.code, guess.trim(), accessToken);
      setRoom(next);
      setFeedback(next.your_feedback || '');
      if (next.accepted) {
        setGuess('');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not submit guess.');
    } finally {
      setBusy(false);
    }
  }

  async function copyCode() {
    if (!room) return;
    try {
      await navigator.clipboard.writeText(room.code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  if (!enabled) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center text-center">
        <p className="text-lg text-slate-300">Multiplayer needs Google sign-in configured.</p>
        <button type="button" onClick={onExit} className="mt-8 text-sm text-slate-500 underline">
          Back to home
        </button>
      </div>
    );
  }

  if (authLoading) {
    return <p className="text-center text-slate-400">Checking sign-in...</p>;
  }

  if (!user || !accessToken) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center text-center">
        <p className="text-sm uppercase tracking-wider text-accent">Multiplayer</p>
        <h2 className="mt-2 font-display text-3xl font-bold text-white">Play with Friends</h2>
        <p className="mt-3 max-w-md text-slate-400">
          Everyone must sign in with Google before creating or joining a room (up to 4 players).
        </p>
        <button
          type="button"
          onClick={() => void signInWithGoogle()}
          className="btn-primary mt-8 w-full max-w-sm py-3"
        >
          Sign in with Google
        </button>
        <button type="button" onClick={onExit} className="mt-8 text-sm text-slate-500 underline hover:text-slate-300">
          Back to home
        </button>
      </div>
    );
  }

  if (!room) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center text-center">
        <p className="text-sm uppercase tracking-wider text-accent">Multiplayer</p>
        <h2 className="mt-2 font-display text-4xl tracking-wide text-white">Play with friend(s)</h2>
        <p className="mt-3 max-w-md text-slate-400">
          Up to 4 players. Pick an era, race to name players, and pass only skips when everyone
          passes.
        </p>
        <p className="mt-4 text-sm text-slate-300">
          Signed in as <span className="text-white">{displayName}</span>
        </p>
        <button
          type="button"
          onClick={() => void signOut()}
          className="mt-1 text-xs text-slate-500 underline hover:text-slate-300"
        >
          Sign out
        </button>

        <div className="mt-8 grid w-full max-w-sm gap-3 text-left">
          <label className="text-sm text-slate-400">
            Era
            <select
              value={selectedEra}
              onChange={(e) => setSelectedEra(e.target.value as (typeof ERA_OPTIONS)[number]['value'])}
              className="mt-2 w-full rounded-xl border border-court-600 bg-court-900 px-4 py-3 text-white focus:border-accent focus:outline-none"
            >
              {ERA_OPTIONS.map((era) => (
                <option key={era.value} value={era.value}>
                  {era.label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-slate-400">
            Rounds
            <select
              value={selectedRounds}
              onChange={(e) => setSelectedRounds(Number(e.target.value) as (typeof ROUND_OPTIONS)[number])}
              className="mt-2 w-full rounded-xl border border-court-600 bg-court-900 px-4 py-3 text-white focus:border-accent focus:outline-none"
            >
              {ROUND_OPTIONS.map((rounds) => (
                <option key={rounds} value={rounds}>
                  {rounds} rounds
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="mt-4 flex w-full max-w-sm flex-col gap-3">
          <button
            type="button"
            disabled={busy}
            onClick={() => void handleCreate()}
            className="btn-primary w-full py-3 disabled:opacity-50"
          >
            {busy ? 'Creating...' : 'Create Room'}
          </button>

          <div className="flex gap-2">
            <input
              type="text"
              value={joinCode}
              onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
              maxLength={8}
              placeholder="ROOM CODE"
              className="flex-1 rounded-xl border border-court-600 bg-court-900 px-4 py-3 uppercase tracking-widest text-white placeholder:text-slate-600 focus:border-accent focus:outline-none"
            />
            <button
              type="button"
              disabled={busy}
              onClick={() => void handleJoin()}
              className="rounded-xl border border-court-500 px-4 py-3 text-sm font-medium text-white hover:border-accent disabled:opacity-50"
            >
              Join
            </button>
          </div>
        </div>

        {error && <p className="mt-4 text-sm text-red-300">{error}</p>}

        <button type="button" onClick={onExit} className="mt-8 text-sm text-slate-500 underline hover:text-slate-300">
          Back to home
        </button>
      </div>
    );
  }

  const youWon = room.winner_ids.includes(playerId) && room.winner_ids.length === 1;
  const isDraw = room.status === 'finished' && room.winner_ids.length > 1;
  const youTied = room.status === 'finished' && isDraw && room.winner_ids.includes(playerId);
  const scoreGridClass =
    room.players.length <= 2 ? 'grid-cols-2' : room.players.length === 3 ? 'grid-cols-3' : 'grid-cols-2 sm:grid-cols-4';

  return (
    <div className="flex flex-1 flex-col">
      <WinnerConfetti active={room.status === 'finished' && youWon} />
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wider text-slate-500">Room</p>
          <button
            type="button"
            onClick={() => void copyCode()}
            className="font-display text-2xl font-bold tracking-widest text-white hover:text-accent"
          >
            {room.code}
          </button>
          {copied && <p className="text-xs text-emerald-400">Copied</p>}
          <p className="mt-1 text-xs text-slate-500">
            {room.era_label} · {room.total_rounds} rounds
          </p>
        </div>
        <button type="button" onClick={onExit} className="text-sm text-slate-500 underline hover:text-slate-300">
          Leave
        </button>
      </div>

      <div className={`mb-6 grid gap-3 ${scoreGridClass}`}>
        {room.players.map((player) => (
          <div
            key={player.player_id}
            className={`rounded-xl border p-3 ${player.is_you ? 'border-accent' : 'border-court-700'}`}
          >
            <p className="truncate text-xs uppercase tracking-wider text-slate-500">
              {player.display_name}
              {player.is_host ? ' · Host' : ''}
              {player.has_passed ? ' · Passed' : ''}
            </p>
            <p className="mt-1 text-2xl font-bold text-white">{player.score}</p>
          </div>
        ))}
        {room.status === 'waiting' &&
          Array.from({ length: Math.max(0, room.max_players - room.players.length) }).map((_, index) => (
            <div key={`empty-${index}`} className="rounded-xl border border-dashed border-court-700 p-3">
              <p className="text-xs uppercase tracking-wider text-slate-600">Open slot</p>
              <p className="mt-1 text-2xl font-bold text-slate-700">—</p>
            </div>
          ))}
      </div>

      {room.status === 'waiting' && (
        <div className="flex flex-1 flex-col items-center justify-center text-center">
          <p className="text-lg text-slate-300">
            Lobby · {room.players.length}/{room.max_players} players
          </p>
          <p className="mt-2 text-sm text-slate-500">
            Share code <span className="text-white">{room.code}</span>
          </p>

          {room.you_are_host ? (
            <div className="mt-6 w-full max-w-xs space-y-3">
              <label className="block text-left text-sm text-slate-400">
                Era
                <select
                  value={room.era}
                  disabled={busy}
                  onChange={(e) => void updateLobbySettings({ era: e.target.value })}
                  className="mt-2 w-full rounded-xl border border-court-600 bg-court-900 px-4 py-3 text-white focus:border-accent focus:outline-none disabled:opacity-50"
                >
                  {ERA_OPTIONS.map((era) => (
                    <option key={era.value} value={era.value}>
                      {era.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-left text-sm text-slate-400">
                Rounds
                <select
                  value={room.total_rounds}
                  disabled={busy}
                  onChange={(e) => void updateLobbySettings({ totalRounds: Number(e.target.value) })}
                  className="mt-2 w-full rounded-xl border border-court-600 bg-court-900 px-4 py-3 text-white focus:border-accent focus:outline-none disabled:opacity-50"
                >
                  {ROUND_OPTIONS.map((rounds) => (
                    <option key={rounds} value={rounds}>
                      {rounds} rounds
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                disabled={busy || !room.can_start}
                onClick={() => void handleStart()}
                className="btn-primary w-full py-3 disabled:opacity-50"
              >
                {room.can_start ? 'Start Match' : 'Need at least 2 players'}
              </button>
            </div>
          ) : (
            <p className="mt-6 text-sm text-slate-400">
              Waiting for host · {room.era_label} · {room.total_rounds} rounds
            </p>
          )}

          <p className="mt-6 text-sm text-slate-400">{room.last_message}</p>
        </div>
      )}

      {room.status === 'countdown' && (
        <div className="flex flex-1 flex-col items-center justify-center text-center">
          <p className="text-sm uppercase tracking-[0.3em] text-accent">Get Ready</p>
          <p
            key={displayCountdown}
            className="mt-4 font-display text-8xl font-bold text-white transition-transform duration-200 sm:text-9xl"
            style={{ transform: 'scale(1.05)' }}
          >
            {displayCountdown > 0 ? displayCountdown : 'GO'}
          </p>
          <p className="mt-4 text-slate-400">
            {room.era_label} · {room.total_rounds} rounds
          </p>
          <p className="mt-2 text-sm text-slate-500">Match starts in a moment...</p>
        </div>
      )}

      {room.status === 'playing' && (
        <>
          <div className="mb-4 flex items-center justify-between gap-4">
            <p className="text-xs uppercase tracking-wider text-slate-500">
              Round {room.round_number} / {room.total_rounds} · {room.era_label}
            </p>
            <p
              className={`text-2xl font-bold tabular-nums ${
                displayTime <= 5 ? 'text-red-400' : 'text-white'
              }`}
            >
              {displayTime}s
            </p>
          </div>

          <div className="mb-6 h-2 overflow-hidden rounded-full bg-court-800">
            <div
              className={`h-full transition-all duration-200 ease-linear ${
                displayTime <= 5 ? 'bg-red-500' : 'bg-accent'
              }`}
              style={{
                width: `${Math.max(0, (displayTime / (room.round_seconds || 30)) * 100)}%`,
              }}
            />
          </div>

          <div className="mb-6 text-center">
            <p className="mt-2 font-display text-7xl font-bold tracking-widest text-white sm:text-8xl">
              {room.current_initials}
            </p>
            {room.initials_player_count > 0 && (
              <p className="mt-3 text-sm text-slate-400">
                {room.initials_player_count === 1
                  ? '1 unused player left for these initials'
                  : `${room.initials_player_count} unused players left for these initials`}
              </p>
            )}
            <p className="mt-3 text-sm text-emerald-400">{room.last_message}</p>
            {feedback && <p className="mt-2 text-sm text-slate-400">{feedback}</p>}
            <p className="mt-2 text-xs text-slate-500">
              Passes {room.pass_count}/{room.players.length}
              {room.you_passed ? ' · you passed' : ''}
            </p>
          </div>

          <form onSubmit={(e) => void handleGuess(e)} className="mt-auto">
            <input
              ref={inputRef}
              type="text"
              value={guess}
              onChange={(e) => setGuess(e.target.value)}
              disabled={busy || room.you_passed}
              autoComplete="off"
              placeholder="Type full name"
              className="w-full rounded-xl border border-court-600 bg-court-900 px-4 py-4 text-lg text-white placeholder:text-slate-600 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30 disabled:opacity-50"
            />
            <div className="mt-4 grid grid-cols-2 gap-3">
              <button
                type="button"
                disabled={busy || room.you_passed}
                onClick={() => void handlePass()}
                className="rounded-xl border border-court-500 py-3 text-lg font-medium text-white hover:border-accent disabled:opacity-50"
              >
                {room.you_passed ? 'Passed' : 'Pass'}
              </button>
              <button
                type="submit"
                disabled={busy || room.you_passed || !guess.trim()}
                className="btn-primary py-3 text-lg disabled:opacity-50"
              >
                {busy ? 'Checking...' : 'Submit'}
              </button>
            </div>
          </form>
        </>
      )}

      {room.status === 'finished' && (
        <div className="flex flex-1 flex-col items-center justify-center text-center">
          {youWon ? (
            <>
              <p className="text-sm uppercase tracking-[0.35em] text-accent">Champion</p>
              <p className="mt-3 font-display text-5xl font-bold text-white sm:text-6xl">You win!</p>
              <p className="mt-3 text-lg text-emerald-300">Nice race — that board is yours.</p>
            </>
          ) : youTied ? (
            <>
              <p className="text-sm uppercase tracking-wider text-accent">Draw</p>
              <p className="mt-2 text-4xl font-bold text-white">You tied!</p>
              <p className="mt-2 text-slate-400">Split the crown this time.</p>
            </>
          ) : (
            <>
              <p className="text-sm uppercase tracking-wider text-slate-500">Match Over</p>
              <p className="mt-2 text-4xl font-bold text-white">You lose</p>
              <p className="mt-2 text-slate-400">Rematch and take it back.</p>
            </>
          )}

          <div
            className={`mt-8 w-full max-w-sm space-y-2 rounded-2xl border p-5 ${
              youWon
                ? 'border-accent/50 bg-accent/10'
                : 'border-court-700 bg-court-900/50'
            }`}
          >
            {[...room.players]
              .sort((a, b) => b.score - a.score)
              .map((player, index) => (
                <p
                  key={player.player_id}
                  className={`flex items-center justify-between text-sm ${
                    player.is_you ? 'font-semibold text-white' : 'text-slate-300'
                  }`}
                >
                  <span>
                    #{index + 1} {player.display_name}
                    {player.is_you ? ' (you)' : ''}
                  </span>
                  <span className="tabular-nums">{player.score}</span>
                </p>
              ))}
          </div>

          <p className="mt-4 text-sm text-slate-400">{room.last_message}</p>
          <button type="button" onClick={onExit} className="btn-primary mt-8 px-8 py-3">
            Back to menu
          </button>
        </div>
      )}

      {error && <p className="mt-4 text-center text-sm text-red-300">{error}</p>}
    </div>
  );
}
