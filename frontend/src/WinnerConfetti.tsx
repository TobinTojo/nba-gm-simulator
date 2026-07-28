import { useEffect, useRef } from 'react';

interface WinnerConfettiProps {
  active: boolean;
}

/** Lightweight canvas confetti — no extra dependency. */
export function WinnerConfetti({ active }: WinnerConfettiProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!active) return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let width = window.innerWidth;
    let height = window.innerHeight;
    canvas.width = width;
    canvas.height = height;

    const colors = ['#f59e0b', '#22c55e', '#38bdf8', '#f472b6', '#a3e635', '#ffffff'];
    const pieces = Array.from({ length: 140 }, () => ({
      x: Math.random() * width,
      y: Math.random() * -height,
      w: 6 + Math.random() * 8,
      h: 8 + Math.random() * 10,
      color: colors[Math.floor(Math.random() * colors.length)],
      speed: 2 + Math.random() * 4,
      drift: -1.5 + Math.random() * 3,
      rotation: Math.random() * Math.PI,
      spin: -0.2 + Math.random() * 0.4,
    }));

    let frame = 0;
    let raf = 0;
    const maxFrames = 220;

    const draw = () => {
      frame += 1;
      ctx.clearRect(0, 0, width, height);
      for (const piece of pieces) {
        piece.y += piece.speed;
        piece.x += piece.drift;
        piece.rotation += piece.spin;
        if (piece.y > height + 20) {
          piece.y = -20;
          piece.x = Math.random() * width;
        }
        ctx.save();
        ctx.translate(piece.x, piece.y);
        ctx.rotate(piece.rotation);
        ctx.fillStyle = piece.color;
        ctx.fillRect(-piece.w / 2, -piece.h / 2, piece.w, piece.h);
        ctx.restore();
      }
      if (frame < maxFrames) {
        raf = window.requestAnimationFrame(draw);
      } else {
        ctx.clearRect(0, 0, width, height);
      }
    };

    const onResize = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width;
      canvas.height = height;
    };

    window.addEventListener('resize', onResize);
    raf = window.requestAnimationFrame(draw);

    return () => {
      window.cancelAnimationFrame(raf);
      window.removeEventListener('resize', onResize);
    };
  }, [active]);

  if (!active) return null;

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none fixed inset-0 z-50"
      aria-hidden
    />
  );
}
