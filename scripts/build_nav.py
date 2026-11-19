#!/usr/bin/env python
"""Generate public/data/nav.json (walking graph) and public/data/scatter.json (trees).

Run via `make assets` after the GLB export.

Coordinate convention matches the exported glTF: x = east (m), z = -north (m), origin at
the campus bbox centre. Building node ids are exactly the ids used in campus.json and in
the GLB (BLDG_<osm_id>), so `make check` can verify parity across the three files.
"""

from __future__ import annotations

import json
import math
import os
import random

from shapely.geometry import Point, shape
from shapely.ops import unary_union

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAV = os.path.join(ROOT, "public", "data", "nav.json")
SCATTER = os.path.join(ROOT, "public", "data", "scatter.json")
GRID = 4.0            # metres; road vertices closer than this are merged
LINK_RADIUS = 300.0   # metres from a building to its nearest road node
ROAD_MARGIN = 0.0015  # degrees (~150 m) around the campus bbox
TREE_SPACING = 35.0   # metres between trees along a road
TREE_OFFSET = 6.5     # metres from the road centreline
MAX_TREES = 250


def local_scale(lat: float) -> tuple[float, float]:
    phi = math.radians(lat)
    m_lat = 111132.92 - 559.82 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi)
    return m_lat, m_lon


def to_lonlat(geom: dict) -> dict:
    """Stored geometries use [lat, lon]; GeoJSON needs [lon, lat]."""
    if geom["type"] == "LineString":
        return {"type": "LineString", "coordinates": [[c[1], c[0]] for c in geom["coordinates"]]}
    return {"type": "Polygon", "coordinates": [[[c[1], c[0]] for c in ring] for ring in geom["coordinates"]]}


class Projector:
    def __init__(self, lat0: float, lon0: float) -> None:
        self.lat0, self.lon0 = lat0, lon0

    def __call__(self, lat: float, lon: float) -> tuple[float, float]:
        m_lat, m_lon = local_scale(lat)
        east = (lon - self.lon0) * m_lon
        north = (lat - self.lat0) * m_lat
        return east, -north  # three.js: x = east, z = -north


def main() -> int:
    bbox = json.load(open(os.path.join(ROOT, "data-src", "campus_bbox.json")))
    south, north, west, east = (float(x) for x in bbox["boundingbox"][:4])
    lat0, lon0 = (south + north) / 2.0, (west + east) / 2.0
    project = Projector(lat0, lon0)

    boundary = shape(bbox["polygon"])
    campus = json.load(open(os.path.join(ROOT, "public", "data", "campus.json")))
    geojson = json.load(open(os.path.join(ROOT, "data-src", "osm_campus.geojson")))

    building_geoms = {}
    for f in geojson.get("features", []):
        p = f.get("properties") or {}
        if p.get("layer") == "building" and f.get("geometry", {}).get("type") == "Polygon":
            building_geoms[str(p.get("osm_id"))] = shape(to_lonlat(f["geometry"]))

    # ---------------- nav: buildings ------------------------------------
    nodes: list[dict] = [{"id": b["id"], "x": 0.0, "z": 0.0} for b in campus["buildings"]]
    building_xy: dict[str, tuple[float, float]] = {}
    for node, b in zip(nodes, campus["buildings"]):
        x, z = project(b["location"]["lat"], b["location"]["lon"])
        node["x"], node["z"] = round(x, 2), round(z, 2)
        building_xy[b["id"]] = (x, z)

    # ---------------- nav: road network ---------------------------------
    road_nodes: dict[tuple[int, int], str] = {}
    links: dict[tuple[str, str], float] = {}

    def road_node(x: float, z: float) -> str:
        key = (round(x / GRID), round(z / GRID))
        nid = road_nodes.get(key)
        if nid is None:
            nid = f"N{len(road_nodes):05d}"
            road_nodes[key] = nid
            nodes.append({"id": nid, "x": round(key[0] * GRID, 2), "z": round(key[1] * GRID, 2)})
        return nid

    def link(a: str, b: str, length: float) -> None:
        if a == b:
            return
        key = (a, b) if a < b else (b, a)
        if key not in links or length < links[key]:
            links[key] = length

    for f in geojson.get("features", []):
        p = f.get("properties") or {}
        if p.get("layer") not in ("road", "footpath"):
            continue
        geom = f.get("geometry") or {}
        if geom.get("type") != "LineString" or not geom.get("coordinates"):
            continue
        lats = [c[0] for c in geom["coordinates"]]
        lons = [c[1] for c in geom["coordinates"]]
        if max(lats) < south - ROAD_MARGIN or min(lats) > north + ROAD_MARGIN:
            continue
        if max(lons) < west - ROAD_MARGIN or min(lons) > east + ROAD_MARGIN:
            continue
        prev = None
        for lat, lon in geom["coordinates"]:
            x, z = project(lat, lon)
            nid = road_node(x, z)
            if prev is not None and prev != nid:
                a = next(n for n in nodes if n["id"] == prev)
                b = next(n for n in nodes if n["id"] == nid)
                link(prev, nid, math.hypot(a["x"] - b["x"], a["z"] - b["z"]))
            prev = nid

    # Attach every building to its nearest road node.
    road_node_ids = [n for n in nodes if n["id"].startswith("N")]
    for bid, (x, z) in building_xy.items():
        best, best_d = None, LINK_RADIUS
        for n in road_node_ids:
            d = math.hypot(n["x"] - x, n["z"] - z)
            if d < best_d:
                best, best_d = n, d
        if best is not None:
            link(bid, best["id"], best_d)

    # Bridge disconnected road components so A* can route between any two buildings.
    parent = {n["id"]: n["id"] for n in nodes}

    def find(a: str) -> str:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for a, b in links:
        union(a, b)

    components: dict[str, list[dict]] = {}
    for n in nodes:
        components.setdefault(find(n["id"]), []).append(n)
    if len(components) > 1:
        comps = sorted(components.values(), key=lambda c: -len(c))
        main = comps[0]
        for comp in comps[1:]:
            best = None
            for a in comp:
                for b in main:
                    d = math.hypot(a["x"] - b["x"], a["z"] - b["z"])
                    if best is None or d < best[0]:
                        best = (d, a, b)
            if best:
                link(best[1]["id"], best[2]["id"], best[0])
                union(best[1]["id"], best[2]["id"])
                main = main + comp

    nav = {
        "nodes": nodes,
        "links": [
            {"from": a, "to": b, "length": round(length, 2)}
            for (a, b), length in sorted(links.items())
        ],
    }
    os.makedirs(os.path.dirname(NAV), exist_ok=True)
    with open(NAV, "w") as fh:
        json.dump(nav, fh)

    # ---------------- scatter: trees along roads ------------------------
    rng = random.Random(42)
    footprints = unary_union([g for g in building_geoms.values() if g.is_valid])
    road_lines = []
    for f in geojson.get("features", []):
        p = f.get("properties") or {}
        if p.get("layer") not in ("road", "footpath"):
            continue
        geom = f.get("geometry") or {}
        if geom.get("type") != "LineString" or not geom.get("coordinates"):
            continue
        lats = [c[0] for c in geom["coordinates"]]
        lons = [c[1] for c in geom["coordinates"]]
        if max(lats) < south - ROAD_MARGIN or min(lats) > north + ROAD_MARGIN:
            continue
        if max(lons) < west - ROAD_MARGIN or min(lons) > east + ROAD_MARGIN:
            continue
        road_lines.append(shape(to_lonlat(geom)))
    road_union = unary_union(road_lines) if road_lines else None

    trees = []
    for line in road_lines:
        if len(trees) >= MAX_TREES:
            break
        length = line.length  # degrees; converted below via local scale
        m_per_deg = 106_000.0  # rough average at this latitude, only used for spacing
        steps = int(length * m_per_deg / TREE_SPACING)
        for i in range(steps):
            if len(trees) >= MAX_TREES:
                break
            frac = (i + 0.5) / max(1, steps)
            pt = line.interpolate(frac, normalized=True)
            # local tangent -> perpendicular offset
            d = 1e-4
            p0 = line.interpolate(max(0.0, frac - d), normalized=True)
            p1 = line.interpolate(min(1.0, frac + d), normalized=True)
            dx, dy = p1.x - p0.x, p1.y - p0.y
            norm = math.hypot(dx, dy) or 1.0
            offset = TREE_OFFSET * (1 if i % 2 == 0 else -1)
            cand = Point(pt.x - dy / norm * offset * 1e-5, pt.y + dx / norm * offset * 1e-5)
            if not boundary.contains(cand):
                continue
            if not footprints.is_empty and footprints.buffer(4e-5).contains(cand):
                continue
            if road_union is not None and road_union.distance(cand) < 3.5e-5:
                continue
            x, z = project(cand.y, cand.x)
            trees.append({
                "type": "tree",
                "id": f"SCAT_tree_{len(trees) + 1:03d}",
                "position": [round(x, 2), 0.0, round(z, 2)],
                "rotation": [0.0, round(rng.uniform(0, 2 * math.pi), 3), 0.0],
                "scale": round(rng.uniform(0.8, 1.3), 2),
            })

    with open(SCATTER, "w") as fh:
        json.dump(trees, fh)

    building_nodes = sum(1 for n in nodes if n["id"].startswith("BLDG_"))
    print(f"NAV_OK nodes={len(nodes)} links={len(nav['links'])} building_nodes={building_nodes} "
          f"scatter={len(trees)} -> public/data/nav.json + public/data/scatter.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
