import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '@/api/client';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { StatCard } from '@/components/StatCard';
import type { CapSheetResponse, PlayerSummary } from '@/types';

export function CapSheetPage() {
  const [sheet, setSheet] = useState<CapSheetResponse | null>(null);
  const [expiring, setExpiring] = useState<PlayerSummary[]>([]);
  const [selected, setSelected] = useState<PlayerSummary | null>(null);
  const [salary, setSalary] = useState(10);
  const [years, setYears] = useState(2);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    void Promise.all([api.getCapSheet(), api.getExpiringContracts()]).then(([s, e]) => {
      setSheet(s);
      setExpiring(e);
      setLoading(false);
    });
  }, []);

  async function handleExtend() {
    if (!selected) return;
    try {
      const result = await api.extendContract(selected.id, salary, years);
      setMessage(result.message);
      if (result.success) {
        const [s, e] = await Promise.all([api.getCapSheet(), api.getExpiringContracts()]);
        setSheet(s);
        setExpiring(e);
        setSelected(null);
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Extension failed');
    }
  }

  if (loading) return <LoadingSpinner message="Loading cap sheet..." />;
  if (!sheet) return null;

  return (
    <div className="animate-fade-in space-y-6">
      <div>
        <Link to="/hub" className="text-sm text-slate-500 hover:text-accent">← Back to Hub</Link>
        <h1 className="mt-2 text-3xl font-bold text-white">Salary Cap</h1>
        <p className="text-slate-400">{sheet.team_name}</p>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Salary Cap" value={`$${sheet.salary_cap.toFixed(1)}M`} />
        <StatCard label="Payroll" value={`$${sheet.payroll.toFixed(1)}M`} />
        <StatCard label="Cap Space" value={`$${sheet.cap_space.toFixed(1)}M`} />
        <StatCard label="Luxury Tax" value={`$${sheet.luxury_tax.toFixed(1)}M`} />
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card overflow-hidden">
          <div className="border-b border-court-700 bg-court-800/50 px-4 py-3">
            <h2 className="font-bold text-white">Contracts</h2>
          </div>
          <table className="w-full text-left text-sm">
            <tbody>
              {sheet.contracts.map((c) => (
                <tr key={c.player_id} className="border-b border-court-800/60">
                  <td className="px-4 py-2 text-white">{c.player_name}</td>
                  <td className="px-4 py-2">${c.salary.toFixed(1)}M</td>
                  <td className="px-4 py-2">{c.years_remaining} yr</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card p-5">
          <h2 className="font-bold text-white">Contract Extensions</h2>
          <p className="mt-1 text-sm text-slate-500">Players with expiring deals</p>
          <ul className="mt-3 max-h-40 space-y-1 overflow-y-auto">
            {expiring.map((p) => (
              <li key={p.id}>
                <button type="button" onClick={() => { setSelected(p); setSalary(Math.round(p.salary || p.overall_rating * 0.35)); }}
                  className={`text-sm ${selected?.id === p.id ? 'text-accent' : 'text-slate-300 hover:text-white'}`}>
                  {p.first_name} {p.last_name} (OVR {p.overall_rating.toFixed(0)})
                </button>
              </li>
            ))}
          </ul>
          {selected && (
            <div className="mt-4 space-y-3">
              <input type="number" value={salary} onChange={(e) => setSalary(Number(e.target.value))}
                className="w-full rounded border border-court-600 bg-court-800 px-3 py-2 text-white" placeholder="Salary $M" />
              <input type="number" min={1} max={5} value={years} onChange={(e) => setYears(Number(e.target.value))}
                className="w-full rounded border border-court-600 bg-court-800 px-3 py-2 text-white" placeholder="Years" />
              <button type="button" onClick={() => void handleExtend()} className="btn-primary w-full">Extend Contract</button>
            </div>
          )}
          {message && <p className="mt-3 text-sm text-accent">{message}</p>}
        </div>
      </div>
    </div>
  );
}
