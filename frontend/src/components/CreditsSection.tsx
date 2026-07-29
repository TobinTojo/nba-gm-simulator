export function CreditsSection() {
  return (
    <section id="credits" className="relative scroll-mt-24 border-t border-white/5 py-16 sm:py-20">
      <div className="mx-auto max-w-6xl px-4 text-center sm:px-6">
        <p className="text-xs font-semibold uppercase tracking-[0.35em] text-accent">Credits</p>
        <h2 className="mt-3 font-display text-4xl tracking-wide text-fg sm:text-5xl">Made by</h2>
        <p className="mt-4 text-base text-slate-400 sm:text-lg">
          <a
            href="https://tobintojo.netlify.app/"
            target="_blank"
            rel="noopener noreferrer"
            className="font-semibold text-fg underline decoration-accent/60 underline-offset-4 transition hover:text-accent hover:decoration-accent"
          >
            Tobin Tojo
          </a>
        </p>
        <p className="mt-2 text-sm text-slate-500">Name Rush · Basketball Initials</p>
      </div>
    </section>
  );
}
