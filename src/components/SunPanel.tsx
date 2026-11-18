'use client';

import { useEffect } from 'react';
import { useCampusStore } from '../lib/store';

function toLocalInputValue(utcMs: number): string {
  const d = new Date(utcMs + 5.5 * 36_000_000);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}T${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`;
}

export function SunPanel() {
  const sunUtcMs = useCampusStore((s) => s.sunUtcMs);
  const setSunUtcMs = useCampusStore((s) => s.setSunUtcMs);

  useEffect(() => {
    const el = document.querySelector<HTMLInputElement>('#sun-time');
    if (el) el.value = toLocalInputValue(sunUtcMs);
  }, [sunUtcMs]);

  const onChange = (value: string) => {
    const t = new Date(value).getTime();
    if (!Number.isNaN(t)) setSunUtcMs(t);
  };

  return (
    <div className="panel sun-panel">
      <h2>Sun</h2>
      <label htmlFor="sun-time">Time of day (IST)</label>
      <input id="sun-time" type="datetime-local" value={toLocalInputValue(sunUtcMs)} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}
