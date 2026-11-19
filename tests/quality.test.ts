import { describe, expect, it } from 'vitest';
import { AUTO_QUALITY_INITIAL, updateAutoQuality, type AutoQualityState } from '../src/lib/quality';

describe('updateAutoQuality (7-12)', () => {
  it('stays high while FPS is healthy', () => {
    const { next, changed } = updateAutoQuality(AUTO_QUALITY_INITIAL, 60, 1000);
    expect(changed).toBe(false);
    expect(next.tier).toBe('high');
  });

  it('drops to low after three consecutive bad windows', () => {
    let state: AutoQualityState = AUTO_QUALITY_INITIAL;
    state = updateAutoQuality(state, 24, 13_000).next;
    expect(state.tier).toBe('high');
    state = updateAutoQuality(state, 28, 13_500).next;
    expect(state.tier).toBe('high');
    const third = updateAutoQuality(state, 20, 14_000);
    expect(third.changed).toBe(true);
    expect(third.next.tier).toBe('low');
    expect(third.next.lastChangeMs).toBe(14_000);
  });

  it('resets the low streak when FPS recovers', () => {
    let state = updateAutoQuality(AUTO_QUALITY_INITIAL, 20, 13_000).next;
    state = updateAutoQuality(state, 60, 13_500).next;
    expect(state.lowStreak).toBe(0);
    expect(state.tier).toBe('high');
  });

  it('needs six good windows to climb back and honours the cooldown', () => {
    let state: AutoQualityState = {
      tier: 'low',
      lowStreak: 0,
      highStreak: 0,
      lastChangeMs: 1000,
    };
    // Still inside the 12 s cooldown.
    expect(updateAutoQuality(state, 60, 5000).changed).toBe(false);
    for (let i = 0; i < 5; i++) state = updateAutoQuality(state, 60, 13_000 + i * 500).next;
    expect(state.tier).toBe('low');
    const sixth = updateAutoQuality(state, 60, 16_000);
    expect(sixth.changed).toBe(true);
    expect(sixth.next.tier).toBe('high');
  });

  it('ignores non-finite FPS samples', () => {
    const { next, changed } = updateAutoQuality(AUTO_QUALITY_INITIAL, Number.NaN, 20_000);
    expect(changed).toBe(false);
    expect(next).toBe(AUTO_QUALITY_INITIAL);
  });
});
