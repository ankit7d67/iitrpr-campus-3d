import { useEffect, useState } from 'react';
import { campusSchema, buildingArraySchema } from './schema';
import type { Building, Campus, NavGraph, ScatterEntry } from './types';

let campusCache: Campus | null = null;
let navCache: NavGraph | null = null;
let scatterCache: ScatterEntry[] | null = null;

export async function loadCampus(): Promise<Campus> {
  if (campusCache) return campusCache;
  const res = await fetch('/data/campus.json');
  if (!res.ok) throw new Error(`Failed to load /data/campus.json (${res.status})`);
  const raw = (await res.json()) as unknown;
  const parsed = campusSchema.parse(raw) as Campus;
  campusCache = parsed;
  return parsed;
}

export async function loadNav(): Promise<NavGraph> {
  if (navCache) return navCache;
  const res = await fetch('/data/nav.json');
  if (!res.ok) throw new Error(`Failed to load /data/nav.json (${res.status})`);
  const raw = (await res.json()) as unknown;
  const parsed = JSON.parse(JSON.stringify(raw)) as NavGraph;
  navCache = parsed;
  return parsed;
}

export async function loadScatter(): Promise<ScatterEntry[]> {
  if (scatterCache) return scatterCache;
  const res = await fetch('/data/scatter.json');
  if (!res.ok) throw new Error(`Failed to load /data/scatter.json (${res.status})`);
  const raw = (await res.json()) as unknown;
  const parsed = (Array.isArray(raw) ? raw : (raw as { scatter?: ScatterEntry[] }).scatter ?? []) as ScatterEntry[];
  scatterCache = parsed;
  return parsed;
}

export function getBuilding(id: string | null | undefined, campus: Campus): Building | undefined {
  if (!id) return undefined;
  return (campus.buildings as Building[]).find((b) => b.id === id);
}

export function buildingList(campus: Campus): Building[] {
  return buildingArraySchema.parse(campus.buildings) as Building[];
}

/** React hook: fetch + parse campus.json. */
export function useCampus(): { campus: Campus | null; error: string | null } {
  const [campus, setCampus] = useState<Campus | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    loadCampus()
      .then((c) => {
        if (!cancelled) setCampus(c);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load campus data');
      });
    return () => {
      cancelled = true;
    };
  }, []);
  return { campus, error };
}
