'use client';

import { useEffect, useMemo, useState } from 'react';
import { Line } from '@react-three/drei';
import { loadNav } from '../lib/data';
import { astar } from '../lib/astar';
import type { NavGraph } from '../lib/types';

interface Props {
  fromId: string;
  toId: string;
}

export function RouteRenderer({ fromId, toId }: Props) {
  const [nav, setNav] = useState<NavGraph | null>(null);

  useEffect(() => {
    let cancelled = false;
    loadNav().then((n) => {
      if (!cancelled) setNav(n);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const result = useMemo(() => {
    if (!nav) return null;
    // Route endpoints are entrance markers (ENTR_<osm_id>) placed on the nearest path;
    // deep links from the building list use the BLDG_<osm_id> building ids, so map them.
    const from = fromId.startsWith('BLDG_') ? `ENTR_${fromId.slice(5)}` : fromId;
    const to = toId.startsWith('BLDG_') ? `ENTR_${toId.slice(5)}` : toId;
    if (from === to) return null;
    const r = astar(nav, from, to);
    if (!r) return null;
    const linePoints = r.path.map((n) => [n.x, 0.6, n.z] as [number, number, number]);
    return { ...r, linePoints };
  }, [nav, fromId, toId]);

  if (!result) return null;

  return (
    <Line
      points={result.linePoints}
      color="#2f7de1"
      lineWidth={4}
      dashed
      dashSize={2}
      gapSize={1}
      opacity={0.9}
    />
  );
}
