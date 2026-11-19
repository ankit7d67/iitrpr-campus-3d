'use client';

import { Html } from '@react-three/drei';
import { useFrame, useThree } from '@react-three/fiber';
import { useEffect, useMemo, useState } from 'react';
import type { ReactElement } from 'react';
import { loadNav, useCampus } from '../lib/data';
import { useCampusStore } from '../lib/store';

type Anchor = [number, number, number];

/** Farther than this the landmark tags are hidden (the selected one stays). */
const FAR_DISTANCE = 3200;

/**
 * Phase 7 item 7-11: name tags for a few landmarks plus the selected building.
 * Positions come from the GLB building bounding-box tops (`anchors` computed in
 * CampusScene); nav.json entrance nodes are a fallback for low quality, which
 * never loads the GLB. Clicking a tag selects the building and flies the camera
 * to it through the existing `focusOn` / `CameraFocus` mechanism.
 */
export function Labels({ anchors }: { anchors: Record<string, Anchor> }): ReactElement | null {
  const { campus } = useCampus();
  const selected = useCampusStore((s) => s.selectedBuildingId);
  const focusOn = useCampusStore((s) => s.focusOn);
  const setSelectedBuildingId = useCampusStore((s) => s.setSelectedBuildingId);
  const setInfoOpen = useCampusStore((s) => s.setInfoOpen);
  const camera = useThree((s) => s.camera);
  const [far, setFar] = useState(false);
  const [navAnchors, setNavAnchors] = useState<Record<string, Anchor>>({});

  useEffect(() => {
    let cancelled = false;
    loadNav()
      .then((nav) => {
        if (cancelled) return;
        const next: Record<string, Anchor> = {};
        for (const node of nav.nodes) {
          if (!node.id.startsWith('ENTR_')) continue;
          next[`BLDG_${node.id.slice(5)}`] = [node.x, 25, node.z];
        }
        setNavAnchors(next);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  useFrame(() => {
    const isFar = camera.position.length() > FAR_DISTANCE;
    setFar((prev) => (prev === isFar ? prev : isFar));
  });

  const landmarkIds = useMemo(
    () => (campus?.landmarks ?? []).map((l) => l.bid),
    [campus],
  );
  if (!campus) return null;

  const ids = new Set<string>(far ? [] : landmarkIds);
  if (selected) ids.add(selected);

  return (
    <>
      {[...ids].map((id) => {
        const building = campus.buildings.find((b) => b.id === id);
        const anchor = anchors[id] ?? navAnchors[id];
        if (!building || !anchor) return null;
        const active = id === selected;
        return (
          <Html key={id} position={anchor} center zIndexRange={[20, 0]} style={{ pointerEvents: 'auto' }}>
            <button
              type="button"
              data-testid="map-label"
              className={`map-label${active ? ' map-label-active' : ''}`}
              onClick={() => {
                focusOn(id);
                setSelectedBuildingId(id);
                setInfoOpen(true);
              }}
            >
              {building.name}
            </button>
          </Html>
        );
      })}
    </>
  );
}
