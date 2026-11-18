import type { NavNode } from './types';

export interface Step {
  instruction: string;
  distanceM: number;
  nodeId?: string;
}

function compass(deg: number): string {
  const dirs = ['north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest'];
  return dirs[Math.round(deg / 45) % 8];
}

/** Convert an A* path into simple step-by-step walking directions. */
export function buildSteps(path: NavNode[], _fromName: string, _toName: string): Step[] {
  const steps: Step[] = [];
  for (let i = 0; i + 1 < path.length; i++) {
    const a = path[i];
    const b = path[i + 1];
    const dist = Math.hypot(b.x - a.x, b.z - a.z);
    if (dist < 1) continue;
    const bearing = (Math.atan2(b.x - a.x, b.z - a.z) * 180) / Math.PI;
    const nextBearing = (Math.atan2(path[i + 2] ? path[i + 2].x - b.x : b.x - a.x, path[i + 2] ? path[i + 2].z - b.z : b.z - a.z) * 180) / Math.PI;
    const turn = Math.abs(((nextBearing - bearing + 540) % 360) - 180);
    const instruction =
      turn > 25
        ? `Turn ${turn > 165 ? 'around' : compass(((bearing + 90) % 360))} toward ${compass(nextBearing)}`
        : `Walk ${compass(bearing)}`;
    steps.push({ instruction, distanceM: dist, nodeId: b.id });
  }
  return steps;
}
