# PLAN — iitrpr-campus-3d

## Goal

Interactive 3D web map of the Indian Institute of Technology Ropar (IIT Ropar) campus, Rupnagar, Punjab, India.

## Pipeline diagram

```
OpenStreetMap (Nominatim + Overpass) ──► data-src/*.geojson, data-src/campus_bbox.json
        │
        ▼
Blender 4.2 headless (import_osm.py + dem) ──► procedural low-poly + baked lighting
        │                                        │
        ▼                                        ▼
  bake.py (AO + sun shadow)            public/models/campus.glb (Meshopt + WebP)
        │                                        │
        ▼                                        ▼
  public/data/nav.json, scatter.json ──► Next.js static export (React Three Fiber)
                                              │
                                              ▼
                                    GitHub Pages deploy
```

## Folder structure

```
iitrpr-campus-3d/
├── AGENTS.md
├── CLAUDE.md
├── PLAN.md
├── Makefile
├── README.md
├── NOTICE.md
├── TODO_VERIFY.md
├── data-src/            # OSM extracts, bbox, DEM, placeholder footprints, extra footprints
├── blender/
│   ├── scripts/
│   │   ├── import_osm.py
│   │   └── bake.py
│   └── README.md
├── scripts/             # python helpers: osm download, bbox, checks, facade table
├── public/
│   ├── data/campus.json
│   ├── data/nav.json
│   ├── data/scatter.json
│   └── models/campus.glb
├── src/
│   ├── app/             # Next.js App Router pages
│   ├── components/      # R3F scene, info panel, search, route, tour, sun, ui
│   ├── lib/             # schema.ts (Zod), search, astar, sun, directions, store
│   └── data/            # static copies of campus.json etc.
├── tests/               # vitest unit + playwright e2e
├── e2e/                  # playwright specs
├── .github/workflows/deploy.yml
└── next.config.mjs
```

## Phase checklist

- [x] Phase 1 — Environment
- [x] Phase 2 — Map data (fixed: boundary filter + audit)
- [x] Phase 3 — Building table and data (54 buildings: 57 in-boundary minus 3 contained duplicates)
- [ ] Phase 4 — Blender model (Blender 4.2.16 LTS installed at `C:\Program Files\Blender Foundation\Blender 4.2\blender.exe`, exposed as `$(BLENDER)`; DONE — asset pipeline green, `make preview` rendering; visual QA pending)
- [x] Phase 5 — Web app
- [x] Phase 6 — Tests and deployment (partial: make verify blocked on Phase 4 assets)

### Phase 2 fix log

- Bbox sanity check: S/N/W/E = 30.9590354 / 30.9720737 / 76.4597510 / 76.4814233;
  centre 30.9655546 N, 76.4705872 E, 0.55 km from the 30.9704 / 76.4691 anchor;
  1.45 km (N-S) × 1.84 km (E-W); 2.67 km² ≈ 661 acres. Within the 3 km / 1 km limits,
  so the Nominatim boundary was kept (bbox is a superset of the ~501–525 acre campus).
- Boundary filter: building polygons in `osm_campus.geojson` were stored as `[lat, lon]`
  while the Nominatim polygon is GeoJSON `[lon, lat]`; containment tests now convert
  before intersecting. 57 of 111 fetched buildings fall inside the boundary.
- `scripts/osm_audit.py` writes `OSM_AUDIT.md` + `build/osm_audit.html` (bbox stats,
  named vs unnamed, outside-boundary list, overlaps ≥20% of smaller footprint, ranked
  correction list) and is wired into `make osm` (fetch → audit → facade table).
- `scripts/facade_table.py` now skips out-of-boundary buildings, so `data-src/facade_sheet.csv`
  and `public/data/campus.json` contain only the 57 in-boundary buildings; the web app
  reads only `public/data/campus.json`, so it inherits the filter.

### Audit review follow-ups

- Contained footprints (≥95% of the smaller footprint) are never extruded twice: the named
  footprint wins, otherwise the larger. Kept: M2 Lecture Hall, Nalanda library, S Ramanujan
  building. Skipped and logged in `build/dedupe.json` + `TODO_VERIFY.md`: `1039160851`,
  `1349163384`, `1349164576` (all unnamed). `campus.json` / `facade_sheet.csv` now hold 54
  buildings (57 in-boundary − 3 duplicates).
- Boundary polygon (Nominatim): **1.580 km² = 390 acres**, centroid
  **30.9669622 N, 76.4731524 E**, i.e. below the institute's stated ~501–525 acres. Flagged in
  `TODO_VERIFY.md`; the outside/inside split depends on this polygon.
- `fetch_osm.py` now keeps `building`, `building:levels`, `height`, `amenity` tags, so the audit
  can report metadata coverage (inside: 1 with `building:levels`, 49 with `height`, 57 with a
  `building` type, 0 with `amenity`; types apartments=13, residential=12, yes=22, university=3,
  industrial=2, garage=2, house=1, retail=1, roof=1).
- `osm_audit.py` ranking is now inside-only (all unnamed inside buildings by footprint, then the
  overlap pairs), adds a "Large unnamed inside buildings" top-10 with
  `https://www.openstreetmap.org/way/<id>` links, and moves outside buildings to a separate,
  unranked section.

### Phase 4 pre-flight (found while wiring assets; since fixed)

- `blender/scripts/import_osm.py` used to iterate every GeoJSON feature (roads/footpaths too)
  and look up `facade[str(osm_id)]` while `facade_sheet.csv` keys rows by `BLDG_<osm_id>`. Both
  were fixed in the rewrite (iterate facade rows, look up geometry by `osm_way`).

### Phase 4 status (2026-11-19)

- `make blend` builds `build/campus.blend`: 54 buildings extruded from the facade sheet,
  80 road ribbons inside the boundary buffer. Saved OK.
- `make assets` exports `public/models/campus.glb` (255,092 bytes, 56 meshes, 3,790 triangles,
  4 materials, 0 textures) and regenerates `public/data/nav.json` (626 nodes incl. 54 BLDG_*,
  666 links) + `public/data/scatter.json` (250 trees) via `scripts/build_nav.py`.
- `make check`: CHECK_OK — size 0.26 MB, triangles 3,790, materials 4, textures 0, buildings 54;
  GLB/campus.json/nav.json ID parity OK; scatter non-empty.
- `make preview`: 3 renders into `build/preview/{main,aerial,close}.png` (EEVEE Next headless OK).
  Image stats (PIL) show real content (std 12–16, ~800–1100 colours) after fixing the camera
  clip plane. Visual inspection still pending (no vision-capable model attached).
- `make verify` ends with **"ALL GREEN"** (check + test + build).
- `make e2e`: 12/12 passed (chromium + pixel7): GLB served 200 (`model/gltf-binary`), canvas
  renders, deep links (`?b=BLDG_1349163385`, `?from=&to=`), live search + Enter selection, tour.
- Fixed along the way: `RouteRenderer` route line height was wrong (`y = north`, now `y = 0.6`),
  `CampusScene` camera had default `near/far` limits and an unreachable starting position,
  `playwright.config.ts` now auto-starts the dev server via `webServer`.

### Phase 4b — Item 1: asset tracking + CI (done)

- Removed from `.gitignore` the rules that ignored `public/models/campus.glb`, `public/data/nav.json`,
  `public/data/scatter.json` (and the whole `public/models/` dir pattern). Assets are now tracked;
  `git ls-files public/models public/data` lists all four data files.
- Committed asset-tracking fix.
- Confirmed `make verify` on CI needs no Blender and no extra Python packages (check_budget.py is
  stdlib-only; vitest + next build cover the rest). Workflow unchanged.

## Risks

- DEM download (no auth-free source yet; fallback: flat ground behind a Makefile flag).
- OSM coverage gaps for IIT Ropar (missing buildings / wrongly placed roads).
- License compliance (ODbL attribution, no scraped satellite imagery).
- Performance budget on phones (150k triangles in view, 5 MB model, ≤2 textures; baked shadows
  deferred — runtime sun shadows instead of baked shadow map).
- Visual QA of the preview PNGs (cannot be done in this environment; needs a vision-capable model).
