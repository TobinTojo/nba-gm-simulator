import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '@/api/client';
import { AttributeChart, RatingHistoryChart, StatTrendChart } from '@/components/PlayerCharts';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { StatCard } from '@/components/StatCard';
import { formatPct } from '@/utils/stats';
import type { PlayerDetail } from '@/types';

export function PlayerPage() {
  const { id } = useParams<{ id: string }>();
  const [player, setPlayer] = useState<PlayerDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      if (!id) return;
      setLoading(true);
      try {
        const data = await api.getPlayer(Number(id));
        setPlayer(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load player');
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [id]);

  if (loading) return <LoadingSpinner message="Loading player profile..." />;
  if (error || !player) {
    return (
      <div className="card p-8 text-center">
        <p className="text-red-300">{error ?? 'Player not found'}</p>
        <Link to="/hub" className="btn-secondary mt-4 inline-block">
          Back to Hub
        </Link>
      </div>
    );
  }

  const attributes = [
    { label: 'Shooting', value: player.shooting },
    { label: 'Defense', value: player.defense },
    { label: 'Playmaking', value: player.playmaking },
    { label: 'Athleticism', value: player.athleticism },
    { label: 'Rebounding', value: player.rebounding },
    { label: 'Basketball IQ', value: player.basketball_iq },
    { label: 'Durability', value: player.durability },
  ];

  const statTrend = player.season_stats
    ? [
        {
          label: 'Season',
          ppg: player.season_stats.ppg,
          rpg: player.season_stats.rpg,
          apg: player.season_stats.apg,
        },
      ]
    : [];

  return (
    <div className="animate-fade-in space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Link to="/hub" className="text-sm text-slate-500 hover:text-accent">
            ← Back to Team Hub
          </Link>
          <h1 className="mt-2 text-3xl font-bold text-white">
            {player.first_name} {player.last_name}
          </h1>
          <p className="text-slate-400">
            {player.team_name} · {player.position} · {player.height} · {player.weight} lbs · Age{' '}
            {player.age}
          </p>
        </div>
        <div className="flex gap-4">
          <div className="card px-5 py-3 text-center">
            <p className="stat-label">Overall</p>
            <p className="text-3xl font-bold text-accent">{player.overall_rating.toFixed(0)}</p>
          </div>
          <div className="card px-5 py-3 text-center">
            <p className="stat-label">Potential</p>
            <p className="text-3xl font-bold text-emerald-400">{player.potential.toFixed(0)}</p>
          </div>
        </div>
      </div>

      {player.injury_status !== 'Healthy' && (
        <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-red-300">
          Injury Status: {player.injury_status}
        </div>
      )}

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Contract" value={`$${player.salary.toFixed(1)}M`} subtext={`${player.years_remaining} yrs left`} />
        <StatCard label="Player Mood" value={`${player.player_mood.toFixed(0)}%`} />
        <StatCard label="Fatigue" value={`${player.fatigue.toFixed(0)}%`} />
        <StatCard label="Development" value={player.development_trend} />
        <StatCard label="Role" value={player.is_starter ? 'Starter' : player.is_g_league ? 'G League' : 'Bench'} />
        <StatCard label="Minutes" value={player.minutes_per_game.toFixed(1)} />
        <StatCard label="TS%" value={`${(player.ts_pct * 100).toFixed(1)}%`} />
        <StatCard label="PER" value={player.per.toFixed(1)} />
      </section>

      {player.season_stats && (
        <section className="grid gap-4 sm:grid-cols-3 lg:grid-cols-6">
          <StatCard label="GP" value={player.season_stats.games_played} />
          <StatCard label="PPG" value={player.season_stats.ppg.toFixed(1)} />
          <StatCard label="RPG" value={player.season_stats.rpg.toFixed(1)} />
          <StatCard label="APG" value={player.season_stats.apg.toFixed(1)} />
          <StatCard label="TS%" value={formatPct(player.season_stats.ts_pct)} />
          <StatCard label="PER" value={player.season_stats.per.toFixed(1)} />
        </section>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card p-6">
          <h2 className="text-lg font-bold text-white">Attributes</h2>
          <div className="mt-4">
            <AttributeChart attributes={attributes} />
          </div>
        </div>

        <div className="card p-6">
          <h2 className="text-lg font-bold text-white">Overall Progression</h2>
          <div className="mt-4">
            <RatingHistoryChart data={player.rating_history} />
          </div>
        </div>
      </div>

      {statTrend.length > 0 && (
        <div className="card p-6">
          <h2 className="text-lg font-bold text-white">Season Stats</h2>
          <div className="mt-4">
            <StatTrendChart data={statTrend} />
          </div>
        </div>
      )}
    </div>
  );
}
