import { useEffect, useRef } from 'react';

interface AnimatedBasketballProps {
  className?: string;
}

/** Canvas basketball with classic panel seams, bounce, and spin. */
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

    const drawSeams = (radius: number) => {
      const line = Math.max(2.5, radius * 0.055);
      ctx.lineWidth = line;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.strokeStyle = 'rgba(28, 16, 8, 0.92)';

      // Vertical + horizontal ribs
      ctx.beginPath();
      ctx.moveTo(0, -radius);
      ctx.lineTo(0, radius);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(-radius, 0);
      ctx.lineTo(radius, 0);
      ctx.stroke();

      // Classic basketball curved ribs (top / bottom) — not globe ellipses
      ctx.beginPath();
      ctx.moveTo(-radius * 0.92, -radius * 0.28);
      ctx.bezierCurveTo(
        -radius * 0.35,
        radius * 0.12,
        radius * 0.35,
        radius * 0.12,
        radius * 0.92,
        -radius * 0.28,
      );
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(-radius * 0.92, radius * 0.28);
      ctx.bezierCurveTo(
        -radius * 0.35,
        -radius * 0.12,
        radius * 0.35,
        -radius * 0.12,
        radius * 0.92,
        radius * 0.28,
      );
      ctx.stroke();
    };

    const drawPebbleTexture = (radius: number) => {
      ctx.save();
      ctx.beginPath();
      ctx.arc(0, 0, radius, 0, Math.PI * 2);
      ctx.clip();

      for (let i = 0; i < 420; i += 1) {
        const angle = (i * 2.399) % (Math.PI * 2);
        const dist = Math.sqrt((i % 97) / 97) * radius * 0.96;
        const x = Math.cos(angle) * dist;
        const y = Math.sin(angle) * dist;
        const shade = i % 3 === 0 ? 'rgba(90, 40, 10, 0.14)' : 'rgba(255, 210, 150, 0.08)';
        ctx.fillStyle = shade;
        ctx.beginPath();
        ctx.arc(x, y, radius * 0.012, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();
    };

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
      const spin = frame * 0.028;
      const shadowScale = 1.1 - bounce * 0.35;
      const shadowAlpha = 0.22 + bounce * 0.18;

      ctx.clearRect(0, 0, w, h);

      // Soft warm glow
      const glow = ctx.createRadialGradient(cx, y, radius * 0.2, cx, y, radius * 2.2);
      glow.addColorStop(0, 'rgba(194, 90, 30, 0.22)');
      glow.addColorStop(0.55, 'rgba(194, 90, 30, 0.06)');
      glow.addColorStop(1, 'rgba(194, 90, 30, 0)');
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

      const ball = ctx.createRadialGradient(-radius * 0.3, -radius * 0.35, radius * 0.08, 0, 0, radius);
      ball.addColorStop(0, '#e8903a');
      ball.addColorStop(0.35, '#d2691e');
      ball.addColorStop(0.72, '#b45309');
      ball.addColorStop(1, '#7c2d12');
      ctx.fillStyle = ball;
      ctx.beginPath();
      ctx.arc(0, 0, radius, 0, Math.PI * 2);
      ctx.fill();

      drawPebbleTexture(radius);

      // Soft leather shading (matte, not plastic)
      const shade = ctx.createRadialGradient(radius * 0.25, radius * 0.35, radius * 0.1, 0, 0, radius);
      shade.addColorStop(0, 'rgba(0, 0, 0, 0)');
      shade.addColorStop(0.65, 'rgba(0, 0, 0, 0)');
      shade.addColorStop(1, 'rgba(40, 15, 5, 0.35)');
      ctx.fillStyle = shade;
      ctx.beginPath();
      ctx.arc(0, 0, radius, 0, Math.PI * 2);
      ctx.fill();

      // Thin rim so the silhouette reads clearly
      ctx.strokeStyle = 'rgba(60, 25, 8, 0.55)';
      ctx.lineWidth = Math.max(1.5, radius * 0.02);
      ctx.beginPath();
      ctx.arc(0, 0, radius - 0.5, 0, Math.PI * 2);
      ctx.stroke();

      // Seams clipped to ball, spinning
      ctx.save();
      ctx.beginPath();
      ctx.arc(0, 0, radius - 1, 0, Math.PI * 2);
      ctx.clip();
      ctx.rotate(spin);
      drawSeams(radius);
      ctx.restore();

      // Subtle matte highlight (leather, not chrome)
      const shine = ctx.createRadialGradient(
        -radius * 0.35,
        -radius * 0.4,
        0,
        -radius * 0.2,
        -radius * 0.25,
        radius * 0.5,
      );
      shine.addColorStop(0, 'rgba(255, 236, 210, 0.22)');
      shine.addColorStop(1, 'rgba(255, 236, 210, 0)');
      ctx.fillStyle = shine;
      ctx.beginPath();
      ctx.arc(-radius * 0.22, -radius * 0.28, radius * 0.42, 0, Math.PI * 2);
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
