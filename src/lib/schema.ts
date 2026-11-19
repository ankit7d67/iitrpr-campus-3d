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

export const roomSchema = z.object({ id: str, number: str, floor: num.optional(), kind: str.optional() });

export const tourStopSchema = z.object({ bid: str.min(1), note: str.optional() });

export const tourSchema = z.object({
  id: str.min(1),
  title: str.min(1),
  stops: z.array(tourStopSchema).min(1),
});

export const landmarkSchema = z.object({ id: str.min(1), name: str.min(1), bid: str.min(1) });

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
  rooms: z.array(roomSchema).default([]),
  hours: str.optional(),
  tour_stop: num.int().optional(),
});

export const campusSchema = z
  .object({
    name: str,
    official_name: str,
    country: str,
    polygon: z.unknown(),
    bbox: z.object({ south: num, north: num, west: num, east: num }),
    buildings: z.array(buildingSchema),
    tours: z.array(tourSchema).default([]),
    landmarks: z.array(landmarkSchema).default([]),
  })
  .superRefine((val, ctx) => {
    const seenBuildingIds = new Set<string>();
    val.buildings.forEach((b, i) => {
      if (seenBuildingIds.has(b.id)) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, path: ['buildings', i, 'id'], message: `duplicate building id ${b.id}` });
      }
      seenBuildingIds.add(b.id);
      b.rooms.forEach((r, j) => {
        if (r.floor != null && (r.floor < 0 || r.floor > b.floors)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ['buildings', i, 'rooms', j, 'floor'],
            message: `room ${r.number} is on floor ${r.floor} but ${b.id} has ${b.floors} floors`,
          });
        }
      });
    });

    const seenTourIds = new Set<string>();
    val.tours.forEach((t, i) => {
      if (seenTourIds.has(t.id)) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, path: ['tours', i, 'id'], message: `duplicate tour id ${t.id}` });
      }
      seenTourIds.add(t.id);
      t.stops.forEach((s, j) => {
        if (!seenBuildingIds.has(s.bid)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ['tours', i, 'stops', j, 'bid'],
            message: `tour stop ${s.bid} is not a building`,
          });
        }
      });
    });

    const seenLandmarkIds = new Set<string>();
    val.landmarks.forEach((l, i) => {
      if (seenLandmarkIds.has(l.id)) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, path: ['landmarks', i, 'id'], message: `duplicate landmark id ${l.id}` });
      }
      seenLandmarkIds.add(l.id);
      if (!seenBuildingIds.has(l.bid)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['landmarks', i, 'bid'],
          message: `landmark ${l.id} references unknown building ${l.bid}`,
        });
      }
    });
  });

export type Campus = z.infer<typeof campusSchema>;
export type Building = z.infer<typeof buildingSchema>;
export type Tour = z.infer<typeof tourSchema>;
export type Landmark = z.infer<typeof landmarkSchema>;

export const buildingArraySchema = z.array(buildingSchema);
