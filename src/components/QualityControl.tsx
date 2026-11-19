'use client';

import { useEffect, useRef } from 'react';
import { AUTO_QUALITY_INITIAL, updateAutoQuality, type AutoQualityState } from '../lib/quality';
import { useCampusStore } from '../lib/store';

export function QualityControl() {
  const quality = useCampusStore((s) => s.quality);
  const setQuality = useCampusStore((s) => s.setQuality);
  const autoTier = useCampusStore((s) => s.autoTier);
  const setAutoTier = useCampusStore((s) => s.setAutoTier);
  const perfFps = useCampusStore((s) => s.perfFps);
  const auto = useRef<AutoQualityState>(AUTO_QUALITY_INITIAL);

  // 7-12: Auto mode reacts to the 0.5 s FPS samples published by PerfOverlay.
  // The pure helper supplies the hysteresis/cooldown (see tests/quality.test.ts).
  useEffect(() => {
    if (quality !== 'auto' || perfFps == null) return;
    const { next, changed } = updateAutoQuality(auto.current, perfFps, performance.now());
    auto.current = next;
    if (changed) setAutoTier(next.tier);
  }, [quality, perfFps, setAutoTier]);

  const effective = quality === 'auto' ? autoTier : quality;
  return (
    <div className="quality-control">
      <label htmlFor="quality">Quality</label>
      <select
        id="quality"
        value={quality}
        onChange={(e) => setQuality(e.target.value as 'auto' | 'low' | 'high')}
      >
        <option value="auto">Auto</option>
        <option value="low">Low</option>
        <option value="high">High</option>
      </select>
      <span className="quality-effective" data-testid="quality-effective">
        {quality === 'auto' ? `Auto · ${effective}` : effective}
      </span>
    </div>
  );
}
