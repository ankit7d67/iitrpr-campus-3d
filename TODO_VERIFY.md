# TODO_VERIFY

Every guessed or placeholder value must be listed here and in the README ("Values to verify").

## Buildings / floors / colours / heights / roofs

- Floor counts per building: guessed from category defaults. File: `data-src/facade_sheet.csv`.
- Wall / roof / trim colours: category defaults. File: `data-src/facade_sheet.csv`.
- Roof types (flat / parapet / sloped): guessed. File: `data-src/facade_sheet.csv`.
- Building heights: floors * 3.5 m (+ plinth). File: `blender/scripts/import_osm.py`.
- Building names / aliases / categories: partially from OSM, some manual curation pending.
- Room numbers: not inventoried yet (empty in `public/data/campus.json`).

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

- The Nominatim boundary polygon measures **1.411 km² = 349 acres**, centroid
  **30.9669622 N, 76.4731524 E**, against the ~501–525 acres the institute states.
  The polygon may omit campus parcels (e.g. the hostel area), which would explain the
  54 fetched buildings that fall outside it. Verify against the campus
  `landuse=university` / `amenity=university` boundary in OSM before trusting the inside/outside split.
- The 57 in-boundary buildings include `building=apartments` (13), `residential` (12),
  `industrial` (2), `retail` (1) — likely town/adjacent parcels inside the polygon. Verify
  which of these actually belong to IIT Ropar before naming or styling them.


## Institute usage

- The institute must be consulted before using the IIT Ropar name or logo publicly.
