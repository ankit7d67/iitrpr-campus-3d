import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { formatDistance, planRoute } from '../src/lib/route';
import type { NavGraph } from '../src/lib/types';

function makeGraph(links: Array<[string, string, number]>): NavGraph {
  const ids = new Set<string>();
  for (const [a, b] of links) {
    ids.add(a);
    ids.add(b);
  }
  const nodes = [...ids].map((id, i) => ({ id, x: i * 10, z: 0 }));
  return { nodes, links: links.map(([from, to, length]) => ({ from, to, length })) };
}

const graph = makeGraph([
  ['ENTR_1', 'n2', 10],
  ['n2', 'ENTR_2', 10],
]);

describe('planRoute', () => {
  it('maps BLDG_ ids to their ENTR_ anchors and plans a path', () => {
    const r = planRoute(graph, 'BLDG_1', 'BLDG_2');
    expect(r).not.toBeNull();
    expect(r!.path.map((n) => n.id)).toEqual(['ENTR_1', 'n2', 'ENTR_2']);
    expect(r!.distanceM).toBeGreaterThan(0);
    expect(r!.steps.length).toBeGreaterThan(0);
  });

  it('returns null when both endpoints are the same building', () => {
    expect(planRoute(graph, 'BLDG_1', 'BLDG_1')).toBeNull();
    expect(planRoute(graph, 'ENTR_1', 'ENTR_1')).toBeNull();
  });

  it('returns null when the endpoints are disconnected', () => {
    const g = makeGraph([
      ['ENTR_1', 'n2', 10],
      ['ENTR_9', 'n8', 10],
    ]);
    expect(planRoute(g, 'BLDG_1', 'BLDG_9')).toBeNull();
  });
});

describe('formatDistance', () => {
  it('formats metres below 1 km and kilometres above', () => {
    expect(formatDistance(837)).toBe('837 m');
    expect(formatDistance(1540)).toBe('1.5 km');
  });
});

describe('planRoute on the shipped nav graph', () => {
  const nav = JSON.parse(readFileSync('public/data/nav.json', 'utf8')) as NavGraph;

  it('plans Nalanda library -> Ravi Girls Hostel (regression: links are bidirectional)', () => {
    const r = planRoute(nav, 'BLDG_1349163385', 'BLDG_1349204070');
    expect(r).not.toBeNull();
    expect(r!.path.length).toBeGreaterThan(2);
    expect(r!.distanceM).toBeGreaterThan(100);
    expect(r!.steps.length).toBeGreaterThan(0);
    // Direction text must be real compass words, never "undefined".
    for (const s of r!.steps) {
      expect(s.instruction).not.toContain('undefined');
      expect(s.instruction).toMatch(/^(Walk|Turn)/);
    }
  });

  it('plans the reverse direction too', () => {
    const r = planRoute(nav, 'BLDG_1349204070', 'BLDG_1349163385');
    expect(r).not.toBeNull();
  });
});
