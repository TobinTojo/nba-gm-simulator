import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '@/api/client';
import { useCareer } from '@/context/CareerContext';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { TeamSelectionCard } from '@/components/TeamSelectionCard';
import type { TeamSummary } from '@/types';

export function NewCareerPage() {
  const navigate = useNavigate();
  const { setActiveCareer } = useCareer();
  const [teams, setTeams] = useState<TeamSummary[]>([]);
  const [selectedTeamId, setSelectedTeamId] = useState<number | null>(null);
  const [careerName, setCareerName] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadTeams() {
      try {
        const data = await api.getTeams();
        setTeams(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load teams');
      } finally {
        setLoading(false);
      }
    }
    void loadTeams();
  }, []);

  const selectedTeam = teams.find((t) => t.id === selectedTeamId);

  useEffect(() => {
    if (selectedTeam && !careerName) {
      setCareerName(`${selectedTeam.city} ${selectedTeam.name} GM`);
    }
  }, [selectedTeam, careerName]);

  async function handleStartCareer() {
    if (!selectedTeamId || !careerName.trim()) return;

    setSubmitting(true);
    setError(null);
    try {
      setActiveCareer(null);
      try {
        await api.deleteCareer(1);
      } catch {
        // No existing save — starting fresh is fine.
      }
      const career = await api.createCareer({
        team_id: selectedTeamId,
        career_name: careerName.trim(),
      });
      setActiveCareer(career);
      navigate('/hub');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create career');
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return <LoadingSpinner message="Loading NBA teams..." />;
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">New Career</h1>
        <p className="mt-2 text-slate-400">
          Select a franchise to manage. Review cap space, young talent, and difficulty before you commit.
        </p>
      </div>

      {error && (
        <div className="mb-6 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="grid gap-4 sm:grid-cols-2">
            {teams.map((team) => (
              <TeamSelectionCard
                key={team.id}
                team={team}
                selected={selectedTeamId === team.id}
                onSelect={() => setSelectedTeamId(team.id)}
              />
            ))}
          </div>
        </div>

        <div className="card sticky top-28 h-fit p-6">
          <h2 className="text-lg font-bold text-white">Career Setup</h2>

          {selectedTeam ? (
            <div className="mt-4 space-y-4">
              <div>
                <p className="stat-label">Selected Team</p>
                <p className="mt-1 text-xl font-bold text-white">
                  {selectedTeam.city} {selectedTeam.name}
                </p>
              </div>

              <div>
                <label htmlFor="career-name" className="stat-label">
                  Career Name
                </label>
                <input
                  id="career-name"
                  type="text"
                  value={careerName}
                  onChange={(e) => setCareerName(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-court-600 bg-court-800 px-3 py-2 text-white focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                />
              </div>

              <p className="text-xs text-slate-500">
                One save slot — starting a new career replaces any existing save.
              </p>

              <button
                type="button"
                onClick={() => void handleStartCareer()}
                disabled={submitting || !careerName.trim()}
                className="btn-primary w-full"
              >
                {submitting ? 'Starting Career...' : 'Start Career'}
              </button>
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-500">Select a team to configure your career.</p>
          )}
        </div>
      </div>
    </div>
  );
}
