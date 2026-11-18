import { describe, expect, it } from 'vitest';
import { searchBuildings } from '../src/lib/search';
import type { Building } from '../src/lib/types';

const buildings: Building[] = [
  {
    id: 'BLDG_hostel_ganga',
    osm_way: 1,
    name: 'Ganga Hostel',
    aliases: ['Ganga'],
    category: 'hostel',
    floors: 3,
    roof_type: 'flat',
    wall_color: '',
    trim_color: '',
    roof_color: '',
    window_pattern: '',
    verified: false,
    location: { lat: 30.97, lon: 77.34 },
  },
  {
    id: 'BLDG_lib',
    osm_way: 2,
    name: 'Central Library',
    aliases: ['Library'],
    category: 'academic',
    floors: 4,
    roof_type: 'flat',
    wall_color: '',
    trim_color: '',
    roof_color: '',
    window_pattern: '',
    verified: false,
    location: { lat: 30.98, lon: 77.35 },
  },
];

describe('searchBuildings', () => {
  it('returns all buildings for an empty query', () => {
    expect(searchBuildings(buildings, '').length).toBe(2);
  });

  it('matches by partial name', () => {
    const res = searchBuildings(buildings, 'ganga');
    expect(res[0].id).toBe('BLDG_hostel_ganga');
  });

  it('matches by alias', () => {
    const res = searchBuildings(buildings, 'lib');
    expect(res.some((b) => b.id === 'BLDG_lib')).toBe(true);
  });

  it('returns nothing for gibberish', () => {
    expect(searchBuildings(buildings, 'zzzznotathing').length).toBe(0);
  });
});
