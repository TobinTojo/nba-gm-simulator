import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '@/api/client';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import type { AwardSummary } from '@/types';

export function AwardsPage() {
  const [awards, setAwards] = useState<AwardSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void api.getAwards().then(setAwards).finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner message="Loading awards..." />;

  const grouped = awards.reduce<Record<string, AwardSummary[]>>((acc, a) => {
    (acc[a.season] ??= []).push(a);
    return acc;
  }, {});

  return (
    <div className="animate-fade-in space-y-6">
      <div>
        <Link to="/hub" className="text-sm text-slate-500 hover:text-accent">← Back to Hub</Link>
        <h1 className="mt-2 text-3xl font-bold text-white">Season Awards</h1>
        <p className="text-slate-400">MVP, DPOY, and All-NBA selections</p>
      </div>

      {Object.keys(grouped).length === 0 ? (
        <div className="card p-8 text-center text-slate-500">
          No awards yet. Complete a season or win the championship to generate awards.
        </div>
      ) : (
        Object.entries(grouped).map(([season, items]) => (
          <div key={season} className="card p-5">
            <h2 className="text-lg font-bold text-white">{season} Season</h2>
            <ul className="mt-4 space-y-2">
              {items.map((a) => (
                <li key={a.id} className="flex justify-between border-b border-court-800/60 pb-2 text-sm">
                  <span className="font-medium text-accent">{a.award_type}</span>
                  <span className="text-white">{a.player_name || 'TBD'}</span>
                </li>
              ))}
            </ul>
          </div>
        ))
      )}
    </div>
  );
}
