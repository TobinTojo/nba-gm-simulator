import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api } from '@/api/client';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { StatCard } from '@/components/StatCard';
import type { TeamAnalytics } from '@/types';

export function AnalyticsPage() {
  const [team, setTeam] = useState<TeamAnalytics | null>(null);
  const [league, setLeague] = useState<TeamAnalytics[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void Promise.all([api.getTeamAnalytics(), api.getLeagueAnalytics()]).then(([t, l]) => {
      setTeam(t);
      setLeague(l);
      setLoading(false);
    });
  }, []);

  if (loading) return <LoadingSpinner message="Loading analytics..." />;
  if (!team) return null;

  const chartData = [
    { name: 'ORtg', value: team.offensive_rating },
    { name: 'DRtg', value: team.defensive_rating },
    { name: 'Net', value: team.net_rating + 110 },
    { name: 'Pace', value: team.pace },
  ];

  const leagueNet = league
    .sort((a, b) => b.net_rating - a.net_rating)
    .slice(0, 10)
    .map((t) => ({ name: t.team_name.split(' ').pop() ?? t.team_name, net: t.net_rating }));

  return (
    <div className="animate-fade-in space-y-6">
      <div>
        <Link to="/hub" className="text-sm text-slate-500 hover:text-accent">← Back to Hub</Link>
        <h1 className="mt-2 text-3xl font-bold text-white">Advanced Analytics</h1>
        <p className="text-slate-400">{team.team_name}</p>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Offensive Rating" value={team.offensive_rating.toFixed(1)} />
        <StatCard label="Defensive Rating" value={team.defensive_rating.toFixed(1)} />
        <StatCard label="Net Rating" value={team.net_rating.toFixed(1)} />
        <StatCard label="Pace" value={team.pace.toFixed(1)} />
        <StatCard label="True Shooting %" value={`${(team.true_shooting_pct * 100).toFixed(1)}%`} />
        <StatCard label="Effective FG%" value={`${(team.effective_fg_pct * 100).toFixed(1)}%`} />
        <StatCard label="Rebounding %" value={`${team.rebounding_pct.toFixed(1)}%`} />
        <StatCard label="Turnover %" value={`${team.turnover_pct.toFixed(1)}%`} />
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card p-6">
          <h2 className="font-bold text-white">Team Ratings</h2>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#243650" />
              <XAxis dataKey="name" stroke="#64748b" fontSize={12} />
              <YAxis stroke="#64748b" />
              <Tooltip contentStyle={{ background: '#151f2e', border: '1px solid #243650' }} />
              <Bar dataKey="value" fill="#f97316" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-6">
          <h2 className="font-bold text-white">League Net Rating Leaders</h2>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={leagueNet} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#243650" />
              <XAxis type="number" stroke="#64748b" />
              <YAxis type="category" dataKey="name" stroke="#64748b" fontSize={11} width={60} />
              <Tooltip contentStyle={{ background: '#151f2e', border: '1px solid #243650' }} />
              <Bar dataKey="net" fill="#34d399" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
