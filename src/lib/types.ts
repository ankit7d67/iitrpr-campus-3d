export type Category =
  | 'academic'
  | 'hostel'
  | 'admin'
  | 'sports'
  | 'food'
  | 'medical'
  | 'gate'
  | 'other';

export interface Room {
  id: string;
  number: string;
  floor?: number;
  kind?: string;
}

export interface Building {
  id: string;
  osm_way: number | null;
  name: string;
  aliases: string[];
  category: Category;
  floors: number;
  roof_type: string;
  wall_color: string;
  trim_color: string;
  roof_color: string;
  window_pattern: string;
  move_m?: { east: number; north: number } | null;
  style?: string;
  pad_group?: string;
  verified: boolean;
  location: { lat: number; lon: number };
  bounds?: { minX: number; maxX: number; minZ: number; maxZ: number };
  rooms?: Room[];
  hours?: string;
  tour_stop?: number;
}

export interface TourStop {
  bid: string;
  note?: string;
}

export interface Tour {
  id: string;
  title: string;
  stops: TourStop[];
}

export interface Landmark {
  id: string;
  name: string;
  bid: string;
}

export interface Campus {
  name: string;
  official_name: string;
  country: string;
  polygon: unknown;
  bbox: { south: number; north: number; west: number; east: number };
  buildings: Building[];
  tours: Tour[];
  landmarks: Landmark[];
}

export interface ScatterEntry {
  type: string;
  id: string;
  position: [number, number, number];
  rotation?: [number, number, number];
  scale?: number;
  meta?: Record<string, unknown>;
}

export interface NavNode {
  id: string;
  x: number;
  z: number;
}

export interface NavLink {
  from: string;
  to: string;
  length: number;
}

export interface NavGraph {
  nodes: NavNode[];
  links: NavLink[];
}
