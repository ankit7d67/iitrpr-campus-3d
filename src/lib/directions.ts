import type { NavNode } from './types';

export interface Step {
  instruction: string;
  distanceM: number;
  nodeId?: string;
}

/** Compass label for a heading in degrees (clockwise from north). Negative-safe. */
function compass(deg: number): string {
  const dirs = ['north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest'];
  const i = ((Math.round(deg / 45) % 8) + 8) % 8;
  return dirs[i];
}

/**
 * Heading in degrees, clockwise from north, from a to b.
 * Scene axes are x = east, z = −north, so north = −z.
 */
function heading(a: NavNode, b: NavNode): number {
  return (Math.atan2(b.x - a.x, -(b.z - a.z)) * 180) / Math.PI;
}

/** Convert an A* path into simple step-by-step walking directions. */
export function buildSteps(path: NavNode[], _fromName: string, _toName: string): Step[] {
  const steps: Step[] = [];
  for (let i = 0; i + 1 < path.length; i++) {
    const a = path[i];
    const b = path[i + 1];
    const dist = Math.hypot(b.x - a.x, b.z - a.z);
    if (dist < 1) continue;
    const bearing = heading(a, b);
    // A turn is performed at node a, so compare how we arrived with how this
    // leg departs; the instruction then matches the distance of this leg.
    const prev = i > 0 ? path[i - 1] : null;
    const incoming =
      prev && Math.hypot(a.x - prev.x, a.z - prev.z) >= 1 ? heading(prev, a) : null;
    let instruction: string;
    if (incoming === null) {
      instruction = `Walk ${compass(bearing)}`;
    } else {
      const signed = ((bearing - incoming + 540) % 360) - 180;
      if (Math.abs(signed) > 165) instruction = 'Turn around';
      else if (signed > 25) instruction = `Turn right toward ${compass(bearing)}`;
      else if (signed < -25) instruction = `Turn left toward ${compass(bearing)}`;
      else instruction = `Walk ${compass(bearing)}`;
    }
    steps.push({ instruction, distanceM: dist, nodeId: b.id });
  }
  return steps;
}
