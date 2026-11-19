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
- `make assets` exports `public/models/campus.glb` (now 421,980 bytes, 110 objects incl. 54
  `ENTR_` entrance markers + 4,222 triangles, 4 materials, 0 textures) and regenerates
  `public/data/nav.json` (626 nodes incl. 54 `ENTR_*` entrances, 666 links) + `public/data/scatter.json`
  (250 trees) via `scripts/build_nav.py`.
- `make check`: CHECK_OK — size 0.42 MB, triangles 4,222, materials 4, textures 0, buildings 54;
  GLB BLDG buildings ↔ campus.json OK; GLB `ENTR_*` ↔ nav `ENTR_*` OK; scatter non-empty.
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

### Phase 4b — Item 2: trees (done)

- `src/components/CampusScene.tsx`: InstancedMesh (Cones, 250 instances from `public/data/scatter.json`)
  via dummy Object3D matrices; `frustumCulled={false}`; trees only rendered when GLB on.
- `make verify` ALL GREEN; `make e2e` 12/12 passed; no budget change (GLB untouched; tree cost in scene).

### Phase 4b — Item 3: windows + night mode (done)

- `blender/scripts/import_osm.py` + `blender/scripts/bake.py`: procedural window rows on `MAT_wall`
  via Wave Texture bands + ColourRamp (cheaper than texture, no new material, no new geometry).
- Night mode: `src/lib/store.ts` (+`night`/`setNight`), `src/components/SunPanel.tsx` (toggle button),
  `src/components/CampusScene.tsx` (`applyNight` via GLTF group ref setting Principled emission).
- Budgets kept: GLB materials 4, textures 0, triangles 3,790, buildings 54.

### Phase 4b — Item 4: ENTR_ entrances (done)

- `blender/scripts/import_osm.py`: per building creates `ENTR_<osm_id>` octahedron entrance
  marker at the nearest road/footpath point (outward offset).
- GLB grew to 110 objects / 4,222 triangles / 4 materials / 0 textures (0.30 MB).
- `scripts/build_nav.py`: nav building nodes renamed to `ENTR_<osm_id>` (entrance nodes).
- `scripts/check_budget.py`: parity now checks GLB BLDG buildings ↔ campus.json, and GLB ENTR ↔ nav ENTR.
- `src/components/RouteRenderer.tsx`: deep-link route endpoints (BLDG_*) are mapped to ENTR_*.
- `make verify` ALL GREEN; `make e2e` 12/12 passed.

### Phase 4b — Item 5: baked AO (done)

- `blender/scripts/bake.py`: `bake_ao()` writes a per-vertex `BYTE_COLOR` attribute named
  `AO` onto every `BLDG_` mesh (vertical AO gradient: ~0.55 at plinth base → ~1.0 at roof top).
  `build_wall_material()` now wires window rows (Wave bands + MixRGB) multiplied by the `AO`
  attribute (Attribute node → MixRGB MULTIPLY → Principled Base Color).
- Validated via headless Blender probe: BYTE_COLOR write + node chain both OK on 4.2.16.
- GLB re-export: `COLOR_0`/`COLOR_1` attributes present; materials 4, textures 0, tris 4,222,
  size 0.42 MB. `make check` CHECK_OK.
- Ground-shadow baking intentionally NOT done (separate deferred item; runtime sun shadows cover it).

## Risks

- DEM download (no auth-free source yet; fallback: flat ground behind a Makefile flag).
- OSM coverage gaps for IIT Ropar (missing buildings / wrongly placed roads).
- License compliance (ODbL attribution, no scraped satellite imagery).
- Performance budget on phones (150k triangles in view, 5 MB model, ≤2 textures; baked shadows
  deferred — runtime sun shadows instead of baked shadow map).
- Visual QA of the preview PNGs (cannot be done in this environment; needs a vision-capable model).
