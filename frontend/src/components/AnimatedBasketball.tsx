interface AnimatedBasketballProps {
  className?: string;
}

/** Simple basketball icon with a bounce animation. */
export function AnimatedBasketball({ className = '' }: AnimatedBasketballProps) {
  return (
    <div className={`relative flex items-center justify-center ${className}`} aria-hidden="true">
      <img
        src="/basketball.svg"
        alt=""
        className="ball-bounce h-44 w-44 sm:h-56 sm:w-56 lg:h-64 lg:w-64"
        draggable={false}
      />
    </div>
  );
}
