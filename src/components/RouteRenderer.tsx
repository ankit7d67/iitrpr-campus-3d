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
    if (!nav || fromId === toId) return null;
    const r = astar(nav, fromId, toId);
    if (!r) return null;
    const linePoints = r.path.map((n) => [n.x, Math.max(0, n.z), n.z] as [number, number, number]);
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
