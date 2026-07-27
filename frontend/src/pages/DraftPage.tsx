import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '@/api/client';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import type { DraftBoardResponse, DraftPickResult } from '@/types';

export function DraftPage() {
  const [board, setBoard] = useState<DraftBoardResponse | null>(null);
  const [myTeamId, setMyTeamId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [results, setResults] = useState<DraftPickResult[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const [data, hub] = await Promise.all([api.getDraftBoard(), api.getTeamHub()]);
      setBoard(data);
      setMyTeamId(hub.team.id);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function handleLottery() {
    setBusy(true);
    try {
      const r = await api.runDraftLottery();
      setMessage(r.message);
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function handleAutoDraft() {
    setBusy(true);
    try {
      const picks = await api.autoDraft();
      setResults(picks);
      setMessage(`Drafted ${picks.length} players`);
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function handlePick(prospectId: number, pickId: number) {
    setBusy(true);
    try {
      const result = await api.makeDraftPick(prospectId, pickId);
      setResults((prev) => [...prev, result]);
      setMessage(`Drafted ${result.player_name} at #${result.pick_number}`);
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Pick failed');
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <LoadingSpinner message="Loading draft board..." />;
  if (!board) return null;

  const myPicks = board.team_picks.filter((p) => p.team_id === myTeamId);

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Link to="/hub" className="text-sm text-slate-500 hover:text-accent">← Back to Hub</Link>
          <h1 className="mt-2 text-3xl font-bold text-white">NBA Draft</h1>
          <p className="text-slate-400">{board.season} Draft Class</p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={() => void handleLottery()} disabled={busy} className="btn-secondary">Run Lottery</button>
          <button type="button" onClick={() => void handleAutoDraft()} disabled={busy} className="btn-primary">Auto Draft</button>
        </div>
      </div>

      {message && <p className="text-sm text-accent">{message}</p>}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card p-4">
          <h2 className="font-bold text-white">Top Prospects</h2>
          <div className="mt-3 max-h-96 space-y-3 overflow-y-auto">
            {board.prospects.slice(0, 30).map((p) => (
              <div key={p.id} className="rounded-lg border border-court-700 bg-court-800/40 p-3">
                <div className="flex justify-between">
                  <p className="font-medium text-white">{p.first_name} {p.last_name}</p>
                  <span className="text-accent">OVR {p.overall_rating.toFixed(0)} / POT {p.potential.toFixed(0)}</span>
                </div>
                <p className="text-xs text-slate-400">{p.position} · {p.height} · Age {p.age} · Combine {p.combine_score.toFixed(0)}</p>
                <p className="mt-1 text-sm text-slate-500">{p.scouting_report}</p>
                {myPicks[0] && (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void handlePick(p.id, myPicks[0].pick_id)}
                    className="mt-2 text-xs text-accent hover:underline"
                  >
                    Draft with pick #{myPicks[0].pick_number}
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="card p-4">
          <h2 className="font-bold text-white">Your Picks</h2>
          <ul className="mt-3 space-y-2">
            {myPicks.slice(0, 10).map((pick) => (
              <li key={pick.pick_id} className="text-sm text-slate-300">
                #{pick.pick_number ?? '?'} — Round {pick.round} ({pick.team})
              </li>
            ))}
          </ul>
          {results.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-white">Recent Picks</h3>
              {results.map((r, i) => (
                <p key={i} className="text-sm text-slate-400">#{r.pick_number} {r.player_name} ({r.position})</p>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
