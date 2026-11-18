import { z } from 'zod';

export const categorySchema = z.enum([
  'academic',
  'hostel',
  'admin',
  'sports',
  'food',
  'medical',
  'gate',
  'other',
]);

const str = z.string();
const num = z.number();
const bool = z.boolean();
const strArray = z.array(z.string());

export const buildingSchema = z.object({
  id: str.min(1),
  osm_way: num.int().nullable().optional(),
  name: str.min(1),
  aliases: strArray.default([]),
  category: categorySchema,
  floors: num.int().min(0).default(0),
  roof_type: str.default(''),
  wall_color: str.default(''),
  trim_color: str.default(''),
  roof_color: str.default(''),
  window_pattern: str.default(''),
  move_m: z.object({ east: num, north: num }).nullable().optional(),
  style: str.optional(),
  pad_group: str.optional(),
  verified: bool,
  location: z.object({ lat: num, lon: num }),
  bounds: z.object({ minX: num, maxX: num, minZ: num, maxZ: num }).optional(),
  rooms: z.array(z.object({ id: str, number: str, floor: num.optional(), kind: str.optional() })).default([]),
  hours: str.optional(),
  tour_stop: num.int().optional(),
});

export const campusSchema = z.object({
  name: str,
  official_name: str,
  country: str,
  polygon: z.unknown(),
  bbox: z.object({ south: num, north: num, west: num, east: num }),
  buildings: z.array(buildingSchema),
});

export type Campus = z.infer<typeof campusSchema>;
export type Building = z.infer<typeof buildingSchema>;

export const buildingArraySchema = z.array(buildingSchema);
