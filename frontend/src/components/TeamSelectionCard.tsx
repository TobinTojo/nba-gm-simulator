import type { TeamSummary } from '@/types';
import { DifficultyStars } from './DifficultyStars';

interface TeamSelectionCardProps {
  team: TeamSummary;
  selected: boolean;
  onSelect: () => void;
}

export function TeamSelectionCard({ team, selected, onSelect }: TeamSelectionCardProps) {
  const capLabel =
    team.salary_cap_space >= 0
      ? `$${team.salary_cap_space.toFixed(0)}M`
      : `-$${Math.abs(team.salary_cap_space).toFixed(0)}M`;

  return (
    <button
      type="button"
      onClick={onSelect}
      className={`card w-full p-5 text-left transition hover:border-accent/40 animate-slide-up ${
        selected ? 'border-accent ring-2 ring-accent/30' : ''
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-accent">
            {team.abbreviation}
          </p>
          <h3 className="mt-1 text-xl font-bold text-white">
            {team.city} {team.name}
          </h3>
          <p className="text-sm text-slate-400">
            {team.conference} · {team.division} · {team.wins}-{team.losses}
          </p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-white">{team.overall_rating.toFixed(0)}</p>
          <p className="text-xs text-slate-500">OVR</p>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div>
          <p className="stat-label">Difficulty</p>
          <DifficultyStars rating={team.difficulty_rating} />
        </div>
        <div>
          <p className="stat-label">Cap Space</p>
          <p className="text-sm font-semibold text-white">{capLabel}</p>
        </div>
        <div>
          <p className="stat-label">Young Talent</p>
          <p className="text-sm font-semibold text-emerald-400">{team.young_core_rating}</p>
        </div>
        <div>
          <p className="stat-label">Title Window</p>
          <p className="text-sm font-semibold text-white">{team.championship_window}</p>
        </div>
      </div>
    </button>
  );
}
