'use client';

import { useEffect } from 'react';
import { useCampus } from '../lib/data';
import { useCampusStore } from '../lib/store';

export function BuildingPanel() {
  const { campus } = useCampus();
  const selectedBuildingId = useCampusStore((s) => s.selectedBuildingId);
  const setSelectedBuildingId = useCampusStore((s) => s.setSelectedBuildingId);
  const infoOpen = useCampusStore((s) => s.infoOpen);
  const setInfoOpen = useCampusStore((s) => s.setInfoOpen);
  const buildings = campus?.buildings ?? [];
  const building = buildings.find((b) => b.id === selectedBuildingId);

  useEffect(() => {
    if (!infoOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setInfoOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [infoOpen, setInfoOpen]);

  if (!infoOpen || !building) return null;

  return (
    <div className="panel building-panel" role="dialog" aria-modal="true" aria-label={building.name}>
      <h2>{building.name}</h2>
      <p className="muted">
        {building.category} · {building.verified ? 'verified' : 'unverified (placeholder)'}
      </p>
      <dl>
        <dt>Floors</dt>
        <dd>{building.floors || '—'}</dd>
        <dt>Roof</dt>
        <dd>{building.roof_type || '—'}</dd>
        <dt>Wall</dt>
        <dd>{building.wall_color || '—'}</dd>
      </dl>
      <button type="button" onClick={() => { setInfoOpen(false); setSelectedBuildingId(null); }}>
        Close
      </button>
    </div>
  );
}
