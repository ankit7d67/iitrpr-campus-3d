import { describe, expect, it } from 'vitest';
import { astar } from '../src/lib/astar';
import type { NavGraph } from '../src/lib/types';

function makeGraph(links: Array<[string, string, number]>, coords: Record<string, [number, number]> = {}): NavGraph {
  const ids = new Set<string>();
  for (const [a, b] of links) {
    ids.add(a);
    ids.add(b);
  }
  const nodes = [...ids].map((id) => ({ id, x: coords[id]?.[0] ?? 0, z: coords[id]?.[1] ?? 0 }));
  const nodeIds = new Set<string>(ids);
  const fullNodes = [...nodeIds].map((id, i) => ({ id, x: coords[id]?.[0] ?? i * 10, z: coords[id]?.[1] ?? 0 }));
  return { nodes: fullNodes, links: links.map(([from, to, length]) => ({ from, to, length })) };
}

describe('astar', () => {
  it('finds a path through a linear graph', () => {
    const g = makeGraph([
      ['a', 'b', 10],
      ['b', 'c', 10],
    ], { a: [0, 0], b: [0, 10], c: [0, 20] });
    const r = astar(g, 'a', 'c');
    expect(r).not.toBeNull();
    expect(r!.path.map((n) => n.id)).toEqual(['a', 'b', 'c']);
    expect(r!.distanceM).toBeGreaterThan(0);
  });

  it('returns null for unknown nodes', () => {
    const g = makeGraph([]);
    expect(astar(g, 'nope', 'nada')).toBeNull();
  });
});
