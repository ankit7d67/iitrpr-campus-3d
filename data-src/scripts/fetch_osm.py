#!/usr/bin/env python
"""Fetch OpenStreetMap data for the IIT Ropar campus.

Pipeline: Nominatim (search + polygon + bbox) -> Overpass (buildings, roads, footpaths, boundary)
Outputs:
  - data-src/campus_bbox.json
  - data-src/osm_campus.geojson
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import requests
from shapely.geometry import shape
from shapely.ops import unary_union

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
CAMPUS_QL = "Indian Institute of Technology Ropar"


def nominatim_search(query: str, limit: int = 5) -> list[dict[str, Any]]:
    r = requests.get(
        NOMINATIM_URL,
        params={"q": query, "format": "json", "polygon_geojson": 1, "limit": limit},
        headers={"User-Agent": "iitrpr-campus-3d/0.1 (student project; OSM data ODbL)"},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def overpass_query(lat: float, lon: float, radius: float) -> dict[str, Any]:
    ql = f"""[out:json][timeout:120];
(
  way["building"](around:{radius},{lat},{lon});
  way["highway"](around:{radius},{lat},{lon});
  way["footway"](around:{radius},{lat},{lon});
  relation["place"="university"](around:{radius},{lat},{lon});
);
out geom;
"""
    last_err = None
    for attempt in range(4):
        r = requests.post(
            OVERPASS_URL,
            data={"data": ql},
            headers={"User-Agent": "iitrpr-campus-3d/0.1 (student project; OSM data ODbL)"},
            timeout=180,
        )
        if r.ok:
            return r.json()
        last_err = r
        import time

        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Overpass failed: {last_err}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data-src/osm_campus.geojson")
    parser.add_argument("--bbox-out", default="data-src/campus_bbox.json")
    args = parser.parse_args()

    results = nominatim_search(CAMPUS_QL)
    if not results:
        print("ERROR: no Nominatim result for campus query", file=sys.stderr)
        return 1
    top = results[0]
    print(f"Top result: {top.get('display_name')}")
    print(f"Bounding box: {top.get('boundingbox')}")
    geojson = top.get("geojson") or {}
    polygon = shape(geojson) if geojson.get("type") else None
    if polygon is None:
        print("ERROR: no polygon geometry in Nominatim response", file=sys.stderr)
        return 1

    south, north, west, east = [float(x) for x in top["boundingbox"]]
    anchor = {
        "lat": sum(float(x) for x in top["boundingbox"][:2]) / 2,
        "lon": sum(float(x) for x in top["boundingbox"][2:]) / 2,
    }
    data = overpass_query(anchor["lat"], anchor["lon"], 8000.0)

    buildings = []
    roads = []
    footpaths = []
    boundaries = []

    for el in data.get("elements", []):
        etype = el.get("type")
        if etype == "way":
            geom = None
            if el.get("geometry"):
                coords = [(n["lat"], n["lon"]) for n in el["geometry"]]
                # OpenStreetMap way geometry is ordered lon,lat; convert to lat,lon
                coords = [(c[1], c[0]) for c in coords]
                if len(coords) > 2 and coords[0] == coords[-1]:
                    geom = {"type": "Polygon", "coordinates": [[[c[1], c[0]] for c in coords]]}
                else:
                    geom = {"type": "LineString", "coordinates": [[c[1], c[0]] for c in coords]}
            tags = el.get("tags") or {}
            if "building" in tags:
                if geom and geom.get("type") == "Polygon":
                    buildings.append({"osm_id": el["id"], "name": tags.get("name"), "geometry": geom, "tags": tags})
            elif "footway" in tags or tags.get("highway") == "footway":
                if geom and geom.get("type") == "LineString":
                    footpaths.append({"osm_id": el["id"], "name": tags.get("name"), "geometry": geom, "tags": tags})
            elif tags.get("highway"):
                if geom and geom.get("type") == "LineString":
                    roads.append({"osm_id": el["id"], "name": tags.get("name"), "geometry": geom, "tags": tags, "highway": tags.get("highway")})

    fc = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {
                "osm_id": b["osm_id"],
                "name": b["name"],
                "layer": "building",
                "building": b["tags"].get("building"),
                "levels": b["tags"].get("building:levels"),
                "height": b["tags"].get("height"),
                "amenity": b["tags"].get("amenity"),
            }, "geometry": b["geometry"]}
            for b in buildings
        ] + [
            {"type": "Feature", "properties": {"osm_id": f["osm_id"], "name": f["name"], "layer": "footpath"}, "geometry": f["geometry"]}
            for f in footpaths
        ] + [
            {"type": "Feature", "properties": {"osm_id": r["osm_id"], "name": r.get("name"), "layer": "road", "highway": r.get("highway")}, "geometry": r["geometry"]}
            for r in roads
        ],
    }

    named = sorted({(b["name"] or f"Building_{b['osm_id']}") for b in buildings if b.get("name")})
    print("NAMED_BUILDINGS_TABLE")
    for n in named:
        print(f"  - {n}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(fc, f)
    with open(args.bbox_out, "w") as f:
        json.dump(
            {
                "name": "Indian Institute of Technology Ropar",
                "display_name": top.get("display_name"),
                "boundingbox": top.get("boundingbox"),
                "polygon": geojson,
            },
            f,
        )

    print(f"Buildings: {len(buildings)}  Roads: {len(roads)}  Footpaths: {len(footpaths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
