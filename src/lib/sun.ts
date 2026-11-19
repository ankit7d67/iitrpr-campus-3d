import type { Building } from './types';

const HOUR_MS = 3_600_000;

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

const IST_OFFSET_MS = 5.5 * HOUR_MS;
/** IIT Ropar main campus (permanent campus beside the Sutlej). */
const CAMPUS_LAT = 30.9704;
const CAMPUS_LON = 76.4691;
/** Standard sun-center refraction at the horizon (degrees). */
const HORIZON_ELEV = -0.833;

function solarDeclination(dayOfYear: number): number {
  // Degrees; standard first-order approximation of the solar declination.
  return -23.44 * Math.cos((2 * Math.PI * (dayOfYear + 10)) / 365);
}

/**
 * Solar position for a UTC time at the campus.
 * elevation: degrees above the horizon (-90..90);
 * azimuth: degrees clockwise from north (0..360).
 *
 * Unit vector in east/north/up is built directly, so everything stays in
 * degrees until the final asin/atan2 (an earlier version mixed degrees into
 * radian expressions and produced garbage).
 */
function computeSun(utcMs: number): { elevation: number; azimuth: number } {
  const d = new Date(utcMs);
  const dayOfYear = Math.floor((utcMs - Date.UTC(d.getUTCFullYear(), 0, 0)) / 86400000);
  const decl = solarDeclination(dayOfYear);
  const utcHours = d.getUTCHours() + d.getUTCMinutes() / 60 + d.getUTCSeconds() / 3600;
  // Solar noon in UTC hours (Ropar is at 76.47°E → noon ≈ 06:54 UTC ≈ 12:24 IST).
  const solarNoonUtc = 12 - CAMPUS_LON / 15;
  const hourAngleDeg = (utcHours - solarNoonUtc) * 15;

  const lr = (CAMPUS_LAT * Math.PI) / 180;
  const dr = (decl * Math.PI) / 180;
  const hr = (hourAngleDeg * Math.PI) / 180;

  // Sun unit vector in ENU coordinates.
  const east = -Math.cos(dr) * Math.sin(hr);
  const north = Math.sin(dr) * Math.cos(lr) - Math.cos(dr) * Math.sin(lr) * Math.cos(hr);
  const up = Math.sin(lr) * Math.sin(dr) + Math.cos(lr) * Math.cos(dr) * Math.cos(hr);

  const elevation = (Math.asin(Math.max(-1, Math.min(1, up))) * 180) / Math.PI;
  const azimuth = ((Math.atan2(east, north) * 180) / Math.PI + 360) % 360;
  return { elevation, azimuth };
}

export function getSunInfo(utcMs: number): SunInfo {
  const { elevation, azimuth } = computeSun(utcMs);
  const local = new Date(utcMs + IST_OFFSET_MS);
  const hour = local.getUTCHours() + local.getUTCMinutes() / 60 + local.getUTCSeconds() / 3600;
  const night = elevation < HORIZON_ELEV;

  // Sunrise/sunset for the local (IST) calendar day, using the same horizon
  // model: hour angle H0 = acos((sin(h0) - sin φ sin δ) / (cos φ cos δ)).
  const localDayStart = Date.UTC(local.getUTCFullYear(), local.getUTCMonth(), local.getUTCDate());
  const dayOfYear = Math.floor((localDayStart - Date.UTC(local.getUTCFullYear(), 0, 0)) / 86400000);
  const decl = solarDeclination(dayOfYear);
  const lr = (CAMPUS_LAT * Math.PI) / 180;
  const dr = (decl * Math.PI) / 180;
  const cosH0 =
    (Math.sin((HORIZON_ELEV * Math.PI) / 180) - Math.sin(lr) * Math.sin(dr)) /
    (Math.cos(lr) * Math.cos(dr));
  const H0 = cosH0 <= -1 ? 180 : cosH0 >= 1 ? 0 : (Math.acos(cosH0) * 180) / Math.PI;
  // Solar noon in IST hours (12 h + 5.5 h offset - longitude correction).
  const solarNoonIst = 12 + IST_OFFSET_MS / HOUR_MS - CAMPUS_LON / 15;
  const localMidnightUtc = localDayStart - IST_OFFSET_MS;
  const sunriseUtcMs = localMidnightUtc + (solarNoonIst - H0 / 15) * HOUR_MS;
  const sunsetUtcMs = localMidnightUtc + (solarNoonIst + H0 / 15) * HOUR_MS;

  return {
    utcMs,
    hour,
    elevationDeg: elevation,
    azimuthDeg: azimuth,
    sunriseUtcMs,
    sunsetUtcMs,
    goldenHourStartUtcMs: sunriseUtcMs + 2 * HOUR_MS,
    goldenHourEndUtcMs: sunsetUtcMs - 2 * HOUR_MS,
    night,
  };
}

/**
 * 0 in full daylight, 1 once the sun is 6° below the horizon, with a smooth
 * dusk/dawn ramp in between (civil twilight ends at −6°). Shared by the sky,
 * stars, moon and street lamps so they all switch on at the same moment.
 */
export function nightFactor(info: SunInfo): number {
  const t = (6 - info.elevationDeg) / 12;
  return Math.min(1, Math.max(0, t));
}

export function formatTime(utcMs: number): string {
  const d = new Date(utcMs + IST_OFFSET_MS);
  const h = d.getUTCHours();
  const m = d.getUTCMinutes();
  const hh = h % 24 === 0 ? 24 : h % 24;
  return `${String(hh).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

/** Format a UTC ms as a `<input type="datetime-local">` value read as IST. */
export function toLocalInputValue(utcMs: number): string {
  const d = new Date(utcMs + IST_OFFSET_MS);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}T${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`;
}

/** Parse a datetime-local value as IST into UTC ms (null when malformed). */
export function fromLocalInputValue(value: string): number | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value);
  if (!m) return null;
  const [, y, mo, d, h, mi] = m;
  return Date.UTC(Number(y), Number(mo) - 1, Number(d), Number(h), Number(mi)) - IST_OFFSET_MS;
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
