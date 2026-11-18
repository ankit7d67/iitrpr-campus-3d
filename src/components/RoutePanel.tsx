'use client';

import { useCampus } from '../lib/data';
import { useCampusStore } from '../lib/store';

export function RoutePanel() {
  const { campus } = useCampus();
  const route = useCampusStore((s) => s.route);
  const setRoute = useCampusStore((s) => s.setRoute);
  const buildings = campus?.buildings ?? [];

  if (!route) {
    return (
      <div className="panel">
        <h2>Walking route</h2>
        <p className="muted">No route selected.</p>
      </div>
    );
  }

  const from = buildings.find((b) => b.id === route.fromId);
  const to = buildings.find((b) => b.id === route.toId);
  return (
    <div className="panel">
      <h2>Walking route</h2>
      {from && to ? (
        <p>
          {from.name} → {to.name}
        </p>
      ) : (
        <p className="muted">Unknown endpoints.</p>
      )}
      <button type="button" onClick={() => setRoute(null)}>Clear</button>
    </div>
  );
}
