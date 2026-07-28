/** Lightweight Web Audio SFX (no asset files). */

type SfxKind = 'start' | 'countdown' | 'correct' | 'wrong' | 'tick';

let audioCtx: AudioContext | null = null;

function getCtx(): AudioContext | null {
  if (typeof window === 'undefined') return null;
  const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  if (!Ctx) return null;
  if (!audioCtx) {
    audioCtx = new Ctx();
  }
  if (audioCtx.state === 'suspended') {
    void audioCtx.resume();
  }
  return audioCtx;
}

function tone(
  frequency: number,
  duration: number,
  type: OscillatorType,
  gainValue: number,
  when = 0,
) {
  const ctx = getCtx();
  if (!ctx) return;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = type;
  osc.frequency.value = frequency;
  const startAt = ctx.currentTime + when;
  gain.gain.setValueAtTime(0.0001, startAt);
  gain.gain.exponentialRampToValueAtTime(gainValue, startAt + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, startAt + duration);
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start(startAt);
  osc.stop(startAt + duration + 0.02);
}

export function playSfx(kind: SfxKind, enabled: boolean) {
  if (!enabled) return;
  try {
    switch (kind) {
      case 'start':
        tone(392, 0.12, 'triangle', 0.08);
        tone(523.25, 0.16, 'triangle', 0.09, 0.1);
        tone(659.25, 0.22, 'triangle', 0.1, 0.22);
        break;
      case 'countdown':
        tone(620, 0.1, 'square', 0.05);
        break;
      case 'tick':
        tone(880, 0.06, 'sine', 0.04);
        break;
      case 'correct':
        tone(523.25, 0.1, 'sine', 0.08);
        tone(659.25, 0.12, 'sine', 0.09, 0.08);
        tone(783.99, 0.18, 'sine', 0.1, 0.18);
        break;
      case 'wrong':
        tone(220, 0.18, 'sawtooth', 0.07);
        tone(165, 0.28, 'sawtooth', 0.08, 0.12);
        break;
      default:
        break;
    }
  } catch {
    /* ignore audio failures */
  }
}
