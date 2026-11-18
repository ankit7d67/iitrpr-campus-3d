import { describe, expect, it } from 'vitest';
import { buildSteps } from '../src/lib/directions';
import type { NavNode } from '../src/lib/types';

describe('buildSteps', () => {
  it('emits a step with distance for a two-node path', () => {
    const path: NavNode[] = [
      { id: 'a', x: 0, z: 0 },
      { id: 'b', x: 0, z: 10 },
    ];
    const steps = buildSteps(path, 'A', 'B');
    expect(steps).toHaveLength(1);
    expect(steps[0].distanceM).toBeGreaterThan(0);
    expect(steps[0].instruction.length).toBeGreaterThan(0);
  });
});
