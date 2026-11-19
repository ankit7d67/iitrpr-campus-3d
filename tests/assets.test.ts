import { createHash } from 'node:crypto';
import fs from 'node:fs';
import { describe, expect, it } from 'vitest';
import { asset, BASE } from '../src/lib/assets';

// 7-16: the manifest is imported at build time, so a stale committed hash would
// silently ship wrong cache-busting URLs. Verify it against the files on disk.
const manifest = JSON.parse(
  fs.readFileSync('public/models/manifest.json', 'utf8'),
) as Record<string, string>;

describe('asset manifest (7-15)', () => {
  it('has an entry for every hashed asset', () => {
    expect(Object.keys(manifest).sort()).toEqual([
      'data/campus.json',
      'data/nav.json',
      'data/scatter.json',
      'models/campus.glb',
    ]);
  });

  it.each(Object.entries(manifest))('hash for %s matches the file', (file, hash) => {
    expect(hash).toMatch(/^[0-9a-f]{10}$/);
    const raw = fs.readFileSync(`public/${file}`);
    // Match scripts/manifest.mjs: JSON hashes are computed from LF text so the
    // same manifest is valid on Windows (CRLF checkout) and Linux (LF checkout).
    const bytes = file.endsWith('.json')
      ? Buffer.from(raw.toString('utf8').replace(/\r\n/g, '\n'))
      : raw;
    const actual = createHash('sha256').update(bytes).digest('hex').slice(0, 10);
    expect(actual).toBe(hash);
  });

  it('prefixes public URLs with the configured base path', () => {
    expect(BASE).toBe('');
    expect(asset('/og.jpg')).toBe('/og.jpg');
  });
});
