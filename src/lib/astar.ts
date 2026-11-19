import type { NavGraph, NavLink, NavNode } from './types';

export interface RouteResult {
  path: NavNode[];
  links: NavLink[];
  distanceM: number;
}

export function findNode(graph: NavGraph, id: string): NavNode | undefined {
  return graph.nodes.find((n) => n.id === id);
}

function heuristic(a: NavNode, b: NavNode): number {
  return Math.hypot(a.x - b.x, a.z - b.z);
}

/** A* shortest path over the walking network. */
export function astar(graph: NavGraph, startId: string, goalId: string): RouteResult | null {
  const nodes = new Map<string, NavNode>();
  for (const n of graph.nodes) nodes.set(n.id, n);
  const linksByFrom = new Map<string, NavLink[]>();
  const push = (l: NavLink) => {
    const arr = linksByFrom.get(l.from) ?? [];
    arr.push(l);
    linksByFrom.set(l.from, arr);
  };
  for (const l of graph.links) {
    // Walking links are bidirectional: nav.json stores each edge once, so expand
    // it in both directions (otherwise most origin/destination pairs are
    // unreachable and no route renders).
    push(l);
    push({ from: l.to, to: l.from, length: l.length });
  }
  if (!nodes.has(startId) || !nodes.has(goalId)) return null;

  const open = new Map<string, number>([[startId, 0]]);
  const gScore = new Map<string, number>([[startId, 0]]);
  const cameFrom = new Map<string, { id: string; via: NavLink }>();
  const closed = new Set<string>();

  while (open.size > 0) {
    let bestId: string | null = null;
    let bestScore = Infinity;
    for (const [id, sc] of open) {
      if (sc < bestScore) {
        bestScore = sc;
        bestId = id;
      }
    }
    const current = nodes.get(bestId as string)!;
    open.delete(bestId as string);
    if (bestId === goalId) break;
    closed.add(bestId!);
    const currentG = gScore.get(bestId!) ?? 0;
    for (const link of linksByFrom.get(bestId!) ?? []) {
      if (closed.has(link.to)) continue;
      const nb = nodes.get(link.to)!;
      const weight = Math.hypot(nb.x - current.x, nb.z - current.z);
      const tentative = currentG + weight;
      if (tentative < (gScore.get(link.to) ?? Infinity) - 1e-9) {
        gScore.set(link.to, tentative);
        cameFrom.set(link.to, { id: bestId!, via: link });
        const f = tentative + heuristic(nb, nodes.get(goalId)!);
        open.set(link.to, f);
      }
    }
  }

  if (!gScore.has(goalId)) return null;

  const path: NavNode[] = [];
  let cursor: string | undefined = goalId;
  const usedLinks: NavLink[] = [];
  while (cursor) {
    const n = nodes.get(cursor)!;
    path.unshift(n);
    const prev = cameFrom.get(cursor);
    if (!prev) break;
    usedLinks.unshift(prev.via);
    cursor = prev.id;
  }
  const distanceM = usedLinks.reduce((acc, l) => acc + l.length, 0) || (path.length ? heuristic(path[0], path[path.length - 1]) : 0);
  return { path, links: usedLinks, distanceM };
}
