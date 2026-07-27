import type { NewsItem } from '@/types';

interface NewsFeedProps {
  items: NewsItem[];
  compact?: boolean;
}

const typeColors: Record<string, string> = {
  game: 'text-accent-light',
  injury: 'text-red-400',
  recap: 'text-blue-400',
  career: 'text-emerald-400',
  trade: 'text-yellow-400',
  free_agency: 'text-purple-400',
  draft: 'text-cyan-400',
  playoffs: 'text-pink-400',
  offseason: 'text-orange-400',
  rumor: 'text-slate-400',
  owner: 'text-red-400',
  awards: 'text-yellow-300',
  extension: 'text-blue-400',
  retirement: 'text-slate-400',
};

export function NewsFeed({ items, compact = false }: NewsFeedProps) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">No news yet. Simulate games to generate updates.</p>;
  }

  return (
    <ul className={`space-y-3 ${compact ? '' : ''}`}>
      {items.map((item) => (
        <li key={item.id} className="border-b border-court-800/80 pb-3 last:border-0">
          <div className="flex items-center gap-2">
            <span
              className={`text-xs font-semibold uppercase tracking-wider ${
                typeColors[item.transaction_type] ?? 'text-slate-400'
              }`}
            >
              {item.transaction_type}
            </span>
            <span className="text-xs text-slate-600">
              {new Date(item.created_at).toLocaleDateString()}
            </span>
          </div>
          <p className={`mt-1 text-sm text-slate-300 ${compact ? 'line-clamp-2' : ''}`}>
            {item.description}
          </p>
        </li>
      ))}
    </ul>
  );
}
