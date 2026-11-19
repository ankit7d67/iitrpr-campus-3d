export type QualityTier = 'low' | 'high';

export interface AutoQualityState {
  tier: QualityTier;
  /** Consecutive 0.5 s windows below the low-FPS threshold. */
  lowStreak: number;
  /** Consecutive 0.5 s windows above the high-FPS threshold. */
  highStreak: number;
  /** performance.now() of the last tier change (0 = none yet). */
  lastChangeMs: number;
}

export const AUTO_QUALITY_INITIAL: AutoQualityState = {
  tier: 'high',
  lowStreak: 0,
  highStreak: 0,
  lastChangeMs: 0,
};

/** Three bad windows to drop, six good ones to climb back; 12 s cooldown. */
const COOLDOWN_MS = 12_000;
const LOW_FPS = 30;
const HIGH_FPS = 55;

/**
 * Pure adaptive-quality decision for Auto mode, driven by the FPS sample that
 * PerfOverlay publishes every 500 ms. Hysteresis plus a cooldown keep the GLB
 * from being mounted/unmounted repeatedly on a borderline machine.
 */
export function updateAutoQuality(
  state: AutoQualityState,
  fps: number,
  nowMs: number,
): { next: AutoQualityState; changed: boolean } {
  if (!Number.isFinite(fps) || nowMs - state.lastChangeMs < COOLDOWN_MS) {
    return { next: state, changed: false };
  }
  if (state.tier === 'high') {
    const lowStreak = fps < LOW_FPS ? state.lowStreak + 1 : 0;
    if (lowStreak >= 3) {
      return {
        next: { tier: 'low', lowStreak: 0, highStreak: 0, lastChangeMs: nowMs },
        changed: true,
      };
    }
    return { next: { ...state, lowStreak }, changed: false };
  }
  const highStreak = fps > HIGH_FPS ? state.highStreak + 1 : 0;
  if (highStreak >= 6) {
    return {
      next: { tier: 'high', lowStreak: 0, highStreak: 0, lastChangeMs: nowMs },
      changed: true,
    };
  }
  return { next: { ...state, highStreak }, changed: false };
}
