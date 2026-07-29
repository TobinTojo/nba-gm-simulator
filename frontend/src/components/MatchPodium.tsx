import type { MultiplayerPlayerState } from '@/types';

interface MatchPodiumProps {
  players: MultiplayerPlayerState[];
}

function avatarSizeForCount(count: number, place: 1 | 2 | 3): string {
  if (count >= 4) return 'h-8 w-8 text-xs';
  if (count === 3) return place === 1 ? 'h-10 w-10 text-sm' : 'h-9 w-9 text-sm';
  if (count === 2) return place === 1 ? 'h-12 w-12 text-base' : 'h-11 w-11 text-sm';
  if (place === 1) return 'h-16 w-16 sm:h-20 sm:w-20 text-2xl';
  if (place === 2) return 'h-14 w-14 sm:h-16 sm:w-16 text-xl';
  return 'h-12 w-12 sm:h-14 sm:w-14 text-lg';
}

function Avatar({ player, sizeClass }: { player: MultiplayerPlayerState; sizeClass: string }) {
  if (player.avatar_url) {
    return (
      <img
        src={player.avatar_url}
        alt=""
        title={player.display_name}
        className={`${sizeClass} rounded-full border-2 border-accent object-cover shadow-lg shadow-black/40`}
      />
    );
  }

  return (
    <span
      title={player.display_name}
      className={`flex ${sizeClass} items-center justify-center rounded-full border-2 border-accent/60 bg-accent/15 font-display text-accent`}
    >
      {player.display_name.slice(0, 1).toUpperCase()}
    </span>
  );
}

function PodiumSlot({
  place,
  players,
  heightClass,
}: {
  place: 1 | 2 | 3;
  players: MultiplayerPlayerState[];
  heightClass: string;
}) {
  const placeLabel = place === 1 ? '1st' : place === 2 ? '2nd' : '3rd';
  const tone =
    place === 1
      ? 'border-accent/50 bg-accent/15'
      : place === 2
        ? 'border-slate-400/30 bg-court-800/80'
        : 'border-amber-700/40 bg-court-900/80';
  const sizeClass = avatarSizeForCount(Math.max(players.length, 1), place);
  const empty = players.length === 0;
  const score = players[0]?.score;

  return (
    <div className="flex min-w-0 flex-1 flex-col items-center justify-end">
      {empty ? (
        <div
          className={`flex ${sizeClass} items-center justify-center rounded-full border-2 border-dashed border-white/15 bg-court-900/40 text-slate-600`}
        >
          -
        </div>
      ) : (
        <div className="flex max-w-full flex-wrap items-center justify-center gap-1 px-1">
          {players.map((player) => (
            <Avatar key={player.player_id} player={player} sizeClass={sizeClass} />
          ))}
        </div>
      )}

      <p
        className={`mt-3 max-w-full truncate px-1 text-center text-sm font-semibold ${
          empty ? 'text-slate-600' : 'text-white'
        }`}
      >
        {empty
          ? 'Empty'
          : players.length === 1
            ? players[0].display_name
            : `${players.length} tied`}
      </p>
      <p className={`text-xs tabular-nums ${empty ? 'text-slate-600' : 'text-slate-400'}`}>
        {empty ? '-' : `${score} pts`}
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

/** Group players into up to 3 podium tiers, keeping tied scores on the same place. */
export function buildPodiumTiers(players: MultiplayerPlayerState[]): MultiplayerPlayerState[][] {
  const ranked = [...players].sort((a, b) => b.score - a.score || a.display_name.localeCompare(b.display_name));
  const tiers: MultiplayerPlayerState[][] = [];
  let index = 0;

  while (tiers.length < 3 && index < ranked.length) {
    const score = ranked[index].score;
    const group: MultiplayerPlayerState[] = [];
    while (index < ranked.length && ranked[index].score === score) {
      group.push(ranked[index]);
      index += 1;
    }
    tiers.push(group);
  }

  while (tiers.length < 3) {
    tiers.push([]);
  }

  return tiers;
}

export function MatchPodium({ players }: MatchPodiumProps) {
  const [first, second, third] = buildPodiumTiers(players);

  return (
    <div className="mt-8 w-full max-w-lg">
      <div className="flex items-end gap-2 sm:gap-4">
        <PodiumSlot place={2} players={second} heightClass="h-24 sm:h-28" />
        <PodiumSlot place={1} players={first} heightClass="h-32 sm:h-40" />
        <PodiumSlot place={3} players={third} heightClass="h-20 sm:h-24" />
      </div>
    </div>
  );
}
