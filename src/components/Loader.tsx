'use client';

import { useProgress } from '@react-three/drei';
import { useEffect, useState } from 'react';
import { loadCampus, loadNav, loadScatter } from '../lib/data';
import { useCampusStore } from '../lib/store';

/** What the progress bar is "doing", by how far it has got. */
const STEPS: [number, string][] = [
  [0, 'Surveying the campus…'],
  [20, 'Laying the roads…'],
  [45, 'Raising buildings…'],
  [70, 'Planting trees…'],
  [90, 'Switching on the lights…'],
];

/**
 * Phase 7 item 7-10: full-screen title card with a progress bar until both the
 * JSON data and the 3D model are ready, then a short fade. A failed data fetch
 * shows an actionable error card instead of leaving a blank screen.
 *
 * `useProgress()` tracks three.js loaders (the GLB); the JSON fetches are
 * tracked by the store's `dataReady` flag, set by this component.
 */
export function Loader() {
  const { progress } = useProgress();
  const dataReady = useCampusStore((s) => s.dataReady);
  const modelReady = useCampusStore((s) => s.modelReady);
  const dataError = useCampusStore((s) => s.dataError);
  const setDataReady = useCampusStore((s) => s.setDataReady);
  const setDataError = useCampusStore((s) => s.setDataError);
  const [gone, setGone] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([loadCampus(), loadNav(), loadScatter()])
      .then(() => {
        if (!cancelled) setDataReady(true);
      })
      .catch((err: unknown) => {
        if (!cancelled) setDataError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [setDataReady, setDataError]);

  const ready = dataReady && modelReady;
  useEffect(() => {
    if (!ready) return;
    const timer = setTimeout(() => setGone(true), 700);
    return () => clearTimeout(timer);
  }, [ready]);

  if (dataError) {
    return (
      <div className="loader-error" role="alert">
        <div className="loader-error-card">
          <h1>The campus data could not be loaded</h1>
          <p>{dataError}</p>
          <button type="button" onClick={() => window.location.reload()}>
            Retry
          </button>
        </div>
      </div>
    );
  }
  if (gone) return null;

  // Blend JSON readiness with three.js download progress; stop at 99 until the
  // GLB has actually attached so the bar never claims success prematurely.
  const pct = ready ? 100 : Math.min(99, Math.round(dataReady ? 15 + progress * 0.8 : progress * 0.2));
  const step = [...STEPS].reverse().find(([at]) => pct >= at)?.[1] ?? STEPS[0][1];

  return (
    <div className={`loader${ready ? ' loader-ready' : ''}`} data-testid={ready ? undefined : 'loader'}>
      <p className="loader-kicker">Campus in 3D</p>
      <h1 className="loader-title">IIT Ropar</h1>
      <p className="loader-subtitle">Rupnagar · Punjab · India</p>
      <div
        className="loader-track"
        role="progressbar"
        aria-label="Loading the campus model"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
      >
        <div className="loader-fill" style={{ transform: `scaleX(${Math.max(0.04, pct / 100)})` }} />
      </div>
      <p className="loader-step" aria-live="polite">
        {step} <span className="loader-pct">{pct}%</span>
      </p>
    </div>
  );
}
