import { describe, expect, it } from 'vitest';
import { getSunInfo, walkingTimeMinutes } from '../src/lib/sun';

describe('sun', () => {
  it('returns sun info for the current time', () => {
    const info = getSunInfo(Date.now());
    expect(info).toHaveProperty('elevationDeg');
    expect(info).toHaveProperty('azimuthDeg');
    expect(info).toHaveProperty('night');
  });

  it('computes sunset after sunrise in the same day', () => {
    const info = getSunInfo(Date.now());
    expect(info.sunsetUtcMs).toBeGreaterThan(info.sunriseUtcMs);
  });

  it('applies Tobler slope factor to walking time', () => {
    const flat = walkingTimeMinutes(1000, 0);
    const uphill = walkingTimeMinutes(1000, 100);
    expect(uphill).toBeGreaterThan(flat);
  });
});
