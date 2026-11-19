import manifest from '../../public/models/manifest.json';

/** Prefix for everything in public/ (set when deploying under a GitHub Pages subpath). */
export const BASE = process.env.NEXT_PUBLIC_BASE_PATH ?? '';

export const asset = (path: string) => BASE + path;

/** Content-hashed URLs: ?v=<hash> busts GitHub Pages caches only when a file changes. */
export const CAMPUS_GLB = asset(`/models/campus.glb?v=${manifest['models/campus.glb']}`);
export const CAMPUS_JSON = asset(`/data/campus.json?v=${manifest['data/campus.json']}`);
export const NAV_JSON = asset(`/data/nav.json?v=${manifest['data/nav.json']}`);
export const SCATTER_JSON = asset(`/data/scatter.json?v=${manifest['data/scatter.json']}`);
