import fs from 'node:fs';
import { describe, expect, it } from 'vitest';

// 7-16: structural GLB assertions that complement scripts/check_budget.py.
// The Python check is the budget authority; this test guards the exact
// compression/topology decisions made in 7-13 from the JS side.
function glbJson(): Record<string, any> {
  const buf = fs.readFileSync('public/models/campus.glb');
  const jsonLength = buf.readUInt32LE(12);
  return JSON.parse(buf.subarray(20, 20 + jsonLength).toString('utf8'));
}

describe('compressed campus GLB (7-13)', () => {
  const j = glbJson();

  it('requires Meshopt, WebP and quantisation extensions', () => {
    expect(j.extensionsRequired).toEqual(
      expect.arrayContaining(['EXT_meshopt_compression', 'EXT_texture_webp', 'KHR_mesh_quantization']),
    );
  });

  it('keeps four materials and two WebP images', () => {
    expect(j.materials).toHaveLength(4);
    expect((j.materials ?? []).map((m: any) => m.name)).toEqual([
      'MAT_ground',
      'MAT_wall',
      'MAT_roof',
      'MAT_road',
    ]);
    expect((j.images ?? []).map((im: any) => im.mimeType)).toEqual(['image/webp', 'image/webp']);
  });

  it('keeps all 110 named meshes and 33,724 triangles', () => {
    expect(j.meshes).toHaveLength(110);
    const accessors = j.accessors ?? [];
    let triangles = 0;
    for (const mesh of j.meshes ?? []) {
      for (const prim of mesh.primitives ?? []) {
        const count = prim.indices !== undefined
          ? accessors[prim.indices].count
          : accessors[prim.attributes?.POSITION ?? 0].count;
        triangles += Math.floor(count / 3);
      }
    }
    expect(triangles).toBe(33_724);
  });

  it('preserves individually clickable BLDG_* nodes', () => {
    const names = (j.nodes ?? []).map((n: any) => n.name ?? '');
    expect(names.filter((n: string) => n.startsWith('BLDG_'))).toHaveLength(54);
    expect(names.filter((n: string) => n.startsWith('ENTR_'))).toHaveLength(54);
  });
});
