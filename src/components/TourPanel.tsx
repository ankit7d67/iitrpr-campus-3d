'use client';

import { useCampus } from '../lib/data';
import { useCampusStore } from '../lib/store';

/**
 * Orientation tour (Phase 7 item 7-6).
 *
 * Reads the hand-maintained `tours[0]` overlay (stops = building id + note,
 * note wording is name + OSM category only). Selecting a stop highlights it,
 * shows its note and counter, and flies the camera to the building.
 */
export function TourPanel() {
  const { campus } = useCampus();
  const tourStopIndex = useCampusStore((s) => s.tourStopIndex);
  const setTourStopIndex = useCampusStore((s) => s.setTourStopIndex);
  const focusOn = useCampusStore((s) => s.focusOn);

  const tour = campus?.tours?.[0];
  const buildings = campus?.buildings ?? [];
  const stops = tour?.stops ?? [];

  if (!tour || stops.length === 0) {
    return (
      <div className="panel tour-panel">
        <h2>Orientation tour</h2>
        <p className="muted">No tour stops.</p>
      </div>
    );
  }

  const index = Math.min(Math.max(tourStopIndex, 0), stops.length - 1);
  const active = stops[index];
  const nameOf = (bid: string) => buildings.find((b) => b.id === bid)?.name ?? bid;

  const select = (i: number) => {
    setTourStopIndex(i);
    focusOn(stops[i].bid);
  };

  return (
    <div className="panel tour-panel">
      <h2>{tour.title}</h2>
      <ol>
        {stops.map((s, i) => (
          <li key={s.bid}>
            <button
              type="button"
              className={i === index ? 'active' : ''}
              onClick={() => select(i)}
            >
              {nameOf(s.bid)}
            </button>
          </li>
        ))}
      </ol>
      <div className="tour-note">
        <span className="tour-counter">
          {index + 1} / {stops.length}
        </span>
        <p className="tour-note-text">{active.note}</p>
      </div>
      <div className="tour-nav">
        <button
          type="button"
          onClick={() => select(Math.max(0, index - 1))}
          disabled={index === 0}
        >
          Prev
        </button>
        <button
          type="button"
          onClick={() => select(Math.min(stops.length - 1, index + 1))}
          disabled={index === stops.length - 1}
        >
          Next
        </button>
      </div>
    </div>
  );
}
