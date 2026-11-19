'use client';

import { formatTime, fromLocalInputValue, getSunInfo, toLocalInputValue } from '../lib/sun';
import { useCampusStore } from '../lib/store';

/**
 * Time-of-day control (Phase 7 item 7-7).
 *
 * The datetime-local input is read/written as IST (round-trips through
 * `toLocalInputValue`/`fromLocalInputValue`), and the computed solar info
 * (elevation, azimuth, sunrise/sunset) is shown. The selected time drives the
 * scene lighting via the store's `sunUtcMs`.
 */
export function SunPanel() {
  const sunUtcMs = useCampusStore((s) => s.sunUtcMs);
  const setSunUtcMs = useCampusStore((s) => s.setSunUtcMs);
  const night = useCampusStore((s) => s.night);
  const setNight = useCampusStore((s) => s.setNight);

  const info = getSunInfo(sunUtcMs);

  const onChange = (value: string) => {
    const t = fromLocalInputValue(value);
    if (t !== null) setSunUtcMs(t);
  };

  return (
    <div className="panel sun-panel">
      <h2>Sun</h2>
      <label htmlFor="sun-time">Time of day (IST)</label>
      <input
        id="sun-time"
        type="datetime-local"
        value={toLocalInputValue(sunUtcMs)}
        onChange={(e) => onChange(e.target.value)}
      />
      <div className="sun-actions">
        <button type="button" onClick={() => setSunUtcMs(Date.now())}>
          Now
        </button>
        <button type="button" onClick={() => setNight(!night)}>
          Night mode: {night ? 'ON' : 'OFF'}
        </button>
      </div>
      <p className="muted sun-info">
        <span className="sun-elevation">Elevation {info.elevationDeg.toFixed(1)}°</span>
        {' · azimuth '}
        {info.azimuthDeg.toFixed(0)}°
      </p>
      <p className="muted sun-info">
        Sunrise {formatTime(info.sunriseUtcMs)} · sunset {formatTime(info.sunsetUtcMs)}
      </p>
    </div>
  );
}
