#!/usr/bin/env python
"""Build the facade sheet (data-src/facade_sheet.csv) and campus.json (public/data/campus.json).

Phase 3: one row per place. Floors/colours/roof types come from category defaults and are
marked verified=false; nothing is invented as fact.

Only buildings inside the campus boundary are emitted. Fully contained footprints are
treated as duplicates/parts of the containing building and are therefore not extruded
(see build/dedupe.json and TODO_VERIFY.md).
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

# Pair whose intersection covers at least this share of the smaller footprint is treated as
# "contained" (duplicate or building part), not as two separate buildings.
CONTAINED_SHARE = 0.95


def category_for(name: str) -> str:
    n = (name or "").lower()
    if any(k in n for k in ("hostel", "dorm", "ganga", "ashoka", "vishnu", "lakshmibai")): return "hostel"
    if any(k in n for k in ("library", "lab", "institute", "department", "block", "academic", "lecture", "hall")): return "academic"
    if any(k in n for k in ("gym", "sports", "stadium", "track")): return "sports"
    if any(k in n for k in ("canteen", "mess", "food", "kitchen", "bhavan")): return "food"
    if any(k in n for k in ("hospital", "medical", "health")): return "medical"
    if any(k in n for k in ("gate", "entry", "portal")): return "gate"
    return "other"


def to_lonlat(geom: dict) -> dict:
    """Convert a stored [lat, lon] geometry to GeoJSON [lon, lat]."""
    if geom.get("type") == "Polygon":
        return {"type": "Polygon", "coordinates": [[[c[1], c[0]] for c in ring] for ring in geom["coordinates"]]}
    if geom.get("type") == "LineString":
        return {"type": "LineString", "coordinates": [[c[1], c[0]] for c in geom["coordinates"]]}
    return geom


def footprint_area_m2(geom) -> float:
    # ~31 N: 1 deg lat = 110.9 km, 1 deg lon = 95.5 km. Only used to rank footprints.
    return geom.area * 110_900.0 * 95_500.0


def main() -> int:
    osm = json.load(open("data-src/osm_campus.geojson"))
    bbox = json.load(open("data-src/campus_bbox.json"))
    boundary = shape(bbox.get("polygon") or {
        "type": "Polygon",
        "coordinates": [[[float(bbox["west"]), float(bbox["south"])], [float(bbox["west"]), float(bbox["north"])],
                         [float(bbox["east"]), float(bbox["north"])], [float(bbox["east"]), float(bbox["south"])],
                         [float(bbox["west"]), float(bbox["south"])]]],
    })

    candidates: list[dict[str, Any]] = []
    for f in osm.get("features", []):
        p = f.get("properties") or {}
        if p.get("layer") != "building":
            continue
        raw = f.get("geometry") or {}
        if raw.get("type") != "Polygon":
            continue
        geom = shape(to_lonlat(raw))
        if not geom.is_valid or geom.is_empty or not geom.intersects(boundary):
            continue
        osm_id = p.get("osm_id")
        candidates.append({
            "osm_id": osm_id,
            "name": p.get("name"),
            "geom": geom,
            "area": footprint_area_m2(geom),
            "raw": raw,
        })

    # Keep the named footprint when two footprints are (near-)identical; otherwise the larger.
    candidates.sort(key=lambda c: (1 if (c["name"] or "").strip() else 0, c["area"]), reverse=True)
    kept: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for c in candidates:
        duplicate_of = None
        for k in kept:
            if not k["geom"].intersects(c["geom"]):
                continue
            inter = k["geom"].intersection(c["geom"]).area
            smaller = min(k["geom"].area, c["geom"].area)
            if smaller > 0 and inter / smaller >= CONTAINED_SHARE:
                duplicate_of = k
                break
        if duplicate_of is None:
            kept.append(c)
        else:
            dropped.append({
                "osm_id": c["osm_id"],
                "name": c["name"],
                "kept_osm_id": duplicate_of["osm_id"],
                "kept_name": duplicate_of["name"],
            })

    kept.sort(key=lambda c: int(c["osm_id"]))

    buildings = []
    for c in kept:
        osm_id = c["osm_id"]
        name = c["name"] or f"Building_{osm_id}"
        cat = category_for(name)
        d = DEFAULTS[cat]
        ring = c["raw"]["coordinates"][0]
        lat = sum(pt[0] for pt in ring) / len(ring)
        lon = sum(pt[1] for pt in ring) / len(ring)
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

    # Hand-maintained overlay: building overrides, orientation tours and landmark shortcuts.
    # Every referenced id must name a building that survived the boundary/dedupe filter,
    # else regeneration fails.
    extra_path = "data-src/campus_extra.json"
    extra: dict[str, Any] = {}
    if os.path.exists(extra_path):
        with open(extra_path) as f:
            extra = json.load(f)
    known_ids = {b["id"] for b in buildings}
    override_keys = {"name", "aliases", "floors", "hours", "rooms", "verified"}
    for bid, patch in (extra.get("building_overrides") or {}).items():
        if bid not in known_ids:
            raise SystemExit(f"FAIL: campus_extra.json building_overrides id {bid!r} is not a campus building")
        unknown = set(patch) - override_keys
        if unknown:
            raise SystemExit(f"FAIL: campus_extra.json override for {bid!r} has disallowed keys: {sorted(unknown)}")
        for b in buildings:
            if b["id"] == bid:
                b.update(patch)
                break
    tours: list[dict[str, Any]] = extra.get("tours") or []
    landmarks: list[dict[str, Any]] = extra.get("landmarks") or []
    seen_tour_ids: set[str] = set()
    for t in tours:
        tid = t.get("id") or ""
        if not tid or tid in seen_tour_ids:
            raise SystemExit(f"FAIL: campus_extra.json tour id missing/duplicate: {tid!r}")
        seen_tour_ids.add(tid)
        stops = t.get("stops") or []
        if not stops:
            raise SystemExit(f"FAIL: campus_extra.json tour {tid!r} has no stops")
        for s in stops:
            if s.get("bid") not in known_ids:
                raise SystemExit(f"FAIL: campus_extra.json tour {tid!r} stop bid {s.get('bid')!r} is not a campus building")
    seen_landmark_ids: set[str] = set()
    for l in landmarks:
        lid = l.get("id") or ""
        if not lid or lid in seen_landmark_ids:
            raise SystemExit(f"FAIL: campus_extra.json landmark id missing/duplicate: {lid!r}")
        seen_landmark_ids.add(lid)
        if l.get("bid") not in known_ids:
            raise SystemExit(f"FAIL: campus_extra.json landmark {lid!r} bid {l.get('bid')!r} is not a campus building")

    os.makedirs("public/data", exist_ok=True)
    campus = {
        "name": "IIT Ropar",
        "official_name": "Indian Institute of Technology Ropar",
        "country": "India",
        "polygon": {"type": "Polygon", "coordinates": []},
        "bbox": {
            "south": float(bbox.get("boundingbox", ["30.9", "31.1", "77.2", "77.5"])[0]),
            "north": float(bbox.get("boundingbox", ["30.9", "31.1", "77.2", "77.5"])[1]),
            "west": float(bbox.get("boundingbox", ["30.9", "31.1", "77.2", "77.5"])[2]),
            "east": float(bbox.get("boundingbox", ["30.9", "31.1", "77.2", "77.5"])[3]),
        },
        "buildings": buildings,
        "tours": tours,
        "landmarks": landmarks,
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

    os.makedirs("build", exist_ok=True)
    with open("build/dedupe.json", "w") as f:
        json.dump({"contained_share": CONTAINED_SHARE, "dropped": dropped}, f, indent=2)

    print(f"facade rows: {len(buildings)}  dropped contained footprints: {len(dropped)}  tours: {len(tours)} ({sum(len(t.get('stops') or []) for t in tours)} stops)  landmarks: {len(landmarks)}")
    for d in dropped:
        print(f"  dropped osm_id={d['osm_id']} name={d['name'] or '(unnamed)'} -> part of osm_id={d['kept_osm_id']} ({d['kept_name'] or 'unnamed'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
