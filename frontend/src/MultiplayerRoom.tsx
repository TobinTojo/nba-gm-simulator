import { useEffect, useMemo, useRef, useState } from 'react';
import { api } from '@/api/client';
import type { MultiplayerRoomResponse } from '@/types';

const PLAYER_ID_KEY = 'nbaNameRushPlayerId';
const DISPLAY_NAME_KEY = 'nbaNameRushDisplayName';

function getOrCreatePlayerId(): string {
  const existing = localStorage.getItem(PLAYER_ID_KEY);
  if (existing && existing.length >= 8) return existing;
  const id =
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : `player-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  localStorage.setItem(PLAYER_ID_KEY, id);
  return id;
}

interface MultiplayerRoomProps {
  onExit: () => void;
}

export function MultiplayerRoom({ onExit }: MultiplayerRoomProps) {
  const playerId = useMemo(() => getOrCreatePlayerId(), []);
  const [displayName, setDisplayName] = useState(
    () => localStorage.getItem(DISPLAY_NAME_KEY) || '',
  );
  const [joinCode, setJoinCode] = useState('');
  const [room, setRoom] = useState<MultiplayerRoomResponse | null>(null);
  const [guess, setGuess] = useState('');
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!room || room.status === 'finished') return;

    const interval = window.setInterval(() => {
      void api
        .getMultiplayerRoom(room.code, playerId)
        .then((next) => setRoom(next))
        .catch(() => {
          /* keep last known room state while polling */
        });
    }, 800);

    return () => window.clearInterval(interval);
  }, [room?.code, room?.status, playerId]);

  useEffect(() => {
    if (room?.status === 'playing') {
      inputRef.current?.focus();
    }
  }, [room?.status, room?.current_initials]);

  async function handleCreate() {
    const name = displayName.trim();
    if (!name) {
      setError('Enter a display name first.');
      return;
    }
    localStorage.setItem(DISPLAY_NAME_KEY, name);
    setBusy(true);
    setError(null);
    try {
      const created = await api.createMultiplayerRoom(playerId, name);
      setRoom(created);
      setFeedback('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create room.');
    } finally {
      setBusy(false);
    }
  }

  async function handleJoin() {
    const name = displayName.trim();
    if (!name) {
      setError('Enter a display name first.');
      return;
    }
    if (!joinCode.trim()) {
      setError('Enter a room code.');
      return;
    }
    localStorage.setItem(DISPLAY_NAME_KEY, name);
    setBusy(true);
    setError(null);
    try {
      const joined = await api.joinMultiplayerRoom(joinCode.trim().toUpperCase(), playerId, name);
      setRoom(joined);
      setFeedback('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not join room.');
    } finally {
      setBusy(false);
    }
  }

  async function handleGuess(event: React.FormEvent) {
    event.preventDefault();
    if (!room || room.status !== 'playing' || busy || !guess.trim()) return;

    setBusy(true);
    setError(null);
    try {
      const next = await api.submitMultiplayerGuess(room.code, playerId, guess.trim());
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

  if (!room) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center text-center">
        <p className="text-sm uppercase tracking-wider text-accent">Head to Head</p>
        <h2 className="mt-2 font-display text-3xl font-bold text-white">Play a Friend</h2>
        <p className="mt-3 max-w-md text-slate-400">
          Same 10 initials for both of you. First correct answer wins the round.
        </p>

        <label className="mt-8 w-full max-w-sm text-left text-sm text-slate-400">
          Display name
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            maxLength={40}
            placeholder="Your name"
            className="mt-2 w-full rounded-xl border border-court-600 bg-court-900 px-4 py-3 text-white placeholder:text-slate-600 focus:border-accent focus:outline-none"
          />
        </label>

        <div className="mt-6 flex w-full max-w-sm flex-col gap-3">
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
          Back to solo
        </button>
      </div>
    );
  }

  const hostScore = room.host.score;
  const guestScore = room.guest?.score ?? 0;
  const youWon = room.winner_id === playerId;
  const isDraw = room.status === 'finished' && !room.winner_id;

  return (
    <div className="flex flex-1 flex-col">
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
        </div>
        <button type="button" onClick={onExit} className="text-sm text-slate-500 underline hover:text-slate-300">
          Leave
        </button>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-4">
        <div className={`rounded-xl border p-4 ${room.you_are === 'host' ? 'border-accent' : 'border-court-700'}`}>
          <p className="text-xs uppercase tracking-wider text-slate-500">{room.host.display_name}</p>
          <p className="mt-1 text-3xl font-bold text-white">{hostScore}</p>
        </div>
        <div className={`rounded-xl border p-4 ${room.you_are === 'guest' ? 'border-accent' : 'border-court-700'}`}>
          <p className="text-xs uppercase tracking-wider text-slate-500">
            {room.guest?.display_name ?? 'Waiting...'}
          </p>
          <p className="mt-1 text-3xl font-bold text-white">{guestScore}</p>
        </div>
      </div>

      {room.status === 'waiting' && (
        <div className="flex flex-1 flex-col items-center justify-center text-center">
          <p className="text-lg text-slate-300">Waiting for your friend to join...</p>
          <p className="mt-2 text-sm text-slate-500">Share code <span className="text-white">{room.code}</span></p>
          <p className="mt-6 text-sm text-slate-400">{room.last_message}</p>
        </div>
      )}

      {room.status === 'playing' && (
        <>
          <div className="mb-6 text-center">
            <p className="text-xs uppercase tracking-wider text-slate-500">
              Round {room.round_number} / {room.total_rounds}
            </p>
            <p className="mt-2 font-display text-7xl font-bold tracking-widest text-white sm:text-8xl">
              {room.current_initials}
            </p>
            {room.initials_player_count > 0 && (
              <p className="mt-3 text-sm text-slate-400">
                {room.initials_player_count === 1
                  ? '1 player has these initials'
                  : `${room.initials_player_count} players have these initials`}
              </p>
            )}
            <p className="mt-3 text-sm text-emerald-400">{room.last_message}</p>
            {feedback && <p className="mt-2 text-sm text-slate-400">{feedback}</p>}
          </div>

          <form onSubmit={(e) => void handleGuess(e)} className="mt-auto">
            <input
              ref={inputRef}
              type="text"
              value={guess}
              onChange={(e) => setGuess(e.target.value)}
              disabled={busy}
              autoComplete="off"
              placeholder="Type full name"
              className="w-full rounded-xl border border-court-600 bg-court-900 px-4 py-4 text-lg text-white placeholder:text-slate-600 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
            />
            <button
              type="submit"
              disabled={busy || !guess.trim()}
              className="btn-primary mt-4 w-full py-3 text-lg disabled:opacity-50"
            >
              {busy ? 'Checking...' : 'Submit'}
            </button>
          </form>
        </>
      )}

      {room.status === 'finished' && (
        <div className="flex flex-1 flex-col items-center justify-center text-center">
          <p className="text-sm uppercase tracking-wider text-accent">Match Over</p>
          <p className="mt-2 text-3xl font-bold text-white">
            {isDraw ? "It's a draw!" : youWon ? 'You win!' : 'You lose'}
          </p>
          <p className="mt-3 text-lg text-slate-300">
            {hostScore} – {guestScore}
          </p>
          <p className="mt-2 text-sm text-slate-400">{room.last_message}</p>
          <button type="button" onClick={onExit} className="btn-primary mt-8 px-8 py-3">
            Back to menu
          </button>
        </div>
      )}

      {error && <p className="mt-4 text-center text-sm text-red-300">{error}</p>}
    </div>
  );
}
