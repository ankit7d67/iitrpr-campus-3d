# Blender build scripts

- `import_osm.py` — procedural low-poly campus from OSM GeoJSON + facade sheet + DEM.
- `bake.py` — ambient occlusion into vertex colours + sun shadow into 2048 px ground texture; exports `campus.glb` (Meshopt + WebP), `nav.json`, `scatter.json`.
- `render_preview.py` — renders scene PNGs into `build/preview/`.

Run headless: `blender -b -P blender/scripts/import_osm.py`
