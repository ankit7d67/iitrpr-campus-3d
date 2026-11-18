#!/usr/bin/env python
"""Build the facade sheet (data-src/facade_sheet.csv) and campus.json (public/data/campus.json).

Phase 3: one row per place. Floors/colours/roof types come from category defaults and are
marked verified=false; nothing is invented as fact.
"""

from __future__ import annotations

import csv
import json
import os
from typing import Any

from shapely.geometry import shape


DEFAULTS: dict[str, dict[str, Any]] = {
    "academic": {"floors": 3, "roof_type": "flat", "wall_color": "#c9c2b4", "trim_color": "#4a4a4a", "roof_color": "#8a8578", "window_pattern": "grid"},
    "hostel": {"floors": 2, "roof_type": "flat", "wall_color": "#cbb694", "trim_color": "#5b4632", "roof_color": "#7a5c3e", "window_pattern": "grid"},
    "admin": {"floors": 2, "roof_type": "flat", "wall_color": "#c9c2b4", "trim_color": "#4a4a4a", "roof_color": "#8a8578", "window_pattern": "grid"},
    "sports": {"floors": 1, "roof_type": "flat", "wall_color": "#b8b0a0", "trim_color": "#3f3f3f", "roof_color": "#6e675c", "window_pattern": "grid"},
    "food": {"floors": 1, "roof_type": "flat", "wall_color": "#d8cbb8", "trim_color": "#6b5a44", "roof_color": "#93764f", "window_pattern": "grid"},
    "medical": {"floors": 2, "roof_type": "flat", "wall_color": "#c9c2b4", "trim_color": "#4a4a4a", "roof_color": "#8a8578", "window_pattern": "grid"},
    "gate": {"floors": 1, "roof_type": "flat", "wall_color": "#c9c2b4", "trim_color": "#4a4a4a", "roof_color": "#8a8578", "window_pattern": "grid"},
    "other": {"floors": 1, "roof_type": "flat", "wall_color": "#c9c2b4", "trim_color": "#4a4a4a", "roof_color": "#8a8578", "window_pattern": "grid"},
}


def category_for(name: str) -> str:
    n = (name or "").lower()
    if any(k in n for k in ("hostel", "dorm", "ganga", "ashoka", "vishnu", "lakshmibai")): return "hostel"
    if any(k in n for k in ("library", "lab", "institute", "department", "block", "academic")): return "academic"
    if any(k in n for k in ("gym", "sports", "stadium", "track")): return "sports"
    if any(k in n for k in ("canteen", "mess", "food", "kitchen", "bhavan")): return "food"
    if any(k in n for k in ("hospital", "medical", "health")): return "medical"
    if any(k in n for k in ("gate", "entry", "portal")): return "gate"
    return "other"


def main() -> int:
    osm = json.load(open("data-src/osm_campus.geojson"))
    bbox = json.load(open("data-src/campus_bbox.json"))
    boundary = shape(bbox.get("polygon") or {"type": "Polygon", "coordinates": [[[[float(bbox["west"]), float(bbox["south"])], [float(bbox["west"]), float(bbox["north"])], [float(bbox["east"]), float(bbox["north"])], [float(bbox["east"]), float(bbox["south"])], [float(bbox["west"]), float(bbox["south"])]]]]})
    buildings = []
    for f in osm.get("features", []):
        p = f.get("properties") or {}
        if p.get("layer") != "building":
            continue
        geom = f.get("geometry") or {}
        if geom.get("type") == "Polygon":
            geom = {"type": "Polygon", "coordinates": [[[c[1], c[0]] for c in ring] for ring in geom["coordinates"]]}
        inside = False
        try:
            g = shape(geom)
            inside = g.is_valid and not g.is_empty and g.intersects(boundary)
        except Exception:
            inside = False
        if not inside:
            continue
        osm_id = p.get("osm_id")
        name = p.get("name") or f"Building_{osm_id}"
        cat = category_for(name)
        d = DEFAULTS[cat]
        geom = f.get("geometry") or {}
        coords = geom.get("coordinates") or []
        lat = lon = 0.0
        if geom.get("type") == "Polygon" and coords:
            flat = [c[1] for c in coords[0]]
            lat, lon = sum(flat) / len(flat), sum(c[0] for c in coords[0]) / len(coords[0])
        elif geom.get("type") == "LineString" and coords:
            flat = [c[1] for c in coords]
            lat, lon = sum(flat) / len(flat), sum(c[0] for c in coords) / len(coords)
        buildings.append({
            "id": f"BLDG_{osm_id}",
            "osm_way": osm_id,
            "name": name,
            "aliases": [name],
            "category": cat,
            "floors": int(d["floors"]),
            "roof_type": d["roof_type"],
            "wall_color": d["wall_color"],
            "trim_color": d["trim_color"],
            "roof_color": d["roof_color"],
            "window_pattern": d["window_pattern"],
            "verified": False,
            "location": {"lat": float(lat), "lon": float(lon)},
            "rooms": [],
            "hours": "",
        })

    os.makedirs("public/data", exist_ok=True)
    campus = {
        "name": "IIT Ropar",
        "official_name": "Indian Institute of Technology Ropar",
        "country": "India",
        "polygon": {"type": "Polygon", "coordinates": []},
        "bbox": {"south": float(bbox.get("boundingbox", ["30.9", "31.1", "77.2", "77.5"])[0]), "north": float(bbox.get("boundingbox", ["30.9", "31.1", "77.2", "77.5"])[1]), "west": float(bbox.get("boundingbox", ["30.9", "31.1", "77.2", "77.5"])[2]), "east": float(bbox.get("boundingbox", ["30.9", "31.1", "77.2", "77.5"])[3])},
        "buildings": buildings,
    }
    with open("public/data/campus.json", "w") as f:
        json.dump(campus, f, indent=2)

    with open("data-src/facade_sheet.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "osm_way", "name", "category", "floors", "roof_type", "wall_color", "trim_color", "roof_color", "window_pattern", "move_m", "style", "pad_group", "verified"])
        for b in buildings:
            w.writerow([
                b["id"], b["osm_way"], b["name"], b["category"], b["floors"], b["roof_type"],
                b["wall_color"], b["trim_color"], b["roof_color"], b["window_pattern"],
                "", "", "", "false",
            ])

    print(f"facade rows: {len(buildings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
