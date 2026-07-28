interface AnimatedBasketballProps {
  className?: string;
}

/** Site basketball icon with a straight upright bounce (no spin). */
export function AnimatedBasketball({ className = '' }: AnimatedBasketballProps) {
  return (
    <div className={`relative mx-auto flex items-center justify-center ${className}`} aria-hidden="true">
      <img
        src="/basketball.png"
        alt=""
        className="ball-bounce h-40 w-40 object-contain sm:h-52 sm:w-52 lg:h-60 lg:w-60"
        draggable={false}
      />
    </div>
  );
}
