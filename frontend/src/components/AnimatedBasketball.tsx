import { useEffect, useRef } from 'react';

interface AnimatedBasketballProps {
  className?: string;
}

/** Canvas basketball with bounce, spin, and soft court shadow. */
export function AnimatedBasketball({ className = '' }: AnimatedBasketballProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let frame = 0;
    let raf = 0;
    let running = true;

    const resize = () => {
      const size = Math.min(420, Math.max(220, canvas.parentElement?.clientWidth ?? 320));
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = size * dpr;
      canvas.height = size * dpr;
      canvas.style.width = `${size}px`;
      canvas.style.height = `${size}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    resize();
    window.addEventListener('resize', resize);

    const draw = () => {
      if (!running) return;
      frame += 1;
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      const cx = w / 2;
      const baseY = h * 0.58;
      const bounce = Math.abs(Math.sin(frame * 0.045));
      const y = baseY - bounce * (h * 0.14);
      const squash = 1 - bounce * 0.08;
      const stretch = 1 + bounce * 0.05;
      const radius = Math.min(w, h) * 0.28;
      const spin = frame * 0.035;
      const shadowScale = 1.1 - bounce * 0.35;
      const shadowAlpha = 0.22 + bounce * 0.18;

      ctx.clearRect(0, 0, w, h);

      // Soft glow behind the ball
      const glow = ctx.createRadialGradient(cx, y, radius * 0.2, cx, y, radius * 2.2);
      glow.addColorStop(0, 'rgba(249, 115, 22, 0.28)');
      glow.addColorStop(0.55, 'rgba(249, 115, 22, 0.08)');
      glow.addColorStop(1, 'rgba(249, 115, 22, 0)');
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(cx, y, radius * 2.1, 0, Math.PI * 2);
      ctx.fill();

      // Court shadow
      ctx.save();
      ctx.translate(cx, baseY + radius * 0.95);
      ctx.scale(shadowScale * 1.35, shadowScale * 0.28);
      ctx.fillStyle = `rgba(0, 0, 0, ${shadowAlpha})`;
      ctx.beginPath();
      ctx.arc(0, 0, radius, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      // Ball body
      ctx.save();
      ctx.translate(cx, y);
      ctx.scale(stretch, squash);

      const ball = ctx.createRadialGradient(-radius * 0.35, -radius * 0.4, radius * 0.1, 0, 0, radius);
      ball.addColorStop(0, '#fdba74');
      ball.addColorStop(0.45, '#f97316');
      ball.addColorStop(1, '#c2410c');
      ctx.fillStyle = ball;
      ctx.beginPath();
      ctx.arc(0, 0, radius, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = 'rgba(10, 15, 20, 0.85)';
      ctx.lineWidth = Math.max(2, radius * 0.045);
      ctx.lineCap = 'round';

      // Seam lines with spin
      ctx.rotate(spin);
      ctx.beginPath();
      ctx.moveTo(0, -radius);
      ctx.lineTo(0, radius);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(-radius, 0);
      ctx.lineTo(radius, 0);
      ctx.stroke();

      ctx.beginPath();
      ctx.ellipse(0, 0, radius * 0.72, radius * 0.95, 0, 0, Math.PI * 2);
      ctx.stroke();

      ctx.beginPath();
      ctx.ellipse(0, 0, radius * 0.95, radius * 0.72, 0, 0, Math.PI * 2);
      ctx.stroke();

      ctx.restore();

      // Specular highlight
      ctx.save();
      ctx.translate(cx, y);
      ctx.scale(stretch, squash);
      const shine = ctx.createRadialGradient(
        -radius * 0.35,
        -radius * 0.4,
        0,
        -radius * 0.2,
        -radius * 0.25,
        radius * 0.55,
      );
      shine.addColorStop(0, 'rgba(255, 255, 255, 0.45)');
      shine.addColorStop(1, 'rgba(255, 255, 255, 0)');
      ctx.fillStyle = shine;
      ctx.beginPath();
      ctx.arc(-radius * 0.2, -radius * 0.25, radius * 0.45, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      raf = window.requestAnimationFrame(draw);
    };

    raf = window.requestAnimationFrame(draw);

    return () => {
      running = false;
      window.cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <div className={`relative flex items-center justify-center ${className}`} aria-hidden="true">
      <canvas ref={canvasRef} className="ball-float" />
    </div>
  );
}
