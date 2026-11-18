import { describe, expect, it } from 'vitest';
import { buildingArraySchema, campusSchema } from '../src/lib/schema';

const validBuilding = {
  id: 'BLDG_hostel_ganga',
  osm_way: 12345,
  name: 'Ganga Hostel',
  aliases: ['Ganga'],
  category: 'hostel' as const,
  floors: 3,
  roof_type: 'flat',
  wall_color: '#c8b08a',
  trim_color: '#5b4632',
  roof_color: '#7a5c3e',
  window_pattern: 'grid',
  verified: false,
  location: { lat: 30.97, lon: 77.34 },
};

const validCampus = {
  name: 'IIT Ropar',
  official_name: 'Indian Institute of Technology Ropar',
  country: 'India',
  polygon: { type: 'Polygon', coordinates: [] },
  bbox: { south: 30.9, north: 31.1, west: 77.2, east: 77.5 },
  buildings: [validBuilding],
};

describe('campusSchema', () => {
  it('accepts a valid campus document', () => {
    const parsed = campusSchema.parse(validCampus);
    expect(parsed.buildings).toHaveLength(1);
  });

  it('accepts an empty buildings array', () => {
    const parsed = campusSchema.parse({ ...validCampus, buildings: [] });
    expect(parsed.buildings).toEqual([]);
  });

  it('rejects a building with an unknown category', () => {
    expect(() => campusSchema.parse({ ...validCampus, buildings: [{ ...validBuilding, category: 'bogus' as never }] })).toThrow();
  });

  it('rejects a building without verified flag', () => {
    const { verified: _v, ...bad } = validBuilding;
    expect(() => campusSchema.parse({ ...validCampus, buildings: [bad] })).toThrow();
  });

  it('accepts building defaults', () => {
    const parsed = buildingArraySchema.parse([
      {
        id: 'x',
        name: 'X',
        category: 'academic',
        verified: true,
        location: { lat: 1, lon: 2 },
      },
    ]);
    expect(parsed[0].floors).toBe(0);
  });
});
