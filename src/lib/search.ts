import type { Building, Category } from './types';

const CATEGORY_LABELS: Record<Category, string> = {
  academic: 'Academic',
  hostel: 'Hostel',
  admin: 'Administration',
  sports: 'Sports',
  food: 'Food',
  medical: 'Medical',
  gate: 'Gate',
  other: 'Other',
};

export function categoryLabel(c: Category): string {
  return CATEGORY_LABELS[c] ?? c;
}

export function searchBuildings(buildings: Building[], query: string): Building[] {
  const q = query.trim().toLowerCase();
  const tokens = q.split(/\s+/).filter(Boolean);
  const list = buildings;
  if (tokens.length === 0) return list;

  const scored = list
    .map((b) => {
      const haystacks = [b.name, ...(b.aliases ?? []), categoryLabel(b.category), b.style ?? '', b.id]
        .join(' ')
        .toLowerCase();
      const tokenHits = tokens.map((t) => haystacks.includes(t));
      const nameHits = tokens.filter((t) => b.name.toLowerCase().includes(t)).length;
      const aliasHits = tokens.filter((t) => (b.aliases ?? []).some((a) => a.toLowerCase().includes(t))).length;
      const score = nameHits * 3 + aliasHits * 2 + tokenHits.filter(Boolean).length * 0.5;
      return { b, score, tokenHits };
    })
    .filter((s) => tokens.every((t, i) => s.tokenHits[i]));

  return scored
    .sort((a, b2) => b2.score - a.score)
    .map((s) => s.b);
}
