import type { SimulationMode } from '@/types';

interface SimulationPanelProps {
  onSimulate: (mode: SimulationMode) => void;
  simulating: boolean;
  seasonDay: number;
}

const modes: { mode: SimulationMode; label: string; description: string }[] = [
  { mode: 'game', label: 'Next Game', description: 'Simulate your next game' },
  { mode: 'week', label: 'Sim Week', description: 'Advance 7 days' },
  { mode: 'month', label: 'Sim Month', description: 'Advance 30 days' },
  { mode: 'all_star', label: 'All-Star Break', description: 'Sim to day 60' },
  { mode: 'deadline', label: 'Trade Deadline', description: 'Sim to day 100' },
  { mode: 'playoffs', label: 'End Regular Season', description: 'Sim to day 150' },
  { mode: 'season', label: 'Full Season', description: 'Sim remaining schedule' },
];

export function SimulationPanel({ onSimulate, simulating, seasonDay }: SimulationPanelProps) {
  return (
    <div className="card p-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-white">Season Simulation</h2>
          <p className="text-sm text-slate-400">Currently on day {seasonDay}</p>
        </div>
      </div>
      <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {modes.map(({ mode, label, description }) => (
          <button
            key={mode}
            type="button"
            disabled={simulating}
            onClick={() => onSimulate(mode)}
            className="rounded-lg border border-court-600 bg-court-800/60 px-4 py-3 text-left transition hover:border-accent/50 hover:bg-court-700 disabled:opacity-50"
          >
            <p className="font-semibold text-white">{label}</p>
            <p className="text-xs text-slate-500">{description}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
