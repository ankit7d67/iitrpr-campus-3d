'use client';

import { useEffect } from 'react';
import { useCampusStore } from '../lib/store';

export function PerfOverlay() {
  const fps = useCampusStore((s) => s.perfFps);
  const setPerfFps = useCampusStore((s) => s.setPerfFps);

  useEffect(() => {
    let frames = 0;
    let raf = 0;
    const loop = () => {
      frames++;
      if (frames >= 30) {
        const f = frames / 0.5;
        setPerfFps(Math.round(f));
        frames = 0;
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [setPerfFps]);

  if (fps == null) return null;
  return <div className="perf-overlay">FPS {fps}</div>;
}
