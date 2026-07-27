import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '@/api/client';
import { useCareer } from '@/context/CareerContext';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import type { CareerSaveDetail } from '@/types';

export function LoadSavePage() {
  const navigate = useNavigate();
  const { setActiveCareer } = useCareer();
  const [saves, setSaves] = useState<CareerSaveDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionSlot, setActionSlot] = useState<number | null>(null);

  async function loadSaves() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getCareers();
      setSaves(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load saves');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadSaves();
  }, []);

  async function handleLoad(slot: number) {
    setActionSlot(slot);
    setError(null);
    try {
      const career = await api.loadCareer(slot);
      setActiveCareer(career);
      navigate('/hub');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load save');
    } finally {
      setActionSlot(null);
    }
  }

  async function handleDelete(slot: number) {
    if (!confirm(`Delete save slot ${slot}? This cannot be undone.`)) return;

    setActionSlot(slot);
    setError(null);
    try {
      await api.deleteCareer(slot);
      await loadSaves();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete save');
    } finally {
      setActionSlot(null);
    }
  }

  if (loading) {
    return <LoadingSpinner message="Loading save slots..." />;
  }

  const occupiedSlots = new Set(saves.map((s) => s.slot));
  const allSlots = Array.from({ length: 10 }, (_, i) => i + 1);

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Load Save</h1>
        <p className="mt-2 text-slate-400">Select a save slot to continue your GM career.</p>
      </div>

      {error && (
        <div className="mb-6 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {allSlots.map((slot) => {
          const save = saves.find((s) => s.slot === slot);
          const isBusy = actionSlot === slot;

          return (
            <div key={slot} className="card p-5">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold uppercase tracking-wider text-slate-400">
                  Slot {slot}
                </p>
                {save?.is_active && (
                  <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-xs font-medium text-emerald-400">
                    Active
                  </span>
                )}
              </div>

              {save ? (
                <>
                  <h3 className="mt-3 text-lg font-bold text-white">{save.name}</h3>
                  <p className="text-sm text-slate-400">
                    {save.team.city} {save.team.name}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Season {save.season} · Day {save.season_day}
                  </p>
                  <div className="mt-4 flex gap-2">
                    <button
                      type="button"
                      onClick={() => void handleLoad(slot)}
                      disabled={isBusy}
                      className="btn-primary flex-1 text-sm"
                    >
                      {isBusy ? 'Loading...' : 'Load'}
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleDelete(slot)}
                      disabled={isBusy}
                      className="btn-secondary text-sm text-red-300"
                    >
                      Delete
                    </button>
                  </div>
                </>
              ) : (
                <p className="mt-4 text-sm text-slate-600">Empty slot</p>
              )}

              {!save && !occupiedSlots.has(slot) && (
                <p className="mt-2 text-xs text-slate-600">Start a new career to use this slot.</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
