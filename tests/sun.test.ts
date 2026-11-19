import { describe, expect, it } from 'vitest';
import {
  formatTime,
  fromLocalInputValue,
  getSunInfo,
  nightFactor,
  toLocalInputValue,
  walkingTimeMinutes,
} from '../src/lib/sun';

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

  it('sun is high at summer noon and below the horizon at night (lat 30.97)', () => {
    // 15 Jun 2026, 07:00 UTC = 12:30 IST
    const noon = getSunInfo(Date.UTC(2026, 5, 15, 7, 0));
    expect(noon.elevationDeg).toBeGreaterThan(60);
    expect(noon.night).toBe(false);
    // 15 Jun 2026, 18:30 UTC = 00:00 IST (next local day)
    const midnight = getSunInfo(Date.UTC(2026, 5, 15, 18, 30));
    expect(midnight.elevationDeg).toBeLessThan(0);
    expect(midnight.night).toBe(true);
  });

  it('azimuth is east of north in the morning and west in the afternoon', () => {
    const morning = getSunInfo(Date.UTC(2026, 5, 15, 3, 0)); // 08:30 IST
    const afternoon = getSunInfo(Date.UTC(2026, 5, 15, 11, 0)); // 16:30 IST
    expect(morning.azimuthDeg).toBeGreaterThan(0);
    expect(morning.azimuthDeg).toBeLessThan(180);
    expect(afternoon.azimuthDeg).toBeGreaterThan(180);
    expect(afternoon.azimuthDeg).toBeLessThan(360);
  });

  it('summer sunrise/sunset land at plausible IST times', () => {
    const info = getSunInfo(Date.UTC(2026, 5, 15, 5, 0)); // 10:30 IST
    const sunrise = formatTime(info.sunriseUtcMs);
    const sunset = formatTime(info.sunsetUtcMs);
    expect(sunrise >= '05:00' && sunrise <= '06:00').toBe(true);
    expect(sunset >= '19:00' && sunset <= '20:00').toBe(true);
  });

  it('night factor ramps over civil twilight and saturates after dark', () => {
    const noon = getSunInfo(Date.UTC(2026, 5, 15, 7, 0)); // 12:30 IST, high sun
    const dusk = getSunInfo(Date.UTC(2026, 5, 15, 13, 30)); // 19:00 IST, sun near horizon
    const midnight = getSunInfo(Date.UTC(2026, 5, 15, 18, 30)); // 00:00 IST
    expect(nightFactor(noon)).toBe(0);
    expect(nightFactor(midnight)).toBe(1);
    expect(nightFactor(dusk)).toBeGreaterThan(0);
    expect(nightFactor(dusk)).toBeLessThan(1);
  });

  it('round-trips IST datetime-local input values', () => {
    const utc = Date.UTC(2026, 5, 15, 12, 30); // 18:00 IST
    const s = toLocalInputValue(utc);
    expect(s).toBe('2026-06-15T18:00');
    expect(fromLocalInputValue(s)).toBe(utc);
    expect(fromLocalInputValue('not-a-date')).toBeNull();
  });
});
