import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '@/api/client';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import type { FreeAgentSummary } from '@/types';

export function FreeAgencyPage() {
  const [agents, setAgents] = useState<FreeAgentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<FreeAgentSummary | null>(null);
  const [salary, setSalary] = useState(10);
  const [years, setYears] = useState(2);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void api.getFreeAgents().then(setAgents).finally(() => setLoading(false));
  }, []);

  async function handleOffer() {
    if (!selected) return;
    setBusy(true);
    setMessage(null);
    try {
      const result = await api.makeOffer(selected.id, salary, years);
      setMessage(result.message);
      if (result.success) {
        setAgents((prev) => prev.filter((a) => a.id !== selected.id));
        setSelected(null);
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Offer failed');
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <LoadingSpinner message="Loading free agents..." />;

  return (
    <div className="animate-fade-in space-y-6">
      <div>
        <Link to="/hub" className="text-sm text-slate-500 hover:text-accent">← Back to Hub</Link>
        <h1 className="mt-2 text-3xl font-bold text-white">Free Agency</h1>
        <p className="text-slate-400">
          Real NBA free agents not currently on a roster — pulled from league stats. Offers weigh money, success, and market size.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 card overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-court-800/50 text-xs uppercase text-slate-400">
              <tr>
                <th className="px-4 py-3">Player</th>
                <th className="px-4 py-3">Pos</th>
                <th className="px-4 py-3">Age</th>
                <th className="px-4 py-3">OVR</th>
                <th className="px-4 py-3">Desired $</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((fa) => (
                <tr
                  key={fa.id}
                  onClick={() => {
                    setSelected(fa);
                    setSalary(Math.round(fa.desired_salary));
                  }}
                  className={`cursor-pointer border-b border-court-800/60 hover:bg-court-800/40 ${
                    selected?.id === fa.id ? 'bg-accent/10' : ''
                  }`}
                >
                  <td className="px-4 py-3 font-medium text-white">{fa.first_name} {fa.last_name}</td>
                  <td className="px-4 py-3 text-slate-400">{fa.position}</td>
                  <td className="px-4 py-3 text-slate-400">{fa.age}</td>
                  <td className="px-4 py-3 text-accent">{fa.overall_rating.toFixed(0)}</td>
                  <td className="px-4 py-3 text-slate-400">${fa.desired_salary.toFixed(1)}M</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card p-5">
          <h2 className="font-bold text-white">Make Offer</h2>
          {selected ? (
            <div className="mt-4 space-y-4">
              <p className="text-lg text-white">{selected.first_name} {selected.last_name}</p>
              <div>
                <label className="text-xs uppercase text-slate-500">Salary ($M/yr)</label>
                <input type="number" step={0.5} value={salary} onChange={(e) => setSalary(Number(e.target.value))}
                  className="mt-1 w-full rounded border border-court-600 bg-court-800 px-3 py-2 text-white" />
              </div>
              <div>
                <label className="text-xs uppercase text-slate-500">Years</label>
                <input type="number" min={1} max={5} value={years} onChange={(e) => setYears(Number(e.target.value))}
                  className="mt-1 w-full rounded border border-court-600 bg-court-800 px-3 py-2 text-white" />
              </div>
              <button type="button" onClick={() => void handleOffer()} disabled={busy} className="btn-primary w-full">
                {busy ? 'Submitting...' : 'Submit Offer'}
              </button>
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-500">Select a free agent.</p>
          )}
          {message && <p className="mt-4 text-sm text-accent">{message}</p>}
        </div>
      </div>
    </div>
  );
}
