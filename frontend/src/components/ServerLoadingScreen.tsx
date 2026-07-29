interface ServerLoadingScreenProps {
  title?: string;
  detail?: string;
}

export function ServerLoadingScreen({
  title = 'Waking up the server',
  detail = 'Render is starting cold. This can take up to a minute the first time.',
}: ServerLoadingScreenProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 py-16 text-center animate-slide-up">
      <div className="relative mb-8 flex h-20 w-20 items-center justify-center">
        <span className="absolute inset-0 rounded-full border-2 border-accent/20" />
        <span className="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-t-accent" />
        <img src="/basketball.png" alt="" className="h-10 w-10 object-contain ball-bounce" />
      </div>
      <p className="text-xs font-semibold uppercase tracking-[0.35em] text-accent">Please wait</p>
      <h2 className="mt-3 font-display text-3xl tracking-wide text-fg sm:text-4xl">{title}</h2>
      <p className="mt-3 max-w-md text-sm leading-relaxed text-slate-400 sm:text-base">{detail}</p>
    </div>
  );
}
