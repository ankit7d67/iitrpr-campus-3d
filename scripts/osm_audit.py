#!/usr/bin/env python
"""Generate the OSM audit: build/osm_audit.html + OSM_AUDIT.md.

Reads data-src/campus_bbox.json and data-src/osm_campus.geojson and reports:
  * the campus bbox (all four values, centre, size, area) against the anchor
  * building counts, named vs unnamed
  * buildings outside the campus boundary
  * overlapping building pairs
  * a ranked list of buildings that most need correcting in OSM

Run via `make osm` (wired into the OSM pipeline) or `make audit`.
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone

from shapely.geometry import shape

ANCHOR_LAT = 30.9704
ANCHOR_LON = 76.4691
KM_PER_DEG_LAT = 111.32
KM_PER_DEG_LON = 85.0  # at ~30.97 N
ACRES_PER_KM2 = 247.105


def building_geom(feature: dict):
    """Return a shapely geometry in (lon, lat) order, or None."""
    g = feature.get("geometry") or {}
    if g.get("type") == "Polygon":
        return shape({
            "type": "Polygon",
            "coordinates": [[[c[1], c[0]] for c in ring] for ring in g["coordinates"]],
        })
    if g.get("type") == "LineString":
        return shape({
            "type": "LineString",
            "coordinates": [[c[1], c[0]] for c in g["coordinates"]],
        })
    return None


def footprint_m2(geom) -> float:
    """Approximate footprint area in m2 from a (lon, lat) geometry."""
    if geom is None or geom.is_empty:
        return 0.0
    return geom.area * KM_PER_DEG_LON * KM_PER_DEG_LAT * 1_000_000.0


def label(feature: dict) -> str:
    p = feature.get("properties") or {}
    name = (p.get("name") or "").strip()
    return f"{name} (osm_id={p.get('osm_id')})" if name else f"(unnamed, osm_id={p.get('osm_id')})"


def main() -> int:
    bbox = json.load(open("data-src/campus_bbox.json"))
    bb = bbox.get("boundingbox") or []
    south, north, west, east = [float(x) for x in bb[:4]]
    centre_lat = (south + north) / 2.0
    centre_lon = (west + east) / 2.0
    dist_from_anchor_km = math.hypot(
        (centre_lat - ANCHOR_LAT) * KM_PER_DEG_LAT,
        (centre_lon - ANCHOR_LON) * KM_PER_DEG_LON,
    )
    width_km = (north - south) * KM_PER_DEG_LAT
    height_km = (east - west) * KM_PER_DEG_LON
    area_km2 = width_km * height_km

    boundary = shape(bbox.get("polygon") or {
        "type": "Polygon",
        "coordinates": [[[west, south], [west, north], [east, north], [east, south], [west, south]]],
    })

    osm = json.load(open("data-src/osm_campus.geojson"))
    buildings = [f for f in osm.get("features", []) if (f.get("properties") or {}).get("layer") == "building"]
    named = [f for f in buildings if ((f.get("properties") or {}).get("name") or "").strip()]
    unnamed = [f for f in buildings if not ((f.get("properties") or {}).get("name") or "").strip()]

    inside, outside = [], []
    for f in buildings:
        geom = building_geom(f)
        ok = geom is not None and geom.is_valid and not geom.is_empty and geom.intersects(boundary)
        (inside if ok else outside).append(f)

    # Overlapping pairs (intersection > 20% of the smaller footprint).
    overlaps: list[tuple[dict, dict, float]] = []
    geoms = [(f, building_geom(f)) for f in inside]
    for i in range(len(geoms)):
        fi, gi = geoms[i]
        if gi is None or gi.is_empty:
            continue
        for j in range(i + 1, len(geoms)):
            fj, gj = geoms[j]
            if gj is None or gj.is_empty or not gi.intersects(gj):
                continue
            inter = gi.intersection(gj).area
            smaller = min(gi.area, gj.area)
            if smaller > 0 and inter / smaller >= 0.20:
                overlaps.append((fi, fj, inter / smaller))

    # Rank corrections: outside the boundary > overlap > unnamed > large footprint.
    overlap_count: dict[str, int] = {}
    for fi, fj, _ in overlaps:
        for f in (fi, fj):
            key = str((f.get("properties") or {}).get("osm_id"))
            overlap_count[key] = overlap_count.get(key, 0) + 1

    ranked = []
    for f in buildings:
        p = f.get("properties") or {}
        key = str(p.get("osm_id"))
        reasons, score = [], 0
        if f in outside:
            score += 100
            reasons.append("outside campus boundary")
        if overlap_count.get(key):
            score += 20 * overlap_count[key]
            reasons.append(f"overlaps {overlap_count[key]} other building(s)")
        if not (p.get("name") or "").strip():
            score += 10
            reasons.append("unnamed")
        area = footprint_m2(building_geom(f))
        score += min(area / 100.0, 20.0)
        if score >= 10:
            ranked.append((score, f, reasons, area))
    ranked.sort(key=lambda row: -row[0])

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    md = [
        "# OSM Audit — IIT Ropar Campus",
        "",
        f"Generated: {generated}",
        "",
        "## Campus boundary",
        "",
        f"- bbox south / north / west / east: {south} / {north} / {west} / {east}",
        f"- bbox centre: {centre_lat:.7f} N, {centre_lon:.7f} E",
        f"- distance from anchor ({ANCHOR_LAT}, {ANCHOR_LON}): {dist_from_anchor_km:.2f} km",
        f"- bbox size: {width_km:.2f} km (N-S) x {height_km:.2f} km (E-W)",
        f"- bbox area: {area_km2:.2f} km2 = {area_km2 * ACRES_PER_KM2:.0f} acres",
        "",
        "## Buildings",
        "",
        f"- total buildings: {len(buildings)}",
        f"- named: {len(named)}",
        f"- unnamed: {len(unnamed)}",
        f"- inside campus boundary: {len(inside)}",
        f"- outside campus boundary: {len(outside)}",
        f"- overlapping pairs (>=20% of smaller footprint): {len(overlaps)}",
        "",
        "### Named buildings",
        "",
    ]
    for f in sorted(named, key=lambda x: (x.get("properties", {}).get("name") or "").lower()):
        p = f.get("properties") or {}
        where = "inside" if f in inside else "OUTSIDE"
        md.append(f"- {p.get('name')} (osm_id={p.get('osm_id')}, {where})")

    md += ["", "### Buildings outside the campus boundary", ""]
    if outside:
        for f in outside:
            md.append(f"- {label(f)}")
    else:
        md.append("- none")

    md += ["", "### Overlapping buildings", ""]
    if overlaps:
        for fi, fj, frac in overlaps:
            md.append(f"- {label(fi)} × {label(fj)} — {frac * 100:.0f}% of smaller footprint")
    else:
        md.append("- none detected")

    md += ["", "### Ranked list needing correction (highest score first)", ""]
    if ranked:
        for score, f, reasons, area in ranked:
            md.append(f"- score {score:.0f}: {label(f)} — {area:.0f} m2 — {', '.join(reasons)}")
    else:
        md.append("- none")

    os.makedirs("build", exist_ok=True)
    with open("OSM_AUDIT.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")

    css = (
        "body{font-family:system-ui,sans-serif;background:#f4f7fb;color:#10233a;padding:2rem;line-height:1.5}"
        "h1{color:#2f6fed}h2{margin-top:2rem;border-bottom:2px solid #d5dee9}"
        "table{border-collapse:collapse;width:100%;margin:.75rem 0}"
        "th,td{border:1px solid #d5dee9;padding:6px;text-align:left;vertical-align:top}"
        "th{background:#2f6fed;color:#fff}tr:nth-child(even){background:#eef3fa}"
        ".outside{color:#b3261e;font-weight:600}.muted{color:#5a6b82}"
    )

    def esc(s: str) -> str:
        return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

    rows_named = "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            esc((f.get("properties") or {}).get("name") or ""),
            (f.get("properties") or {}).get("osm_id"),
            "outside" if f in outside else "inside",
        )
        for f in sorted(named, key=lambda x: (x.get("properties", {}).get("name") or "").lower())
    )
    rows_outside = "".join(
        "<tr><td>{}</td><td>{}</td><td class='outside'>outside</td></tr>".format(
            esc((f.get("properties") or {}).get("name") or "(unnamed)"),
            (f.get("properties") or {}).get("osm_id"),
        )
        for f in outside
    )
    rows_overlaps = "".join(
        "<tr><td>{}</td><td>{}</td><td>{:.0f}%</td></tr>".format(esc(label(fi)), esc(label(fj)), frac * 100)
        for fi, fj, frac in overlaps
    )
    rows_ranked = "".join(
        "<tr><td>{:.0f}</td><td>{}</td><td>{:.0f}</td><td>{}</td></tr>".format(
            score, esc(label(f)), area, esc(", ".join(reasons))
        )
        for score, f, reasons, area in ranked
    )

    html = (
        "<!doctype html>\n<html><head><meta charset='utf-8'>"
        "<title>OSM Audit — IIT Ropar Campus</title>"
        f"<style>{css}</style></head><body>\n"
        "<h1>OSM Audit — IIT Ropar Campus</h1>"
        f"<p class='muted'>Generated: {generated}</p>"
        "<h2>Campus boundary</h2><table>"
        f"<tr><th>bbox south / north / west / east</th><td>{south} / {north} / {west} / {east}</td></tr>"
        f"<tr><th>bbox centre</th><td>{centre_lat:.7f} N, {centre_lon:.7f} E</td></tr>"
        f"<tr><th>distance from anchor ({ANCHOR_LAT}, {ANCHOR_LON})</th><td>{dist_from_anchor_km:.2f} km</td></tr>"
        f"<tr><th>size</th><td>{width_km:.2f} km (N-S) x {height_km:.2f} km (E-W)</td></tr>"
        f"<tr><th>area</th><td>{area_km2:.2f} km2 = {area_km2 * ACRES_PER_KM2:.0f} acres</td></tr>"
        "</table>"
        "<h2>Buildings</h2><p>"
        f"total <b>{len(buildings)}</b> · named <b>{len(named)}</b> · unnamed <b>{len(unnamed)}</b> · "
        f"inside <b>{len(inside)}</b> · outside <b>{len(outside)}</b> · "
        f"overlapping pairs <b>{len(overlaps)}</b></p>"
        "<h2>Named buildings</h2><table><tr><th>Name</th><th>OSM id</th><th>Boundary</th></tr>"
        f"{rows_named}</table>"
        "<h2>Buildings outside the campus boundary</h2><table><tr><th>Name</th><th>OSM id</th><th>Status</th></tr>"
        f"{rows_outside}</table>"
        "<h2>Overlapping buildings</h2><table><tr><th>Building A</th><th>Building B</th><th>Overlap</th></tr>"
        f"{rows_overlaps or '<tr><td colspan=\"3\">none detected</td></tr>'}</table>"
        "<h2>Ranked list needing correction</h2>"
        "<table><tr><th>Score</th><th>Building</th><th>Footprint m²</th><th>Reasons</th></tr>"
        f"{rows_ranked or '<tr><td colspan=\"4\">none</td></tr>'}</table>"
        "</body></html>\n"
    )
    with open("build/osm_audit.html", "w", encoding="utf-8") as fh:
        fh.write(html)

    print(
        f"OSM_AUDIT buildings={len(buildings)} named={len(named)} unnamed={len(unnamed)} "
        f"inside={len(inside)} outside={len(outside)} overlaps={len(overlaps)} "
        f"-> build/osm_audit.html + OSM_AUDIT.md"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
