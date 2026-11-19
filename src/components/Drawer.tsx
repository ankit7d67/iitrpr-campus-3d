'use client';

import { useEffect } from 'react';
import { useCampusStore } from '../lib/store';

/**
 * Slide-out control drawer (Phase 7 item 7-4).
 *
 * Houses the primary controls (title, search, quality). Defaults to open so
 * deep links, search and tour e2e tests always find their controls; the user
 * can collapse it to give the map more room. Escape closes it.
 */
export function Drawer({ label, children }: { label: string; children: React.ReactNode }) {
  const open = useCampusStore((s) => s.drawerOpen);
  const setDrawerOpen = useCampusStore((s) => s.setDrawerOpen);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setDrawerOpen(false);
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, setDrawerOpen]);

  return (
    <>
      <div
        className={`drawer ${open ? 'open' : 'closed'}`}
        aria-hidden={!open}
        aria-label={label}
      >
        <button
          type="button"
          className="drawer-close"
          onClick={() => setDrawerOpen(false)}
          aria-label={`Close ${label}`}
          title="Collapse (Esc)"
        >
          &#171;
        </button>
        <div className="drawer-body">{children}</div>
      </div>
      {!open && (
        <button
          type="button"
          className="drawer-open"
          onClick={() => setDrawerOpen(true)}
          aria-label={`Open ${label}`}
          title="Open controls"
        >
          &#9776;
        </button>
      )}
    </>
  );
}
