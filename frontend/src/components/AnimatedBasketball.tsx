interface AnimatedBasketballProps {
  className?: string;
}

/** Simple basketball icon that slowly bounces and spins. */
export function AnimatedBasketball({ className = '' }: AnimatedBasketballProps) {
  return (
    <div className={`relative mx-auto flex items-center justify-center ${className}`} aria-hidden="true">
      <img
        src="/basketball.svg"
        alt=""
        className="ball-bounce h-40 w-40 sm:h-52 sm:w-52 lg:h-60 lg:w-60"
        draggable={false}
      />
    </div>
  );
}
