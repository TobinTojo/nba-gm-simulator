import { AnimatedBasketball } from '@/components/AnimatedBasketball';

interface LandingHeroProps {
  playerCount: number;
  timerSeconds: number;
  onPlaySolo: () => void;
  onPlayFriends: () => void;
}

export function LandingHero({
  playerCount,
  timerSeconds,
  onPlaySolo,
  onPlayFriends,
}: LandingHeroProps) {
  return (
    <section className="relative isolate min-h-[calc(100svh-4rem)] overflow-hidden">
      <div className="hero-atmosphere" aria-hidden="true" />
      <div className="hero-court-lines" aria-hidden="true" />

      <div className="relative mx-auto grid max-w-6xl items-center gap-10 px-4 pb-20 pt-10 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:gap-6 lg:pb-24 lg:pt-16">
        <div className="animate-slide-up">
          <p className="font-display text-5xl leading-[0.92] tracking-wide text-fg sm:text-7xl lg:text-8xl">
            NAME
            <span className="block text-accent">RUSH</span>
          </p>
          <p className="mt-5 max-w-md text-base leading-relaxed text-slate-300 sm:text-lg">
            Race the clock against every basketball initial in history, solo or with friends.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
            <button type="button" onClick={onPlaySolo} className="btn-primary px-8 py-3.5 text-base">
              Start Solo
            </button>
            <button type="button" onClick={onPlayFriends} className="btn-ghost px-8 py-3.5 text-base">
              Play with friend(s)
            </button>
          </div>

          <p className="mt-6 text-sm text-slate-500">
            {playerCount || '…'} all-time players · {timerSeconds}s per initials
          </p>
        </div>

        <div className="relative flex min-h-[280px] items-center justify-center animate-fade-in lg:min-h-[420px]">
          <AnimatedBasketball className="w-full max-w-[420px]" />
        </div>
      </div>
    </section>
  );
}
