import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '@/api/client';
import { useCareer } from '@/context/CareerContext';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { NewsFeed } from '@/components/NewsFeed';
import { SimulationPanel } from '@/components/SimulationPanel';
import { JobSecurityMeter } from '@/components/JobSecurityMeter';
import { StatCard } from '@/components/StatCard';
import type {
  CareerStatusResponse,
  GameResult,
  NewsItem,
  SimulationMode,
  TeamHubResponse,
} from '@/types';

export function TeamHubPage() {
  const { refreshCareer } = useCareer();
  const [hub, setHub] = useState<TeamHubResponse | null>(null);
  const [status, setStatus] = useState<CareerStatusResponse | null>(null);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [lastGame, setLastGame] = useState<GameResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [offseasonMsg, setOffseasonMsg] = useState<string | null>(null);

  const loadHub = useCallback(async () => {
    setError(null);
    try {
      const [hubData, newsData, statusData] = await Promise.all([
        api.getTeamHub(),
        api.getNews(15),
        api.getCareerStatus(),
      ]);
      setHub(hubData);
      setNews(newsData);
      setStatus(statusData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load team hub');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadHub();
  }, [loadHub]);

  async function handleSimulate(mode: SimulationMode) {
    setSimulating(true);
    setError(null);
    try {
      const result = await api.simulate(mode);
      if (result.last_game) setLastGame(result.last_game);
      await loadHub();
      await refreshCareer();
      const newsData = await api.getNews(15);
      setNews(newsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Simulation failed');
    } finally {
      setSimulating(false);
    }
  }

  async function handleOffseason() {
    setSimulating(true);
    try {
      const result = await api.advanceOffseason();
      setOffseasonMsg(result.message);
      await loadHub();
      await refreshCareer();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Offseason failed');
    } finally {
      setSimulating(false);
    }
  }

  if (loading) {
    return <LoadingSpinner message="Loading team hub..." />;
  }

  if (error && !hub) {
    return (
      <div className="card p-8 text-center animate-fade-in">
        <h2 className="text-xl font-bold text-white">No Active Career</h2>
        <p className="mt-2 text-slate-400">{error}</p>
        <div className="mt-6 flex justify-center gap-3">
          <Link to="/new-career" className="btn-primary">
            New Career
          </Link>
          <Link to="/new-career" className="btn-secondary">
            New Career
          </Link>
        </div>
      </div>
    );
  }

  if (!hub) return null;

  const { team, career, roster } = hub;
  const capLabel =
    team.salary_cap_space >= 0
      ? `$${team.salary_cap_space.toFixed(1)}M`
      : `-$${Math.abs(team.salary_cap_space).toFixed(1)}M`;

  return (
    <div className="animate-fade-in space-y-8">
      <section className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wider text-accent">
            {career.season} · Day {career.season_day} · {career.phase.replace(/_/g, ' ')}
          </p>
          <h1 className="mt-1 text-3xl font-bold text-white">
            {team.city} {team.name}
          </h1>
          <p className="text-slate-400">
            {team.conference} · {team.division} · Record {team.wins}-{team.losses}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/trades" className="btn-secondary text-sm">Trades</Link>
          <Link to="/free-agency" className="btn-secondary text-sm">Free Agency</Link>
          <Link to="/cap-sheet" className="btn-secondary text-sm">Cap Sheet</Link>
          <Link to="/playoffs" className="btn-secondary text-sm">Playoffs</Link>
          <Link to="/analytics" className="btn-secondary text-sm">Analytics</Link>
          <Link to="/awards" className="btn-secondary text-sm">Awards</Link>
        </div>
      </section>

      {status && (
        <JobSecurityMeter
          security={status.job_security}
          status={status.job_status}
          ownerExpectations={status.owner_expectations}
        />
      )}

      {error && (
        <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Team Overall" value={team.overall_rating.toFixed(0)} />
        <StatCard label="Salary Cap Space" value={capLabel} />
        <StatCard label="Team Chemistry" value={`${team.chemistry.toFixed(0)}%`} />
        <StatCard label="Playoff Odds" value={`${(team.playoff_odds * 100).toFixed(0)}%`} />
      </section>

      {career.phase === 'regular_season' && (
        <SimulationPanel
        onSimulate={(mode) => void handleSimulate(mode)}
        simulating={simulating}
        seasonDay={career.season_day}
        />
      )}

      {(career.phase === 'offseason' || career.phase === 'playoffs') && (
        <section className="card p-6">
          <h2 className="text-lg font-bold text-white">Offseason</h2>
          <p className="mt-2 text-sm text-slate-400">
            Advance to the next season — process contract expirations, player development, and reset records.
          </p>
          <button type="button" onClick={() => void handleOffseason()} disabled={simulating} className="btn-primary mt-4">
            Start New Season
          </button>
          {offseasonMsg && <p className="mt-3 text-sm text-emerald-400">{offseasonMsg}</p>}
        </section>
      )}

      {lastGame && (
        <section className="card p-6">
          <h2 className="text-lg font-bold text-white">Last Game Result</h2>
          <p className="mt-2 text-slate-300">
            <span className={lastGame.user_team_won ? 'text-emerald-400' : 'text-red-400'}>
              {lastGame.user_team_won ? 'WIN' : 'LOSS'}
            </span>
            {' · '}
            {lastGame.home_team} {lastGame.home_score} - {lastGame.away_score} {lastGame.away_team}
          </p>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-xs uppercase text-slate-500">{lastGame.home_team}</p>
              <ul className="mt-2 space-y-1 text-sm">
                {lastGame.home_box_score.slice(0, 5).map((p) => (
                  <li key={p.player_id} className="text-slate-300">
                    {p.name}: {p.points}pts {p.rebounds}reb {p.assists}ast
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="text-xs uppercase text-slate-500">{lastGame.away_team}</p>
              <ul className="mt-2 space-y-1 text-sm">
                {lastGame.away_box_score.slice(0, 5).map((p) => (
                  <li key={p.player_id} className="text-slate-300">
                    {p.name}: {p.points}pts {p.rebounds}reb {p.assists}ast
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="lg:col-span-2">
          <h2 className="mb-4 text-xl font-bold text-white">Roster</h2>

          <div className="card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="border-b border-court-700 bg-court-800/50 text-xs uppercase tracking-wider text-slate-400">
                  <tr>
                    <th className="px-4 py-3">Player</th>
                    <th className="px-4 py-3">Pos</th>
                    <th className="px-4 py-3">OVR</th>
                    <th className="px-4 py-3">PPG</th>
                    <th className="px-4 py-3">RPG</th>
                    <th className="px-4 py-3">APG</th>
                    <th className="px-4 py-3">MIN</th>
                    <th className="px-4 py-3">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {roster.slice(0, 12).map((player) => (
                    <tr
                      key={player.id}
                      className="border-b border-court-800/80 transition hover:bg-court-800/40"
                    >
                      <td className="px-4 py-3">
                        <Link
                          to={`/players/${player.id}`}
                          className="font-medium text-white hover:text-accent"
                        >
                          {player.first_name} {player.last_name}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-slate-400">{player.position}</td>
                      <td className="px-4 py-3 font-semibold text-accent">
                        {player.overall_rating.toFixed(0)}
                      </td>
                      <td className="px-4 py-3 text-slate-400">{player.ppg.toFixed(1)}</td>
                      <td className="px-4 py-3 text-slate-400">{player.rpg.toFixed(1)}</td>
                      <td className="px-4 py-3 text-slate-400">{player.apg.toFixed(1)}</td>
                      <td className="px-4 py-3 text-slate-400">
                        {player.minutes_per_game.toFixed(1)}
                      </td>
                      <td className="px-4 py-3">
                        {player.injury_status !== 'Healthy' ? (
                          <span className="text-xs text-red-400">{player.injury_status}</span>
                        ) : player.is_starter ? (
                          <span className="rounded bg-accent/20 px-2 py-0.5 text-xs text-accent-light">
                            Starter
                          </span>
                        ) : player.is_g_league ? (
                          <span className="text-xs text-slate-500">G League</span>
                        ) : (
                          <span className="text-xs text-slate-500">Bench</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section className="card p-5">
          <h2 className="text-lg font-bold text-white">League News</h2>
          <div className="mt-4 max-h-[480px] overflow-y-auto">
            <NewsFeed items={news} compact />
          </div>
        </section>
      </div>
    </div>
  );
}
