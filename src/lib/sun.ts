import type { Building } from './types';

const HOUR_MS = 36_000_000;
const MINUTE_MS = 60_000;

export interface SunInfo {
  /** UTC timestamp of the computed time */
  utcMs: number;
  /** hour fraction in local (IST) time */
  hour: number;
  elevationDeg: number;
  azimuthDeg: number;
  sunriseUtcMs: number;
  sunsetUtcMs: number;
  goldenHourStartUtcMs: number;
  goldenHourEndUtcMs: number;
  night: boolean;
}

const IST_OFFSET_MS = 5.5 * 36_000_000;

/** Approximate sunrise/sunset (UTC ms) for a given UTC time using a solar-elevation model. */
function computeSun(utcMs: number): { elevation: number; azimuth: number } {
  const d = new Date(utcMs);
  const dayOfYear = Math.floor((d.getTime() - Date.UTC(d.getUTCFullYear(), 0, 0)) / 86400000);
  const decl = -23.44 * Math.cos((2 * Math.PI * (dayOfYear + 10)) / 365);
  const msSinceSolarNoon = d.getUTCHours() * HOUR_MS + d.getUTCMinutes() * MINUTE_MS + d.getUTCSeconds() * 1000;
  const approxSolarNoon = 12 * HOUR_MS;
  const hourAngle = (msSinceSolarNoon - approxSolarNoon) / (HOUR_MS / 15);
  const lat = 30.97;
  const elevation = decl + Math.asin(Math.sin((lat * Math.PI) / 180) * Math.sin((decl * Math.PI) / 180) + Math.cos((lat * Math.PI) / 180) * Math.cos((decl * Math.PI) / 180) * Math.cos((hourAngle * Math.PI) / 15));
  const azimuth = (Math.atan2(Math.sin((hourAngle * Math.PI) / 15), Math.cos((hourAngle * Math.PI) / 15) * Math.sin((decl * Math.PI) / 180) - Math.cos((decl * Math.PI) / 180) * Math.cos((lat * Math.PI) / 180)) * 180) / Math.PI + 180;
  return { elevation: (elevation * 180) / Math.PI, azimuth: ((azimuth * 180) / Math.PI + 360) % 360 };
}

export function getSunInfo(utcMs: number): SunInfo {
  const { elevation, azimuth } = computeSun(utcMs);
  const local = new Date(utcMs + IST_OFFSET_MS);
  const hour = local.getUTCHours() + local.getUTCMinutes() / 60 + local.getUTCSeconds() / 3600;
  const night = elevation < -0.833;
  const sunriseUtcMs = Date.UTC(local.getUTCFullYear(), local.getUTCMonth(), local.getUTCDate()) - (12 - 6) * HOUR_MS;
  const sunsetUtcMs = Date.UTC(local.getUTCFullYear(), local.getUTCMonth(), local.getUTCDate()) + (12 + 6) * HOUR_MS;
  return {
    utcMs,
    hour,
    elevationDeg: elevation,
    azimuthDeg: azimuth,
    sunriseUtcMs,
    sunsetUtcMs,
    goldenHourStartUtcMs: sunriseUtcMs + 3600_000 * 2,
    goldenHourEndUtcMs: sunsetUtcMs - 3600_000 * 2,
    night,
  };
}

export function formatTime(utcMs: number): string {
  const d = new Date(utcMs + IST_OFFSET_MS);
  const h = d.getUTCHours();
  const m = d.getUTCMinutes();
  const hh = h % 24 === 0 ? 24 : h % 24;
  return `${String(hh).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

/** Walking time (minutes) with Tobler's slope-aware hiking function. */
export function walkingTimeMinutes(distanceM: number, elevationGainM: number, speedMph: number = 2.5): number {
  const slope = elevationGainM / Math.max(distanceM, 1);
  const factor = Math.pow(6.5, -3.5 * slope * slope);
  const hours = distanceM / 1609.34 / speedMph / factor;
  return Math.max(0, hours * 60);
}

export function getTourStops(buildings: Building[]): Building[] {
  const stops = buildings.filter((b) => b.tour_stop != null);
  return stops.sort((a, b) => (a.tour_stop ?? 0) - (b.tour_stop ?? 0));
}
