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

## Institute usage

- The institute must be consulted before using the IIT Ropar name or logo publicly.
