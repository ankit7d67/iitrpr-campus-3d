# TODO_VERIFY

Every guessed or placeholder value must be listed here and in the README ("Values to verify").

## Buildings / floors / colours / heights / roofs

- Floor counts per building: guessed from category defaults. File: `data-src/facade_sheet.csv`.
- Wall / roof / trim colours: category defaults. File: `data-src/facade_sheet.csv`.
- Roof types (flat / parapet / sloped): guessed. File: `data-src/facade_sheet.csv`.
- Building heights: floors * 3.5 m (+ plinth). File: `blender/scripts/import_osm.py`.
- Building names / aliases / categories: partially from OSM, some manual curation pending.
- Room numbers: not inventoried yet (empty in `public/data/campus.json`).

## Tour / landmark copy (editorial)

- The orientation tour title and stop notes, and the landmark labels, live in the hand
  maintained overlay `data-src/campus_extra.json`; the phrasing is editorial (written
  for the UI), **not** sourced from the institute — verify before treating as official.
- `building_overrides` in the same file renames OSM's "M2 Lecture Hall" to "Lecture Hall"
  (the OSM name is kept as an alias) — carried over from an earlier manual edit of
  `public/data/campus.json`, now source-controlled so `make osm` cannot lose it.

## Terrain (DEM)

- Copernicus GLO-30 (AWS open bucket `copernicus-dem-30m`, tile N30/E076) is processed by
  `scripts/dem_grid.py` with a **5×5 median despeckle**: the raw tile has raster-aligned
  artifacts on the campus (a 2-row-wide, full-tile-width band at rows 23–24 worth +2..+7 m
  with 15% one-pixel edges, plus isolated +5 m pixels; raw max 273.8 m → 267.4 m after).
  Whether that band is a real embankment/canal or a DEM stitching artifact was **not**
  verified against imagery — check before trusting absolute heights near lat 30.9655.
- Absolute elevations (~262–267 m) come from the DEM and are plausible for the Sutlej plain
  but were not surveyed; verify against a topographic map if exact heights matter.

## Scatter props (trees / street lamps)

- The 250 trees and 80 street lamps in `public/data/scatter.json` are **synthetic
  decorations**, not objects mapped in OSM. They are placed deterministically along
  OSM road centrelines by `scripts/build_nav.py` (trees 35 m spacing / 6.5 m offset,
  lamps 90 m spacing / 4.5 m offset on the opposite side). Their exact positions,
  count and appearance are unverified against the real campus — do not treat them as
  an inventory of actual street furniture.

## Baked lighting (7-9)

- The baked ground shadow in `blender/textures/ground_bake.png` is rasterised for
  one **fixed** sun position (15 Jun, 10:30 IST, elevation 63.6°, azimuth 99.9°).
  It is a static contact cue, not a time-accurate shadow: the app's SunPanel can
  move the sun, and the runtime directional shadow follows it, while the baked
  shadow stays put. Verify the result in daylight and at night before treating
  it as a faithful lighting model.
- The window emissive atlas (`window_emissive.png`) is a repeating decorative
  pattern, not the real window layout of any building.

## Placeholders

- Missing OSM footprints (buildings/roads) go to `data-src/extra_footprints.geojson` with
  `confidence: "low"` and must be verified against satellite imagery.

## OSM duplicates / building parts (not extruded)

These footprints are ≥95% contained in another footprint, so only the containing building is
extruded. The contained footprint is skipped in `public/data/campus.json` and
`data-src/facade_sheet.csv` (see `build/dedupe.json`) — possible duplicate or building part,
verify in OSM:

- `osm_id=1039160851` (unnamed) contained in **M2 Lecture Hall** (`osm_id=1032552691`)
- `osm_id=1349163384` (unnamed) contained in **Nalanda library** (`osm_id=1349163385`)
- `osm_id=1349164576` (unnamed) contained in **S Ramanujan building** (`osm_id=1349164577`)

No names were invented for either footprint.

## Campus boundary

- The Nominatim boundary polygon measures **1.580 km² = 390 acres**, centroid
  **30.9669622 N, 76.4731524 E**, against the ~501–525 acres the institute states.
  The polygon may omit campus parcels (e.g. the hostel area), which would explain the
  54 fetched buildings that fall outside it. Verify against the campus
  `landuse=university` / `amenity=university` boundary in OSM before trusting the inside/outside split.
- The 57 in-boundary buildings include `building=apartments` (13), `residential` (12),
  `industrial` (2), `retail` (1) — likely town/adjacent parcels inside the polygon. Verify
  which of these actually belong to IIT Ropar before naming or styling them.


## Institute usage

- The institute must be consulted before using the IIT Ropar name or logo publicly.
