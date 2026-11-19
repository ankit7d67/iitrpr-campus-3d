"""Clip road/footpath LineStrings to the campus polygon + 100 m margin.

Runs in the system Python (shapely), because Blender's bundled Python has no
shapely -- same pattern as scripts/dem_grid.py. import_osm.py prefers the output
(build/roads_clip.geojson) over the raw OSM features and falls back to the old
bbox-only selection if it is missing.

Coordinates: osm_campus.geojson stores [lat, lon] pairs, campus_bbox.json stores
[lon, lat] (see PLAN.md), so both are converted explicitly. The 100 m buffer is
built in local metres (same local_scale as import_osm.project) and mapped back
to lat/lon, so it means100 m on the ground.
"""

import json
import math
import os

from shapely.geometry import LineString, Polygon, shape

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MARGIN_M = 100.0


def local_scale(lat: float) -> tuple[float, float]:
    """Metres per degree (lat, lon) -- must match blender/scripts/import_osm.py."""
    phi = math.radians(lat)
    m_lat = 111132.92 - 559.82 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi)
    return m_lat, m_lon


def main() -> int:
    bbox = json.load(open(os.path.join(ROOT, "data-src", "campus_bbox.json")))
    south, north, west, east = (float(x) for x in bbox["boundingbox"][:4])
    lat0, lon0 = (south + north) / 2.0, (west + east) / 2.0
    m_lat, m_lon = local_scale(lat0)

    def to_m(lon: float, lat: float) -> tuple[float, float]:
        return (lon - lon0) * m_lon, (lat - lat0) * m_lat

    def to_ll(x: float, y: float) -> tuple[float, float]:
        return lon0 + x / m_lon, lat0 + y / m_lat

    # Campus polygon ([lon, lat] in the file) -> metres -> 100 m buffer -> back to lat/lon.
    poly_m = Polygon([to_m(lon, lat) for lon, lat in bbox["polygon"]["coordinates"][0]])
    buf_m = poly_m.buffer(MARGIN_M)
    buf_ll = Polygon([to_ll(x, y) for x, y in buf_m.exterior.coords])

    src = json.load(open(os.path.join(ROOT, "data-src", "osm_campus.geojson")))
    out_feats = []
    kept = dropped = parts_n = 0
    for f in src.get("features", []):
        p = f.get("properties") or {}
        if p.get("layer") not in ("road", "footpath"):
            continue
        geom = f.get("geometry") or {}
        if geom.get("type") != "LineString":
            continue
        coords = geom.get("coordinates") or []
        if len(coords) < 2:
            continue
        # [lat, lon] pairs -> shapely (lon, lat)
        ls = LineString([(c[1], c[0]) for c in coords])
        if not ls.intersects(buf_ll):
            dropped += 1
            continue
        inter = ls.intersection(buf_ll)
        if inter.is_empty:
            dropped += 1
            continue
        part_geoms = [g for g in getattr(inter, "geoms", [inter])
                      if g.geom_type == "LineString" and len(g.coords) >= 2]
        if not part_geoms:
            dropped += 1  # only touched the margin at a point
            continue
        kept += 1
        for g in part_geoms:
            parts_n += 1
            out_feats.append({
                "type": "Feature",
                "properties": p,
                # back to [lat, lon] to match osm_campus.geojson
                "geometry": {"type": "LineString",
                             "coordinates": [[lat, lon] for lon, lat in g.coords]},
            })

    out_path = os.path.join(ROOT, "build", "roads_clip.geojson")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({"type": "FeatureCollection", "features": out_feats}, f)
    print(f"CLIP_OK kept={kept} dropped={dropped} parts={parts_n} "
          f"margin={MARGIN_M:.0f}m -> build/roads_clip.geojson")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
