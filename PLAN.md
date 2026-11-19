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
- [x] Phase 6 — Tests and deployment (`make verify` = **ALL GREEN** locally, e2e 12/12.
  Deploy pending: no git remote yet — branch aligned to `main` to match `deploy.yml`;
  GitHub Pages must be enabled in the repo settings after the first push.)
- [ ] Phase 7 — Feature parity with the reference app (17 items, agreed order; per-item
  protocol = check + verify + e2e → PLAN → commit → report → wait for "approved";
  7-1 done)

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
- `make assets` exports `public/models/campus.glb` (now ~1.40 MB, 110 objects incl. 54
  `ENTR_` entrance markers + 26,654 triangles — terrain ground grid (62.5 m cells) +
  street kerbs + densified road ribbons + level pads/retaining walls included,
  4 materials, 0 textures) and regenerates `public/data/nav.json` (626 nodes incl. 54 `ENTR_*`
  entrances, 666 links) + `public/data/scatter.json` (250 trees) via `scripts/build_nav.py`.
- `make check`: CHECK_OK — size 1.40 MB, triangles 26,654, materials 4, textures 0, buildings 54;
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

### Phase 4b — Item 6: DEM (done)

- Copernicus GLO-30 found on AWS Open Data (no login): bucket `copernicus-dem-30m`
  (registry.opendata.aws/copernicus-dem), COG tiles named
  `Copernicus_DSM_COG_10_<band>/<file>.tif` (10 arcsec = 30 m, 1° tiles).
- Campus tile `Copernicus_DSM_COG_10_N30_00_E076_00_DEM` downloaded (39.75 MB) and cropped to
  the campus bbox → `data-src/dem.tif` (78×47 px, EPSG:4326, **261.7–273.8 m**, mean 263.8 m —
  consistent with the Sutlej plain). `data-src/*.tif` stays gitignored; `make dem` regenerates.
- New `scripts/dem_grid.py` converts the GeoTIFF to `build/dem_grid.json` (Blender's Python has
  no rasterio); `make blend` runs it via the new `dem-grid` target (failure ignored → flat ground).
- `blender/scripts/import_osm.py`: `load_dem_grid`/`dem_sample` (bilinear, edge-clamped) +
  `terrain_z`; ground is now a 40×40 subdivided grid following the DEM inside the bbox (flat
  outside), buildings sit on the local terrain (`base_z`), roads and `ENTR_` markers are
  terrain-offset too. `bake.py` AO gradient now uses the mesh z-range (buildings have base_z).
- Budgets kept: GLB 7,420 tris, 0.52 MB, 4 materials, 0 textures. `make check` CHECK_OK,
  `make verify` ALL GREEN, `make e2e` 12/12.

### Phase 4b — Item 7: kerbs (done)

- `blender/scripts/import_osm.py`: `road_ribbon(..., kerb=True)` adds a kerb (0.15 m face +
  0.35 m lip, both sides) along `tertiary`/`unclassified` streets only; `KERB_H`/`KERB_W`/
  `KERB_HIGHWAYS` constants. Kerbs reuse `MAT_road` (budgets: materials stay 4, textures 0).
- Budgets after kerbs: GLB **8,796 tris**, **0.60 MB**, 4 materials, 0 textures — well inside
  150k tris / 5 MB / 4 materials / 2 textures, so kerbs were allowed.
- `make check` CHECK_OK, `make verify` ALL GREEN, `make e2e` 12/12.

### Phase 4b — Regression fix: roads (done)

Reported: roads broken/dashed and spread far outside the campus after the DEM
commits (fine at `8d828a0`). Three distinct causes found and fixed:

1. **Two different surfaces** — road z was sampled from the raw DEM (bilinear)
   while the ground mesh was a coarse quad grid that Blender re-tessellated, so
   roads intermittently sank below the ground (dashed). Fix: `build_ground` now
   emits **explicit triangles with a known diagonal**, `ground_surface_z()`
   interpolates those *same* triangle planes, roads sit at **+0.1 m**
   (`ROAD_LIFT`), and long segments are densified (`ROAD_SEG_M = 10 m`).
   `GROUND_SEGS` 40 → 80 (62.5 m cells) so creases are gentler.
2. **No horizontal clipping** — `build_roads` kept any OSM way that merely
   touched the bbox and drew its **full geometry** (Overpass returns whole ways;
   road data spans lat 30.87–31.04, lon 76.24–76.63 ≈ 19×16 km). Fix: new
   `scripts/clip_roads.py` (shapely, system Python — Blender has none) clips
   roads/footpaths to the **campus polygon + 100 m** → `build/roads_clip.geojson`
   (73 ways kept, 1652 dropped), wired as the `clip-roads` make target;
   `import_osm.py` prefers it and warns if missing.
3. **`data-src/dem.tif` was mis-georeferenced** (live since item 6) — the first
   crop wrote height/width swapped: bounds read east 76.4728 (should be
   76.4814) / south 30.9504 (should be 30.9590) and pixels were scrambled
   (matched neither the window nor its transpose). Fixed `crop_dem.py` with a
   `CROP_VERIFY` bounds+content assertion; regenerated 47×78, bounds OK.

Also: Copernicus GLO-30 has **raster-aligned artifacts** on the campus — a
2-row-wide, full-tile-width band at rows 23–24 (+2..+7 m, 15% one-pixel edges)
plus isolated +5 m pixels (max 273.8 m). `scripts/dem_grid.py` now applies a
**5×5 median despeckle** (removes 1–2-pixel features only; max now 267.4 m) —
processed-data note, logged here and in TODO_VERIFY.md.

Verification (numerical, no visual QA claimed): new `qa_roads.py` reads the
exported GLB — all **14,600 road verts exactly +0.100 m** above the GROUND
mesh (barycentric on its triangles), all **7,300 ribbon centroids above
ground** (min +0.007 m), max distance of any road vert to the polygon
**102.2 m** (≤ 100 m + ribbon/kerb width). Budgets: 23,094 tris, 1.16 MB,
4 materials, 0 textures. `make check` CHECK_OK, `make verify` ALL GREEN,
e2e **12/12** (`npx playwright test` after killing a stale dev server on :3000
that made `make e2e` fail once — known flake).

### Phase 4b — Item 8: level pads + retaining walls (done)

Previously gated on "a real DEM is in" — now unblocked (items 6 + road regression fix).

- `blender/scripts/import_osm.py`: `build_building(..., ground_z=...)` now computes
  `base_z = max(terrain under the footprint)` on the **same surface the GROUND mesh uses**
  (`ground_surface_z`, i.e. the exact triangle planes — the road-regression lesson applied
  to buildings), so nothing floats or sinks. New `offset_ring()` (CCW bisector offset,
  mitre clamped at 3×, `PAD_OFFSET = 1.5 m`) builds a level-pad annulus around each
  footprint plus retaining-wall quads from the pad edge down (fill) or up (cut, uphill
  side) to grade; wall winding is picked per segment so normals face away from the
  building on both sides. Pads/walls are faces inside the existing `BLDG_` meshes using
  `MAT_wall` — **no new objects, no new materials** (parity and 4-material budget intact).
  Entrance markers now also sit on `ground_surface_z` instead of raw-DEM bilinear.
- Budgets after pads: GLB **26,654 tris**, **1.40 MB**, 4 materials, 0 textures, 110 objects.
- Numerical QA (`qa_pads.py`, GLB-based): 54 BLDG meshes; ring bottoms never below ground
  (worst −0.0000 m); every wall foot exactly on the ground surface (worst 0.0000 m); every
  pad edge closes to grade (0 missing feet) → **PAD_QA PASS**.
- `make check` CHECK_OK, `make verify` ALL GREEN, e2e **12/12**, previews re-rendered.

## Phase 7 — feature parity with the reference app (in progress)

Reference: https://roshanbinoj-iiitk.github.io/iiitk-campus-in-3d/ (source repo
`Kunal-Sarpal/iiitk-campus-in-3d`, public) — same OSM → Blender → glTF → Next.js/R3F
pipeline and the same budgets. Gap analysis produced a 17-item order (7-1 … 7-17);
the per-item protocol is unchanged: `make check` + `make verify` + `make e2e`, numeric
QA, PLAN update, commit, report, stop for approval. User decisions: no push yet; full
parity stack (fuse.js, postprocessing, gltf-transform — no Tailwind/Next16); rooms UI
ships with empty data; analytics included once a GoatCounter account exists.

### 7-1 — Data & schema: tours, landmarks, cross-field validation (done)

- New hand-maintained source overlay `data-src/campus_extra.json`, merged into
  `public/data/campus.json` by `scripts/facade_table.py` whenever `make osm` runs:
  `building_overrides` (allowlisted keys: name/aliases/floors/hours/rooms/verified),
  one orientation `tours[]` entry and 6 `landmarks[]`. The generator fails loudly on
  unknown or duplicate ids, and `make osm` is now lossless for campus.json — the
  regeneration was diff-checked against the previous file (only tours/landmarks added).
  The override also preserves the earlier manual rename of OSM's "M2 Lecture Hall" to
  "Lecture Hall", keeping the OSM name as an alias.
- **Finding:** the tour was previously **empty** — no building carried `tour_stop`, so
  `getTourStops()` returned []. Real data now exists (9 stops); TourPanel switches to
  it in item 7-6 (with the camera work).
- `src/lib/schema.ts`: `roomSchema`, `tourSchema`, `landmarkSchema` plus a
  `superRefine` on `campusSchema` — duplicate building/tour/landmark ids, room floors
  within `0..floors`, every tour-stop and landmark `bid` must name a building.
  `tours`/`landmarks` default to `[]`, so old cached documents still parse.
  Matching hand-written types added to `src/lib/types.ts`.
- `scripts/check_budget.py`: parity extended with tour/landmark id uniqueness and
  `bid` → campus-building references (GLB parity follows transitively through the
  existing BLDG check); `CHECK_OK` now prints `tours`, `tour_stops`, `landmarks`.
- QA: CHECK_OK = 26,654 tris / 1.40 MB / 4 mats / 0 tex / 54 buildings /
  1 tour (9 stops) / 6 landmarks / 626 nav nodes / 666 links. Unit tests 24
  (schema file 5 → 14, including parse of the real document), typecheck clean,
  `make verify` **ALL GREEN**, e2e **12/12**. Blender previews unchanged (no model
  change). Docs updated: README pipeline, AGENTS parity rules, TODO_VERIFY editorial note.

### 7-2 — CameraRig (done, one follow-up)

- `OrbitControls` already ship with `enableDamping` (smooth orbit) and the camera
  is framed at `[1150, 1500, 1750]` → target `[0,0,0]`, `maxDistance=8000`
  (re-aimed in fix (b) after the ground grew).
- **Follow-up:** setting an explicit `damping={0.05}` value is not currently
  possible — `@react-three/drei`'s `OrbitControlsProps` type does not expose the
  `damping` prop (the prop works at runtime, but typecheck/lint blocks it).
  Revisit when the drei types catch up or via a `ref` accessor.

### 7-3 — Search (reviewed, already complete)

- `SearchPanel` (input + max-12 results + Go + no-match hint) over
  `searchBuildings()` (token/name/alias scoring: name×3 + alias×2 + token×0.5)
  in `src/lib/search.ts`, fed by `loadCampus()` (zod-validated).
- Verified end-to-end: unit tests 4/4 (`tests/search.test.ts`) and e2e
  "search finds a building and opens the info panel" green on chromium + pixel7.
  Search → info dialog already navigates the user to the selected building panel.

### 7-4 — Control drawer (done)

- New `src/components/Drawer.tsx`: slide-out left drawer housing the title,
  `SearchPanel` and `QualityControl`; `«` collapses it (Escape also closes),
  `☰` reopens it. State lives in the store (`drawerOpen`, default **open** so
  deep-link/search/tour e2e always find their controls).
- CSS in `globals.css`: 300 px panel matching the panel design tokens,
  `transform/opacity/visibility` transition, `visibility: hidden` when closed
  (so closed content is genuinely hidden from Playwright/AT), inner cards drop
  their chrome inside the drawer, `.dialog-backdrop` bumped to `z-index: 40`
  so modals stay above it, responsive width on ≤640 px.
- QA: `make verify` **ALL GREEN** (check + 24 unit tests + build), e2e
  **16/16** — new test "drawer collapses and reopens with controls" runs on
  chromium + pixel7; fresh `ui-desktop.png` / `ui-phone.png` captured.

### 7-5 — Route planner + turn-by-turn directions (done, 3 latent bugs fixed)

- New `src/lib/route.ts`: `planRoute()` (single source of truth for panel +
  renderer: BLDG→ENTR id mapping, A*, `buildSteps`) and `formatDistance()`.
- `RoutePanel` now plans routes from the UI: From/To `<select>` pickers over the
  building list + Route button, then endpoint names, total distance, step count
  and a scrollable turn-by-turn list; Clear returns to the pickers. Pickers stay
  in sync with deep-link/search-set routes.
- **Bug 1 — A* was directed.** `nav.json` stores each walking edge once, but the
  network is one undirected component (626 nodes); following `from→to` only left
  70 directed components, so most pairs (incl. the e2e deep-link pair) found no
  path and the route line never rendered. Fixed by expanding every link in both
  directions in `astar.ts`.
- **Bug 2 — `<Line>` rendered outside the Canvas.** `RouteRenderer` sat next to
  `<CampusScene />` in `page.tsx`, so drei's `Line` ran without R3F context and
  crashed the app ("Hooks can only be used within the Canvas") the moment a route
  had a path — masked until bug 1 was fixed. Moved inside the Canvas in
  `CampusScene.tsx`.
- **Bug 3 — direction text broken.** `compass()` indexed `dirs[-1]` for negative
  degrees ("undefined"), bearings used `atan2(dx, dz)` with z = −north (N/S
  flipped; verified via corr(lon,x)=+1.0, corr(lat,z)=−1.0), and turns were
  announced on the wrong leg. Rewrote `directions.ts`: negative-safe compass,
  `atan2(dx, −dz)` headings, turns attributed to the leg started after turning
  ("Turn right toward east"), left/right from the signed turn angle.
- QA: `make verify` **ALL GREEN** — unit tests 28 → **34** (route.test 6 incl.
  real-nav.json regressions both directions, astar bidirectional, directions
  cardinal/left-right/no-"undefined"), e2e **18/18** (new "route planner plans a
  route from the pickers" on chromium + pixel7), numeric QA ROAD_QA/PAD_QA/
  DEM_GRID all PASS (model unchanged: 33,724 tris / 1.63 MB / 4 mats). Fresh
  `ui-desktop.png` / `ui-phone.png`.
- Build note: the transient `[Invariant: no direct app page entry found for
  /_not-found]` was traced to orphaned node processes + a stale `.next` (likely
  a leftover `next dev` sharing the build dir); killing node and removing
  `.next` cleared it — do that first if it recurs.

## Fixes

- **(a)** Pad faces + retaining walls → `MAT_ground` via 3rd BLDG material slot (commit `08947bd`): 218 primitives, 4 materials, tris unchanged 26,654. verify + e2e 14/14.
- **(b)** Ground = campus bbox + 150 m (2370.5 × 1745.5 m, 95×70 grid), camera reframed, smooth GROUND normals, `ROAD_LIFT=0.15` + 5 m densify so ROAD_QA passes (commit `0168500`): ROAD_QA PASS (min centroid margin +0.0327 m), PAD_QA PASS (0/0/0), verify ALL GREEN, e2e 14/14, preview OK.
- **(c)** Hide `ENTR_*` entrance marker meshes at runtime via `attachGltf` callback (commit `62fc030`): 54 nodes hidden in web scene only; GLB + nav.json anchors untouched; routing unaffected. verify ALL GREEN, e2e 14/14 w/ fresh screenshots.
- **DEM crop fix** (this batch): Integer outward window `Window(1655,101,79,47)` replaces fractional `from_bounds()` transform, eliminating the 0.54 m east bound shortfall; bbox now fully contained on all 4 sides. `data-src/dem.tif` regenerated, `build/dem_grid.json` updated (cols 79). `make check`/`make verify`/`make e2e` all pass (14/14).
- **Tour notes rewrite** (this batch): 9 non-compliant notes rewritten to data-only wording (name + OSM category only, no functional claims). `scripts/facade_table.py` regenerated `public/data/campus.json`. `make check`/`make verify`/`make e2e` all pass (14/14).

## Risks

- ~~DEM download (no auth-free source yet; fallback: flat ground behind a Makefile flag).~~
  Resolved (item 6): Copernicus GLO-30 on AWS Open Data, no auth needed.
- OSM coverage gaps for IIT Ropar (missing buildings / wrongly placed roads).
- License compliance (ODbL attribution, no scraped satellite imagery).
- Performance budget on phones (150k triangles in view, 5 MB model, ≤2 textures; baked shadows
  deferred — runtime sun shadows instead of baked shadow map).
- Visual QA of the preview PNGs (cannot be done in this environment; needs a vision-capable model).
