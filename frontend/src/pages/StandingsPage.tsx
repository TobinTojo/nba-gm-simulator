import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '@/api/client';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import type { StandingsResponse } from '@/types';

function StandingsTable({
  title,
  teams,
  highlightId,
}: {
  title: string;
  teams: StandingsResponse['east'];
  highlightId?: number;
}) {
  return (
    <div className="card overflow-hidden">
      <div className="border-b border-court-700 bg-court-800/50 px-4 py-3">
        <h2 className="font-bold text-white">{title}</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-xs uppercase tracking-wider text-slate-400">
            <tr>
              <th className="px-4 py-2">#</th>
              <th className="px-4 py-2">Team</th>
              <th className="px-4 py-2">W</th>
              <th className="px-4 py-2">L</th>
              <th className="px-4 py-2">PCT</th>
              <th className="px-4 py-2">OVR</th>
            </tr>
          </thead>
          <tbody>
            {teams.map((team) => (
              <tr
                key={team.team_id}
                className={`border-b border-court-800/60 ${
                  team.team_id === highlightId ? 'bg-accent/10' : ''
                }`}
              >
                <td className="px-4 py-2 text-slate-500">{team.seed}</td>
                <td className="px-4 py-2 font-medium text-white">
                  {team.city} {team.name}
                  {team.team_id === highlightId && (
                    <span className="ml-2 text-xs text-accent">You</span>
                  )}
                </td>
                <td className="px-4 py-2">{team.wins}</td>
                <td className="px-4 py-2">{team.losses}</td>
                <td className="px-4 py-2">{(team.win_pct * 100).toFixed(1)}%</td>
                <td className="px-4 py-2 text-accent">{team.overall_rating.toFixed(0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function StandingsPage() {
  const [standings, setStandings] = useState<StandingsResponse | null>(null);
  const [teamId, setTeamId] = useState<number | undefined>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [standingsData, hub] = await Promise.all([
          api.getStandings(),
          api.getTeamHub().catch(() => null),
        ]);
        setStandings(standingsData);
        setTeamId(hub?.team.id);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load standings');
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, []);

  if (loading) return <LoadingSpinner message="Loading standings..." />;
  if (error || !standings) {
    return (
      <div className="card p-8 text-center">
        <p className="text-red-300">{error ?? 'No standings available'}</p>
        <Link to="/hub" className="btn-secondary mt-4 inline-block">
          Back to Hub
        </Link>
      </div>
    );
  }

  return (
    <div className="animate-fade-in space-y-6">
      <div>
        <Link to="/hub" className="text-sm text-slate-500 hover:text-accent">
          ← Back to Team Hub
        </Link>
        <h1 className="mt-2 text-3xl font-bold text-white">League Standings</h1>
        <p className="text-slate-400">{standings.season} Season</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <StandingsTable title="Eastern Conference" teams={standings.east} highlightId={teamId} />
        <StandingsTable title="Western Conference" teams={standings.west} highlightId={teamId} />
      </div>
    </div>
  );
}
