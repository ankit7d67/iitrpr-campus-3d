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

  // Scene axes: x = east, z = −north.
  it('labels the four cardinal headings correctly', () => {
    const cases: Array<[NavNode, string]> = [
      [{ id: 'n', x: 0, z: -10 }, 'Walk north'],
      [{ id: 's', x: 0, z: 10 }, 'Walk south'],
      [{ id: 'e', x: 10, z: 0 }, 'Walk east'],
      [{ id: 'w', x: -10, z: 0 }, 'Walk west'],
    ];
    for (const [to, expected] of cases) {
      const steps = buildSteps([{ id: 'a', x: 0, z: 0 }, to], 'A', 'B');
      expect(steps[0].instruction).toBe(expected);
    }
  });

  it('never emits "undefined" and reports turns as left/right', () => {
    // north, then east: a right turn.
    const path: NavNode[] = [
      { id: 'a', x: 0, z: 0 },
      { id: 'b', x: 0, z: -10 },
      { id: 'c', x: 10, z: -10 },
      { id: 'd', x: 20, z: -10 },
    ];
    const steps = buildSteps(path, 'A', 'D');
    const text = steps.map((s) => s.instruction).join(' | ');
    expect(text).not.toContain('undefined');
    expect(steps[0].instruction).toBe('Walk north');
    expect(steps[1].instruction).toBe('Turn right toward east');
    expect(steps[2].instruction).toBe('Walk east');
  });

  it('reports a left turn', () => {
    // north, then west.
    const path: NavNode[] = [
      { id: 'a', x: 0, z: 0 },
      { id: 'b', x: 0, z: -10 },
      { id: 'c', x: -10, z: -10 },
      { id: 'd', x: -20, z: -10 },
    ];
    const steps = buildSteps(path, 'A', 'D');
    expect(steps[1].instruction).toBe('Turn left toward west');
  });
});
