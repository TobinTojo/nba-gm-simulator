import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '@/api/client';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import type { ScheduleResponse } from '@/types';

function GameRow({ game, showDay = false }: { game: ScheduleResponse['games'][0]; showDay?: boolean }) {
  const scoreDisplay =
    game.is_played && game.team_score !== null && game.opponent_score !== null
      ? `${game.team_score}-${game.opponent_score}`
      : '—';

  return (
    <div className="flex items-center justify-between border-b border-court-800/60 px-4 py-3 last:border-0">
      <div>
        {showDay && <p className="text-xs text-slate-500">Day {game.season_day}</p>}
        <p className="font-medium text-white">
          {game.is_home ? 'vs' : '@'} {game.opponent_name}
        </p>
        <p className="text-xs text-slate-500">{game.game_date}</p>
      </div>
      <div className="text-right">
        {game.result && (
          <span
            className={`mr-2 rounded px-2 py-0.5 text-xs font-bold ${
              game.result === 'W' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'
            }`}
          >
            {game.result}
          </span>
        )}
        <span className="font-semibold text-slate-300">{scoreDisplay}</span>
      </div>
    </div>
  );
}

export function SchedulePage() {
  const [schedule, setSchedule] = useState<ScheduleResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await api.getSchedule();
        setSchedule(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load schedule');
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, []);

  if (loading) return <LoadingSpinner message="Loading schedule..." />;
  if (error || !schedule) {
    return (
      <div className="card p-8 text-center">
        <p className="text-red-300">{error ?? 'No schedule available'}</p>
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
        <h1 className="mt-2 text-3xl font-bold text-white">Schedule</h1>
        <p className="text-slate-400">
          {schedule.season} · Day {schedule.season_day} · {schedule.games.length} games
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <div className="border-b border-court-700 bg-court-800/50 px-4 py-3">
            <h2 className="font-bold text-white">Recent Games</h2>
          </div>
          {schedule.recent.length === 0 ? (
            <p className="p-4 text-sm text-slate-500">No games played yet.</p>
          ) : (
            schedule.recent.map((game) => <GameRow key={game.id} game={game} />)
          )}
        </div>

        <div className="card">
          <div className="border-b border-court-700 bg-court-800/50 px-4 py-3">
            <h2 className="font-bold text-white">Upcoming Games</h2>
          </div>
          {schedule.upcoming.length === 0 ? (
            <p className="p-4 text-sm text-slate-500">No upcoming games.</p>
          ) : (
            schedule.upcoming.map((game) => <GameRow key={game.id} game={game} showDay />)
          )}
        </div>
      </div>

      <div className="card">
        <div className="border-b border-court-700 bg-court-800/50 px-4 py-3">
          <h2 className="font-bold text-white">Full Schedule</h2>
        </div>
        <div className="max-h-96 overflow-y-auto">
          {schedule.games.map((game) => (
            <GameRow key={game.id} game={game} showDay />
          ))}
        </div>
      </div>
    </div>
  );
}
