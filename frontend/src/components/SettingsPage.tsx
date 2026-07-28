import { useSettings } from '@/context/SettingsContext';

interface SettingsPageProps {
  onBack: () => void;
}

export function SettingsPage({ onBack }: SettingsPageProps) {
  const { soundEnabled, theme, setSoundEnabled, setTheme } = useSettings();

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-4 pb-16 pt-16 sm:px-6 sm:pt-20">
      <div className="animate-slide-up">
        <p className="text-xs font-semibold uppercase tracking-[0.35em] text-accent">Settings</p>
        <h1 className="mt-2 font-display text-5xl tracking-wide text-fg">Preferences</h1>
        <p className="mt-3 text-slate-400">Sound and theme for Name Rush.</p>
      </div>

      <section className="card mt-10 space-y-4 p-6 sm:p-8 animate-slide-up">
        <div className="rounded-2xl border border-white/10 bg-court-950/50 px-4 py-5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-[10px] uppercase tracking-[0.22em] text-slate-500">Sound effects</p>
              <p className="mt-2 text-sm font-semibold text-white">Start, countdown, correct, wrong</p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={soundEnabled}
              onClick={() => setSoundEnabled(!soundEnabled)}
              className={`relative h-7 w-12 shrink-0 rounded-full transition ${
                soundEnabled ? 'bg-accent' : 'bg-court-700'
              }`}
            >
              <span
                className={`absolute top-0.5 h-6 w-6 rounded-full bg-white transition ${
                  soundEnabled ? 'left-5' : 'left-0.5'
                }`}
              />
            </button>
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-court-950/50 px-4 py-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-[10px] uppercase tracking-[0.22em] text-slate-500">Theme</p>
              <p className="mt-2 text-sm font-semibold text-white">Dark is the default look</p>
            </div>
            <div className="flex rounded-full border border-white/15 bg-court-900 p-1">
              <button
                type="button"
                onClick={() => setTheme('dark')}
                className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
                  theme === 'dark' ? 'bg-accent text-court-950' : 'text-white'
                }`}
              >
                Dark
              </button>
              <button
                type="button"
                onClick={() => setTheme('light')}
                className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
                  theme === 'light' ? 'bg-accent text-court-950' : 'text-white'
                }`}
              >
                Light
              </button>
            </div>
          </div>
        </div>

        <button type="button" onClick={onBack} className="btn-ghost mt-4 px-6 py-3">
          Back to home
        </button>
      </section>
    </main>
  );
}
