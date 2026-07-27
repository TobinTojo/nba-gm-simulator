import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '@/api/client';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import type { PlayoffBracket, PlayoffSimResponse } from '@/types';

export function PlayoffsPage() {
  const [bracket, setBracket] = useState<PlayoffBracket | null>(null);
  const [simResult, setSimResult] = useState<PlayoffSimResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void api.getPlayoffBracket().then(setBracket).finally(() => setLoading(false));
  }, []);

  async function handleSimulate() {
    setBusy(true);
    try {
      const result = await api.simulatePlayoffs();
      setSimResult(result);
      setBracket(result.bracket);
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <LoadingSpinner message="Loading playoff bracket..." />;

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Link to="/hub" className="text-sm text-slate-500 hover:text-accent">← Back to Hub</Link>
          <h1 className="mt-2 text-3xl font-bold text-white">Playoffs</h1>
          <p className="text-slate-400">{bracket?.season ?? ''} Postseason · Play-in included for seeds 7–10</p>
        </div>
        <button type="button" onClick={() => void handleSimulate()} disabled={busy} className="btn-primary">
          {busy ? 'Simulating...' : 'Simulate Round'}
        </button>
      </div>

      {bracket?.champion_name && (
        <div className="card border-accent/40 bg-accent/10 p-6 text-center">
          <p className="text-sm uppercase tracking-wider text-accent">NBA Champion</p>
          <p className="mt-2 text-2xl font-bold text-white">{bracket.champion_name}</p>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card p-4">
          <h2 className="font-bold text-white">Eastern Conference — Round 1</h2>
          <ul className="mt-3 space-y-2">
            {bracket?.east_r1.map((s, i) => (
              <li key={i} className="text-sm text-slate-300">
                {s.team_a} vs {s.team_b}
                {s.winner && <span className="ml-2 text-emerald-400">→ {s.winner}</span>}
              </li>
            ))}
          </ul>
        </div>
        <div className="card p-4">
          <h2 className="font-bold text-white">Western Conference — Round 1</h2>
          <ul className="mt-3 space-y-2">
            {bracket?.west_r1.map((s, i) => (
              <li key={i} className="text-sm text-slate-300">
                {s.team_a} vs {s.team_b}
                {s.winner && <span className="ml-2 text-emerald-400">→ {s.winner}</span>}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {simResult && simResult.series_results.length > 0 && (
        <div className="card p-4">
          <h2 className="font-bold text-white">Latest Results — {simResult.round_name}</h2>
          <ul className="mt-3 space-y-2">
            {simResult.series_results.map((s, i) => (
              <li key={i} className="text-sm text-slate-300">
                {s.team_a} vs {s.team_b}: <span className="text-white">{s.winner}</span> wins {s.score}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
