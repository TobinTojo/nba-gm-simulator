import { Link } from 'react-router-dom';
import { useCareer } from '@/context/CareerContext';
import { LoadingSpinner } from '@/components/LoadingSpinner';

export function HomePage() {
  const { activeCareer, loading } = useCareer();

  if (loading) {
    return <LoadingSpinner message="Checking for saved career..." />;
  }

  return (
    <div className="animate-fade-in">
      <section className="relative overflow-hidden rounded-2xl border border-court-600/60 bg-gradient-to-br from-court-900 via-court-900 to-court-800 p-8 sm:p-12">
        <div className="absolute -right-16 -top-16 h-64 w-64 rounded-full bg-accent/10 blur-3xl" />
        <div className="relative max-w-2xl">
          <p className="text-sm font-semibold uppercase tracking-widest text-accent">NBA GM Simulator</p>
          <h1 className="mt-3 font-display text-4xl font-bold tracking-tight text-white sm:text-5xl">
            Run Your Franchise
          </h1>
          <p className="mt-4 text-lg text-slate-300">
            One career, real rosters, trades, free agency, and full season simulation.
          </p>
        </div>
      </section>

      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        {activeCareer ? (
          <Link to="/hub" className="card group p-6 transition hover:border-accent/50">
            <p className="text-sm font-semibold uppercase tracking-wider text-accent">Continue Career</p>
            <h2 className="mt-2 text-2xl font-bold text-white group-hover:text-accent-light">
              {activeCareer.name}
            </h2>
            <p className="mt-2 text-slate-400">
              {activeCareer.team.city} {activeCareer.team.name} · {activeCareer.season}
            </p>
          </Link>
        ) : (
          <div className="card p-6 opacity-60">
            <p className="text-sm font-semibold uppercase tracking-wider text-slate-500">Continue Career</p>
            <h2 className="mt-2 text-xl font-bold text-slate-400">No active career</h2>
            <p className="mt-2 text-sm text-slate-500">Start a new career to begin.</p>
          </div>
        )}

        <Link to="/new-career" className="card group p-6 transition hover:border-accent/50">
          <p className="text-sm font-semibold uppercase tracking-wider text-accent">
            {activeCareer ? 'Start Over' : 'New Career'}
          </p>
          <h2 className="mt-2 text-2xl font-bold text-white group-hover:text-accent-light">
            Choose Your Team
          </h2>
          <p className="mt-2 text-slate-400">
            {activeCareer
              ? 'Starting over replaces your current save.'
              : 'Pick any of 30 NBA franchises and begin your tenure.'}
          </p>
        </Link>

        <Link to="/settings" className="card group p-6 transition hover:border-accent/50 sm:col-span-2">
          <p className="text-sm font-semibold uppercase tracking-wider text-accent">Settings</p>
          <h2 className="mt-2 text-2xl font-bold text-white group-hover:text-accent-light">
            Database & Rosters
          </h2>
          <p className="mt-2 text-slate-400">Load real NBA rosters and manage the local database.</p>
        </Link>
      </div>
    </div>
  );
}
