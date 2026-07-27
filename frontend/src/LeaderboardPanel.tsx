import { useCallback, useEffect, useState } from 'react';
import { api } from '@/api/client';
import type { LeaderboardEntry } from '@/types';

interface LeaderboardPanelProps {
  accessToken?: string | null;
  title?: string;
  limit?: number;
  refreshKey?: number;
}

export function LeaderboardPanel({
  accessToken,
  title = 'Leaderboard',
  limit = 10,
  refreshKey = 0,
}: LeaderboardPanelProps) {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [enabled, setEnabled] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadLeaderboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.getLeaderboard(limit, accessToken ?? undefined);
      setEnabled(response.enabled);
      setEntries(response.entries);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load leaderboard.');
      setEntries([]);
    } finally {
      setLoading(false);
    }
  }, [accessToken, limit]);

  useEffect(() => {
    void loadLeaderboard();
  }, [loadLeaderboard, refreshKey]);

  if (!enabled) {
    return null;
  }

  return (
    <div className="rounded-xl border border-court-700 bg-court-900/60 p-4">
      <p className="text-xs uppercase tracking-wider text-slate-500">{title}</p>

      {loading ? (
        <p className="mt-3 text-sm text-slate-400">Loading leaderboard...</p>
      ) : error ? (
        <p className="mt-3 text-sm text-red-300">{error}</p>
      ) : entries.length === 0 ? (
        <p className="mt-3 text-sm text-slate-400">No scores yet. Be the first!</p>
      ) : (
        <ol className="mt-3 space-y-2">
          {entries.map((entry) => (
            <li
              key={`${entry.rank}-${entry.display_name}`}
              className={`flex items-center justify-between gap-3 text-sm ${
                entry.is_you ? 'font-medium text-accent' : 'text-slate-300'
              }`}
            >
              <span className="flex min-w-0 items-center gap-3">
                <span className="w-6 shrink-0 text-slate-500">#{entry.rank}</span>
                <span className="truncate">{entry.display_name}</span>
              </span>
              <span className="shrink-0 tabular-nums">{entry.high_score} pts</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
