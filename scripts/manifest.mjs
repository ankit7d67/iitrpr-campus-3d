// Phase 7 item 7-15: short content hashes for static assets. GitHub Pages cannot
// set cache headers, so the app appends ?v=<hash> to these URLs; a rebuild that
// changes a file gets a fresh URL, an unchanged one stays cached.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const ROOT = process.cwd();
const FILES = [
  'public/models/campus.glb',
  'public/data/campus.json',
  'public/data/nav.json',
  'public/data/scatter.json',
];
const out = {};
for (const file of FILES) {
  const full = path.join(ROOT, file);
  if (!fs.existsSync(full)) throw new Error(`missing ${file}; run \`make assets\` first`);
  out[file.slice('public/'.length)] = crypto
    .createHash('sha256')
    .update(fs.readFileSync(full))
    .digest('hex')
    .slice(0, 10);
}
const target = path.join(ROOT, 'public', 'models', 'manifest.json');
fs.writeFileSync(target, `${JSON.stringify(out, null, 2)}\n`);
console.log('MANIFEST_OK', JSON.stringify(out));
