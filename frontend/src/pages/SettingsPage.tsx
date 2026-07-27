import { useEffect, useState } from 'react';
import { api } from '@/api/client';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import type { HealthResponse, SeedResponse } from '@/types';

export function SettingsPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [seedResult, setSeedResult] = useState<SeedResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function checkHealth() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.health();
      setHealth(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Backend unreachable');
      setHealth(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void checkHealth();
  }, []);

  async function handleReloadRosters() {
    setSeeding(true);
    setSeedResult(null);
    setError(null);
    try {
      const result = await api.reloadRosters();
      setSeedResult(result);
      await checkHealth();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Roster reload failed');
    } finally {
      setSeeding(false);
    }
  }

  async function handleRefreshSalaries() {
    setSeeding(true);
    setSeedResult(null);
    setError(null);
    try {
      const result = await api.refreshSalaries();
      setSeedResult(result);
      await checkHealth();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Salary refresh failed');
    } finally {
      setSeeding(false);
    }
  }

  async function handleSeed(force: boolean) {
    setSeeding(true);
    setSeedResult(null);
    setError(null);
    try {
      const result = await api.seedDatabase(force);
      setSeedResult(result);
      await checkHealth();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Seed failed');
    } finally {
      setSeeding(false);
    }
  }

  return (
    <div className="animate-fade-in max-w-2xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Settings</h1>
        <p className="mt-2 text-slate-400">Backend connection and database management.</p>
      </div>

      {loading ? (
        <LoadingSpinner message="Checking API connection..." />
      ) : (
        <div className="space-y-6">
          <div className="card p-6">
            <h2 className="text-lg font-bold text-white">API Status</h2>
            {health ? (
              <dl className="mt-4 space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-slate-400">Status</dt>
                  <dd className="font-medium text-emerald-400">{health.status}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-400">Application</dt>
                  <dd className="text-white">{health.app}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-400">Database Seeded</dt>
                  <dd className={health.database_seeded ? 'text-emerald-400' : 'text-amber-400'}>
                    {health.database_seeded ? 'Yes' : 'No'}
                  </dd>
                </div>
                {health.has_placeholder_rosters && (
                  <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-amber-300">
                    Placeholder rosters detected (fake names like Marcus Thomas). Click{' '}
                    <strong>Load Real NBA Rosters</strong> below.
                  </div>
                )}
              </dl>
            ) : (
              <p className="mt-4 text-sm text-red-300">
                Cannot reach the FastAPI backend. Make sure it is running on port 8000.
              </p>
            )}

            <button type="button" onClick={() => void checkHealth()} className="btn-secondary mt-4">
              Refresh Status
            </button>
          </div>

          <div className="card p-6">
            <h2 className="text-lg font-bold text-white">NBA Rosters</h2>
            <p className="mt-2 text-sm text-slate-400">
              You do <strong className="text-white">not</strong> need the <code className="text-accent">nba_api</code> Python
              package. The game loads real players from:
            </p>
            <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-slate-400">
              <li><strong className="text-white">stats.nba.com</strong> (live, no extra deps)</li>
              <li><strong className="text-white">Bundled 2025-26 snapshot</strong> (offline fallback)</li>
              <li><strong className="text-white">nba_api</strong> (optional, needs pandas)</li>
            </ol>
            {health?.has_placeholder_rosters && (
              <p className="mt-3 text-sm text-amber-400">
                Your database has <strong className="text-white">fake generated players</strong> from an
                old failed load. Refresh Salaries will <em>not</em> fix names — you must load real rosters.
              </p>
            )}
            <div className="mt-4 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => void handleReloadRosters()}
                disabled={seeding}
                className="btn-primary"
              >
                {seeding ? 'Loading rosters...' : 'Load Real NBA Rosters'}
              </button>
              <button
                type="button"
                onClick={() => void handleRefreshSalaries()}
                disabled={seeding || health?.has_placeholder_rosters}
                className="btn-secondary"
              >
                {seeding ? 'Refreshing...' : 'Refresh Salaries'}
              </button>
              <button
                type="button"
                onClick={() => void handleSeed(true)}
                disabled={seeding}
                className="btn-secondary"
              >
                Full Reset
              </button>
            </div>
            <p className="mt-3 text-xs text-slate-500">
              <strong className="text-slate-400">Load Real NBA Rosters</strong> replaces fake names with real
              2025-26 players and keeps your career. <strong className="text-slate-400">Full Reset</strong> wipes
              everything including career saves.
            </p>
          </div>

          {seedResult && (
            <div className={`rounded-lg border px-4 py-3 text-sm ${
              seedResult.roster_source.includes('placeholder')
                ? 'border-amber-500/40 bg-amber-500/10 text-amber-300'
                : 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
            }`}>
              <p>{seedResult.message}</p>
              <p className="mt-1 text-xs opacity-80">
                Source: {seedResult.roster_source} · {seedResult.player_count} players
              </p>
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
              {error}
            </div>
          )}

          <div className="card p-6">
            <h2 className="text-lg font-bold text-white">About</h2>
            <p className="mt-2 text-sm text-slate-400">
              NBA GM Simulator · Phase 4 — Per-career league state, trades, extensions, awards, and more.
              All data stored locally in SQLite.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
