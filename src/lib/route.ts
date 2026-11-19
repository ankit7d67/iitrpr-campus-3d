import { astar, type RouteResult } from './astar';
import { buildSteps, type Step } from './directions';
import type { NavGraph } from './types';

export interface PlannedRoute {
  path: RouteResult['path'];
  distanceM: number;
  steps: Step[];
}

/**
 * Plan a walking route between two UI ids.
 *
 * UI ids come in two flavours: `BLDG_<osm_id>` (building list, deep links,
 * search) and `ENTR_<osm_id>` (nav-graph entrance anchors). Buildings map to
 * their entrance anchor; a route to itself is null.
 */
export function planRoute(nav: NavGraph, fromId: string, toId: string): PlannedRoute | null {
  const from = fromId.startsWith('BLDG_') ? `ENTR_${fromId.slice(5)}` : fromId;
  const to = toId.startsWith('BLDG_') ? `ENTR_${toId.slice(5)}` : toId;
  if (from === to) return null;
  const result = astar(nav, from, to);
  if (!result) return null;
  return {
    path: result.path,
    distanceM: result.distanceM,
    steps: buildSteps(result.path, fromId, toId),
  };
}

/** Format a walking distance for display (m below 1 km, km above). */
export function formatDistance(m: number): string {
  if (m < 1000) return `${Math.round(m)} m`;
  return `${(m / 1000).toFixed(1)} km`;
}
