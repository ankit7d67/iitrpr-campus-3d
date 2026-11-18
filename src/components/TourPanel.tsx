'use client';

import { useCampus } from '../lib/data';
import { getTourStops } from '../lib/sun';
import { useCampusStore } from '../lib/store';

export function TourPanel() {
  const { campus } = useCampus();
  const tourStopIndex = useCampusStore((s) => s.tourStopIndex);
  const setTourStopIndex = useCampusStore((s) => s.setTourStopIndex);

  const stops = campus?.buildings ? getTourStops(campus.buildings) : [];

  return (
    <div className="panel tour-panel">
      <h2>Orientation tour</h2>
      <ol>
        {stops.map((s, i) => (
          <li key={s.id}>
            <button
              type="button"
              className={i === tourStopIndex ? 'active' : ''}
              onClick={() => setTourStopIndex(i)}
            >
              {s.name}
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
