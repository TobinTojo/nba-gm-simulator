interface DifficultyStarsProps {
  rating: number;
  max?: number;
}

export function DifficultyStars({ rating, max = 5 }: DifficultyStarsProps) {
  return (
    <div className="flex gap-0.5 text-accent" aria-label={`Difficulty ${rating} of ${max}`}>
      {Array.from({ length: max }, (_, i) => (
        <span key={i} className={i < rating ? 'opacity-100' : 'opacity-25'}>
          ★
        </span>
      ))}
    </div>
  );
}
