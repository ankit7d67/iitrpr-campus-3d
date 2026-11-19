'use client';

import { useEffect, useMemo, useState } from 'react';
import { loadNav, useCampus } from '../lib/data';
import { useCampusStore } from '../lib/store';
import { formatDistance, planRoute } from '../lib/route';
import type { NavGraph } from '../lib/types';

export function RoutePanel() {
  const { campus } = useCampus();
  const route = useCampusStore((s) => s.route);
  const setRoute = useCampusStore((s) => s.setRoute);
  const buildings = campus?.buildings ?? [];

  const [nav, setNav] = useState<NavGraph | null>(null);
  const [fromId, setFromId] = useState('');
  const [toId, setToId] = useState('');

  useEffect(() => {
    let cancelled = false;
    loadNav().then((n) => {
      if (!cancelled) setNav(n);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  // Keep the pickers in sync with routes set elsewhere (deep links, search).
  useEffect(() => {
    if (route) {
      setFromId(route.fromId);
      setToId(route.toId);
    }
  }, [route]);

  const planned = useMemo(() => {
    if (!nav || !route) return null;
    return planRoute(nav, route.fromId, route.toId);
  }, [nav, route]);

  const from = route ? buildings.find((b) => b.id === route.fromId) : undefined;
  const to = route ? buildings.find((b) => b.id === route.toId) : undefined;

  const options = buildings.map((b) => (
    <option key={b.id} value={b.id}>
      {b.name}
    </option>
  ));

  if (!route) {
    return (
      <div className="panel">
        <h2>Walking route</h2>
        <div className="route-form">
          <label>
            From
            <select value={fromId} onChange={(e) => setFromId(e.target.value)}>
              <option value="">Choose building…</option>
              {options}
            </select>
          </label>
          <label>
            To
            <select value={toId} onChange={(e) => setToId(e.target.value)}>
              <option value="">Choose building…</option>
              {options}
            </select>
          </label>
          <button
            type="button"
            disabled={!fromId || !toId || fromId === toId}
            onClick={() => setRoute({ fromId, toId })}
          >
            Route
          </button>
        </div>
        {fromId && fromId === toId && <p className="muted">Pick two different buildings.</p>}
      </div>
    );
  }

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
      {planned ? (
        <>
          <p className="muted">
            {formatDistance(planned.distanceM)} · {planned.steps.length} step
            {planned.steps.length === 1 ? '' : 's'}
          </p>
          <ol className="route-steps">
            {planned.steps.map((s, i) => (
              <li key={`${s.nodeId ?? i}-${i}`}>
                {s.instruction} <span className="muted">({formatDistance(s.distanceM)})</span>
              </li>
            ))}
          </ol>
        </>
      ) : (
        <p className="muted">No walking path found.</p>
      )}
      <div className="route-actions">
        <button type="button" onClick={() => setRoute(null)}>
          Clear
        </button>
      </div>
    </div>
  );
}
