export function AboutSection() {
  return (
    <section id="about" className="relative scroll-mt-24 border-t border-white/5 py-20 sm:py-28">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(249,115,22,0.08),transparent_55%)]" aria-hidden="true" />
      <div className="relative mx-auto max-w-6xl px-4 sm:px-6">
        <p className="text-xs font-semibold uppercase tracking-[0.35em] text-accent">About</p>
        <h2 className="mt-3 max-w-2xl font-display text-4xl tracking-wide text-fg sm:text-5xl">
          Initials. Instinct. Instant points.
        </h2>
        <p className="mt-4 max-w-2xl text-base leading-relaxed text-slate-400 sm:text-lg">
          Name Rush is a fast basketball trivia race: you see two letters, you name a real player from history,
          and the clock decides how many points you bank. Miss once in solo and the run ends. In friend
          matches, the first correct answer takes the round.
        </p>

        <div className="mt-14 grid gap-10 md:grid-cols-3">
          <article>
            <p className="font-display text-3xl text-accent">01</p>
            <h3 className="mt-3 text-lg font-semibold text-fg">Know the names</h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-400">
              Every all-time basketball player is in the pool. Close spelling still counts when the initials match.
            </p>
          </article>
          <article>
            <p className="font-display text-3xl text-accent">02</p>
            <h3 className="mt-3 text-lg font-semibold text-fg">Beat the clock</h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-400">
              Faster answers earn more points. Each correct guess resets the timer and deals a new set of initials.
            </p>
          </article>
          <article>
            <p className="font-display text-3xl text-accent">03</p>
            <h3 className="mt-3 text-lg font-semibold text-fg">Challenge friends</h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-400">
              Host a private room, pick an era, and race head-to-head. Sole 1v1 wins are tracked on your profile.
            </p>
          </article>
        </div>
      </div>
    </section>
  );
}
