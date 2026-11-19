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

  it('defaults tours and landmarks to empty arrays', () => {
    const parsed = campusSchema.parse(validCampus);
    expect(parsed.tours).toEqual([]);
    expect(parsed.landmarks).toEqual([]);
  });

  it('accepts valid tours and landmarks', () => {
    const parsed = campusSchema.parse({
      ...validCampus,
      tours: [{ id: 'orientation', title: 'Orientation tour', stops: [{ bid: validBuilding.id, note: 'Hello' }] }],
      landmarks: [{ id: 'library', name: 'Library', bid: validBuilding.id }],
    });
    expect(parsed.tours).toHaveLength(1);
    expect(parsed.landmarks).toHaveLength(1);
  });

  it('rejects duplicate building ids', () => {
    expect(() => campusSchema.parse({ ...validCampus, buildings: [validBuilding, validBuilding] })).toThrow();
  });

  it('rejects a room floor above the building floors', () => {
    expect(() =>
      campusSchema.parse({
        ...validCampus,
        buildings: [{ ...validBuilding, rooms: [{ id: 'r1', number: '101', floor: 99 }] }],
      }),
    ).toThrow();
  });

  it('rejects a tour stop referencing an unknown building', () => {
    expect(() =>
      campusSchema.parse({
        ...validCampus,
        tours: [{ id: 't1', title: 'Tour', stops: [{ bid: 'BLDG_nope' }] }],
      }),
    ).toThrow();
  });

  it('rejects a landmark referencing an unknown building', () => {
    expect(() =>
      campusSchema.parse({
        ...validCampus,
        landmarks: [{ id: 'lm', name: 'Nowhere', bid: 'BLDG_nope' }],
      }),
    ).toThrow();
  });

  it('rejects duplicate tour ids', () => {
    const tour = { id: 't1', title: 'Tour', stops: [{ bid: validBuilding.id }] };
    expect(() => campusSchema.parse({ ...validCampus, tours: [tour, tour] })).toThrow();
  });

  it('rejects duplicate landmark ids', () => {
    const lm = { id: 'lm', name: 'Library', bid: validBuilding.id };
    expect(() => campusSchema.parse({ ...validCampus, landmarks: [lm, lm] })).toThrow();
  });

  it('parses the real campus document with tours and landmarks', async () => {
    const raw = JSON.parse(await import('node:fs').then((fs) => fs.readFileSync('public/data/campus.json', 'utf8')));
    const parsed = campusSchema.parse(raw);
    expect(parsed.buildings.length).toBeGreaterThanOrEqual(50);
    expect(parsed.tours.length).toBeGreaterThanOrEqual(1);
    expect(parsed.landmarks.length).toBeGreaterThanOrEqual(1);
  });
});
