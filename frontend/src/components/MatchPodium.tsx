import type { MultiplayerPlayerState } from '@/types';

interface MatchPodiumProps {
  players: MultiplayerPlayerState[];
}

function Avatar({
  player,
  sizeClass,
}: {
  player: MultiplayerPlayerState | null;
  sizeClass: string;
}) {
  if (!player) {
    return (
      <div
        className={`flex ${sizeClass} items-center justify-center rounded-full border-2 border-dashed border-white/15 bg-court-900/40 text-slate-600`}
      >
        -
      </div>
    );
  }

  if (player.avatar_url) {
    return (
      <img
        src={player.avatar_url}
        alt=""
        className={`${sizeClass} rounded-full border-2 border-accent object-cover shadow-lg shadow-black/40`}
      />
    );
  }

  return (
    <span
      className={`flex ${sizeClass} items-center justify-center rounded-full border-2 border-accent/60 bg-accent/15 font-display text-2xl text-accent`}
    >
      {player.display_name.slice(0, 1).toUpperCase()}
    </span>
  );
}

function PodiumSlot({
  place,
  player,
  heightClass,
  avatarSize,
}: {
  place: 1 | 2 | 3;
  player: MultiplayerPlayerState | null;
  heightClass: string;
  avatarSize: string;
}) {
  const placeLabel = place === 1 ? '1st' : place === 2 ? '2nd' : '3rd';
  const tone =
    place === 1
      ? 'border-accent/50 bg-accent/15'
      : place === 2
        ? 'border-slate-400/30 bg-court-800/80'
        : 'border-amber-700/40 bg-court-900/80';

  return (
    <div className="flex flex-1 flex-col items-center justify-end">
      <Avatar player={player} sizeClass={avatarSize} />
      <p className={`mt-3 max-w-[6.5rem] truncate text-center text-sm font-semibold ${player ? 'text-white' : 'text-slate-600'}`}>
        {player?.display_name ?? 'Empty'}
      </p>
      <p className={`text-xs tabular-nums ${player ? 'text-slate-400' : 'text-slate-600'}`}>
        {player ? `${player.score} pts` : '-'}
      </p>
      <div
        className={`mt-3 flex w-full ${heightClass} flex-col items-center justify-start rounded-t-2xl border border-b-0 pt-3 ${tone}`}
      >
        <span className={`font-display text-2xl ${place === 1 ? 'text-accent' : 'text-white'}`}>
          {placeLabel}
        </span>
      </div>
    </div>
  );
}

export function MatchPodium({ players }: MatchPodiumProps) {
  const ranked = [...players].sort((a, b) => b.score - a.score);
  const first = ranked[0] ?? null;
  const second = ranked[1] ?? null;
  const third = ranked[2] ?? null;

  return (
    <div className="mt-8 w-full max-w-lg">
      <div className="flex items-end gap-2 sm:gap-4">
        <PodiumSlot place={2} player={second} heightClass="h-24 sm:h-28" avatarSize="h-14 w-14 sm:h-16 sm:w-16" />
        <PodiumSlot place={1} player={first} heightClass="h-32 sm:h-40" avatarSize="h-16 w-16 sm:h-20 sm:w-20" />
        <PodiumSlot place={3} player={third} heightClass="h-20 sm:h-24" avatarSize="h-12 w-12 sm:h-14 sm:w-14" />
      </div>
    </div>
  );
}
