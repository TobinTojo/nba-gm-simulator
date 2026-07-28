import { useSettings } from '@/context/SettingsContext';

interface SettingsMenuProps {
  open: boolean;
  onClose: () => void;
}

export function SettingsMenu({ open, onClose }: SettingsMenuProps) {
  const { soundEnabled, theme, setSoundEnabled, setTheme } = useSettings();

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 px-4 backdrop-blur-sm">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
        className="card w-full max-w-md p-6 shadow-2xl animate-slide-up"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-accent">Settings</p>
            <h2 id="settings-title" className="mt-1 font-display text-3xl tracking-wide text-white">
              Preferences
            </h2>
          </div>
          <button type="button" onClick={onClose} className="btn-ghost px-3 py-1.5 text-sm">
            Close
          </button>
        </div>

        <div className="mt-8 space-y-5">
          <label className="flex items-center justify-between gap-4 rounded-2xl border border-white/10 bg-court-950/40 px-4 py-4">
            <span>
              <span className="block text-sm font-semibold text-white">Sound effects</span>
              <span className="mt-1 block text-xs text-slate-400">Start, countdown, correct, wrong</span>
            </span>
            <button
              type="button"
              role="switch"
              aria-checked={soundEnabled}
              onClick={() => setSoundEnabled(!soundEnabled)}
              className={`relative h-7 w-12 rounded-full transition ${
                soundEnabled ? 'bg-accent' : 'bg-court-700'
              }`}
            >
              <span
                className={`absolute top-0.5 h-6 w-6 rounded-full bg-white transition ${
                  soundEnabled ? 'left-5' : 'left-0.5'
                }`}
              />
            </button>
          </label>

          <label className="flex items-center justify-between gap-4 rounded-2xl border border-white/10 bg-court-950/40 px-4 py-4">
            <span>
              <span className="block text-sm font-semibold text-white">Theme</span>
              <span className="mt-1 block text-xs text-slate-400">Dark is the default look</span>
            </span>
            <div className="flex rounded-full border border-white/10 p-1">
              <button
                type="button"
                onClick={() => setTheme('dark')}
                className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
                  theme === 'dark' ? 'bg-white/15 text-white' : 'text-slate-400'
                }`}
              >
                Dark
              </button>
              <button
                type="button"
                onClick={() => setTheme('light')}
                className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
                  theme === 'light' ? 'bg-white/15 text-white' : 'text-slate-400'
                }`}
              >
                Light
              </button>
            </div>
          </label>
        </div>
      </div>
    </div>
  );
}
