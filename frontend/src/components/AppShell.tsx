import { Link, useLocation } from 'react-router-dom';
import { useCareer } from '@/context/CareerContext';

const navItems = [
  { to: '/', label: 'Home', requiresCareer: false },
  { to: '/hub', label: 'Hub', requiresCareer: true },
  { to: '/trades', label: 'Trades', requiresCareer: true },
  { to: '/free-agency', label: 'Free Agency', requiresCareer: true },
  { to: '/cap-sheet', label: 'Cap', requiresCareer: true },
  { to: '/standings', label: 'Standings', requiresCareer: true },
  { to: '/playoffs', label: 'Playoffs', requiresCareer: true },
  { to: '/awards', label: 'Awards', requiresCareer: true },
  { to: '/analytics', label: 'Analytics', requiresCareer: true },
  { to: '/settings', label: 'Settings', requiresCareer: false },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const { activeCareer } = useCareer();

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-50 border-b border-court-700/80 bg-court-950/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <Link to="/" className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent/20">
              <span className="text-lg">🏀</span>
            </div>
            <div>
              <p className="font-display text-sm font-bold tracking-wide text-white">NBA GM</p>
              <p className="text-xs text-slate-500">Simulator · Phase 4</p>
            </div>
          </Link>

          {activeCareer && (
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium text-white">{activeCareer.name}</p>
              <p className="text-xs text-slate-400">
                {activeCareer.team.city} {activeCareer.team.name} · {activeCareer.season} ·{' '}
                {activeCareer.phase.replace(/_/g, ' ')} · Security {activeCareer.job_security?.toFixed(0) ?? 75}%
              </p>
            </div>
          )}
        </div>

        <nav className="mx-auto max-w-7xl overflow-x-auto px-4 pb-2">
          <ul className="flex gap-1">
            {navItems.map((item) => {
              const disabled = item.requiresCareer && !activeCareer;
              const isActive =
                location.pathname === item.to ||
                (item.to === '/hub' && location.pathname.startsWith('/players/'));

              if (disabled) {
                return (
                  <li key={item.to}>
                    <span className="inline-block cursor-not-allowed rounded-lg px-3 py-2 text-sm text-slate-600">
                      {item.label}
                    </span>
                  </li>
                );
              }

              return (
                <li key={item.to}>
                  <Link
                    to={item.to}
                    className={`inline-block whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition ${
                      isActive
                        ? 'bg-accent/20 text-accent-light'
                        : 'text-slate-400 hover:bg-court-800 hover:text-white'
                    }`}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8">{children}</main>
    </div>
  );
}
