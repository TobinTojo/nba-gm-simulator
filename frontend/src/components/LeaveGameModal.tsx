interface LeaveGameModalProps {
  open: boolean;
  score: number;
  onStay: () => void;
  onLeave: () => void;
}

export function LeaveGameModal({ open, score, onStay, onLeave }: LeaveGameModalProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 px-4 backdrop-blur-sm">
      <div role="dialog" aria-modal="true" className="card w-full max-w-md p-6 shadow-2xl animate-slide-up">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-red-300">Leave run?</p>
        <h2 className="mt-2 font-display text-3xl tracking-wide text-white">Score will be saved</h2>
        <p className="mt-3 text-sm leading-relaxed text-slate-300">
          You are already past round 1. Leaving now ends the run and records your current score of{' '}
          <span className="font-semibold text-white">{score} pts</span> so early exits still count.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <button type="button" onClick={onStay} className="btn-primary flex-1 px-4 py-3">
            Keep playing
          </button>
          <button type="button" onClick={onLeave} className="btn-leave flex-1">
            Leave and save
          </button>
        </div>
      </div>
    </div>
  );
}
