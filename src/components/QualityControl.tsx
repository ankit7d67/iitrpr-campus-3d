'use client';

import { useCampusStore } from '../lib/store';

export function QualityControl() {
  const quality = useCampusStore((s) => s.quality);
  const setQuality = useCampusStore((s) => s.setQuality);
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
    </div>
  );
}
