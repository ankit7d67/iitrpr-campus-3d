// Phase 7 item 7-13: compress the raw Blender GLB without changing its topology
// or node names. Meshopt + 16-bit quantised positions keep every BLDG_* mesh
// individually clickable; WebP shrinks the two baked textures. See
// scripts/check_budget.py for the strict post-compression assertions.
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = process.cwd();
const RAW = path.join(ROOT, 'build', 'raw_campus.glb');
const OPT = path.join(ROOT, 'build', 'opt_campus.glb');
const OUT = path.join(ROOT, 'public', 'models', 'campus.glb');

if (!fs.existsSync(RAW)) {
  console.error(`missing ${RAW}; run \`make assets\` (Blender writes the raw GLB there)`);
  process.exit(1);
}

function gt(args) {
  const cmd = process.platform === 'win32' ? 'npx.cmd' : 'npx';
  const res = spawnSync(cmd, ['--no-install', 'gltf-transform', ...args], {
    cwd: ROOT,
    encoding: 'utf8',
    shell: process.platform === 'win32',
    maxBuffer: 16 * 1024 * 1024,
  });
  if (res.status !== 0) {
    throw new Error(`gltf-transform ${args.join(' ')} failed:\n${res.stdout ?? ''}\n${res.stderr ?? ''}`);
  }
  return (res.stdout ?? '').trim();
}

// Never join/flatten/instance/simplify: 54 separately named BLDG nodes are the
// basis of both parity checks and click-to-select (7-11).
gt([
  'optimize', RAW, OPT,
  '--compress', 'false',
  '--texture-compress', 'webp',
  '--texture-size', '2048',
  '--join', 'false',
  '--flatten', 'false',
  '--instance', 'false',
  '--simplify', 'false',
  '--palette', 'false',
  '--prune-attributes', 'false',
]);
// 16-bit positions: the default 14-bit quantisation rounds the ~600 m campus
// coordinates to ~3.5 cm, which would flatten small facade offsets into
// z-fighting. 16 bits keeps each vertex within ~1 cm.
gt(['meshopt', OPT, OUT, '--quantize-position', '16']);

// Validate before Meshopt: the glTF validator does not understand
// EXT_meshopt_compression. check_budget.py asserts the extension separately.
const validation = gt(['validate', OPT]);
const rawSize = fs.statSync(RAW).size;
const finalSize = fs.statSync(OUT).size;
console.log(`COMPRESS_OK raw=${(rawSize / 1e6).toFixed(2)} MB final=${(finalSize / 1e6).toFixed(2)} MB`);
if (validation) console.log(validation);
