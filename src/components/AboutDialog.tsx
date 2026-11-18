'use client';

import { useCampusStore } from '../lib/store';

export function AboutDialog() {
  const open = useCampusStore((s) => s.aboutOpen);
  const setAboutOpen = useCampusStore((s) => s.setAboutOpen);

  if (!open) return null;
  return (
    <div className="dialog-backdrop" role="presentation">
      <div className="dialog" role="dialog" aria-modal="true" aria-label="About">
        <h2>About this project</h2>
        <p>
          Unofficial student project. Not affiliated with or endorsed by the Indian Institute of
          Technology Ropar.
        </p>
        <p>
          Campus geometry © OpenStreetMap contributors, ODbL. Rendering procedurally in Blender.
        </p>
        <button type="button" onClick={() => setAboutOpen(false)}>Close</button>
      </div>
    </div>
  );
}
