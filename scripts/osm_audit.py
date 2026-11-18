#!/usr/bin/env python
"""Generate the OSM audit: build/osm_audit.html + OSM_AUDIT.md.

Reads data-src/campus_bbox.json and data-src/osm_campus.geojson and reports:
  * the campus bbox and the real boundary polygon (centre, size, acres)
  * building counts, named vs unnamed, inside vs outside
  * inside buildings that carry building:levels / height / building-type tags
  * the 10 largest unnamed inside buildings, with OSM way links
  * fully contained footprints (possible duplicates or building parts)
  * a ranked correction list built ONLY from buildings inside the boundary

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
CONTAINED_SHARE = 0.95  # intersection / smaller footprint => duplicate or part


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
    if geom is None or geom.is_empty:
        return 0.0
    return geom.area * KM_PER_DEG_LON * KM_PER_DEG_LAT * 1_000_000.0


def props(feature: dict) -> dict:
    return feature.get("properties") or {}


def osm_id(feature: dict) -> str:
    return str(props(feature).get("osm_id"))


def way_url(feature: dict) -> str:
    return f"https://www.openstreetmap.org/way/{osm_id(feature)}"


def label(feature: dict) -> str:
    name = (props(feature).get("name") or "").strip()
    return f"{name} (osm_id={osm_id(feature)})" if name else f"(unnamed, osm_id={osm_id(feature)})"


def is_named(feature: dict) -> bool:
    return bool((props(feature).get("name") or "").strip())


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main() -> int:
    bbox = json.load(open("data-src/campus_bbox.json"))
    bb = bbox.get("boundingbox") or []
    south, north, west, east = [float(x) for x in bb[:4]]
    bbox_centre_lat = (south + north) / 2.0
    bbox_centre_lon = (west + east) / 2.0
    bbox_width_km = (north - south) * KM_PER_DEG_LAT
    bbox_height_km = (east - west) * KM_PER_DEG_LON
    bbox_area_km2 = bbox_width_km * bbox_height_km
    bbox_dist_km = math.hypot(
        (bbox_centre_lat - ANCHOR_LAT) * KM_PER_DEG_LAT,
        (bbox_centre_lon - ANCHOR_LON) * KM_PER_DEG_LON,
    )

    boundary = shape(bbox.get("polygon") or {
        "type": "Polygon",
        "coordinates": [[[west, south], [west, north], [east, north], [east, south], [west, south]]],
    })
    boundary_centroid = boundary.centroid
    boundary_area_km2 = boundary.area * KM_PER_DEG_LAT * KM_PER_DEG_LON

    osm = json.load(open("data-src/osm_campus.geojson"))
    buildings = [f for f in osm.get("features", []) if props(f).get("layer") == "building"]
    named = [f for f in buildings if is_named(f)]
    unnamed = [f for f in buildings if not is_named(f)]

    inside, outside = [], []
    geoms: dict[str, object] = {}
    for f in buildings:
        geom = building_geom(f)
        geoms[osm_id(f)] = geom
        ok = geom is not None and geom.is_valid and not geom.is_empty and geom.intersects(boundary)
        (inside if ok else outside).append(f)

    inside.sort(key=lambda f: int(osm_id(f)))

    # --- contained footprints (duplicates / parts) -------------------------
    contained_pairs: list[tuple[dict, dict, float]] = []
    inside_geoms = [(f, geoms[osm_id(f)]) for f in inside if geoms[osm_id(f)] is not None]
    for i in range(len(inside_geoms)):
        fi, gi = inside_geoms[i]
        for j in range(i + 1, len(inside_geoms)):
            fj, gj = inside_geoms[j]
            if not gi.intersects(gj):
                continue
            smaller = min(gi.area, gj.area)
            if smaller <= 0:
                continue
            share = gi.intersection(gj).area / smaller
            if share >= CONTAINED_SHARE:
                # keeper: named first, then larger
                keep, drop = (fi, fj)
                if not is_named(fi) and is_named(fj):
                    keep, drop = fj, fi
                elif is_named(fi) == is_named(fj) and gi.area < gj.area:
                    keep, drop = fj, fi
                contained_pairs.append((keep, drop, share))

    # --- metadata tags -----------------------------------------------------
    with_levels = [f for f in inside if (props(f).get("levels") or "").strip()]
    with_height = [f for f in inside if (props(f).get("height") or "").strip()]
    with_building_tag = [f for f in inside if (props(f).get("building") or "").strip()]
    with_amenity = [f for f in inside if (props(f).get("amenity") or "").strip()]
    type_counts: dict[str, int] = {}
    for f in with_building_tag:
        key = (props(f).get("building") or "").strip()
        type_counts[key] = type_counts.get(key, 0) + 1

    # --- large unnamed inside buildings (top 10) ---------------------------
    unnamed_inside = sorted(
        [f for f in inside if not is_named(f)],
        key=lambda f: -footprint_m2(geoms[osm_id(f)]),
    )
    top_unnamed = unnamed_inside[:10]

    # --- ranked corrections (inside only) ---------------------------------
    dropped_ids = {osm_id(drop) for _, drop, _ in contained_pairs}
    ranked: list[tuple[str, float, dict, str]] = []
    for f in unnamed_inside:
        area = footprint_m2(geoms[osm_id(f)])
        reason = "unnamed, large footprint"
        if osm_id(f) in dropped_ids:
            reason = "unnamed, contained footprint (duplicate/part)"
        ranked.append(("large unnamed inside", area, f, reason))
    for keep, drop, share in contained_pairs:
        ranked.append((
            "overlap",
            footprint_m2(geoms[osm_id(keep)]),
            keep,
            f"duplicate/part: {label(drop)} is {share * 100:.0f}% contained",
        ))

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    md = [
        "# OSM Audit — IIT Ropar Campus",
        "",
        f"Generated: {generated}",
        "",
        "## Campus boundary",
        "",
        "### Bounding box",
        "",
        f"- south / north / west / east: {south} / {north} / {west} / {east}",
        f"- bbox centre: {bbox_centre_lat:.7f} N, {bbox_centre_lon:.7f} E",
        f"- distance from anchor ({ANCHOR_LAT}, {ANCHOR_LON}): {bbox_dist_km:.2f} km",
        f"- bbox size: {bbox_width_km:.2f} km (N-S) x {bbox_height_km:.2f} km (E-W)",
        f"- bbox area: {bbox_area_km2:.2f} km2 = {bbox_area_km2 * ACRES_PER_KM2:.0f} acres",
        "",
        "### Actual boundary polygon (Nominatim)",
        "",
        f"- polygon area: {boundary_area_km2:.3f} km2 = {boundary_area_km2 * ACRES_PER_KM2:.0f} acres",
        f"- polygon centroid: {boundary_centroid.y:.7f} N, {boundary_centroid.x:.7f} E",
        "",
        "## Buildings",
        "",
        f"- total buildings: {len(buildings)}",
        f"- named: {len(named)}",
        f"- unnamed: {len(unnamed)}",
        f"- inside campus boundary: {len(inside)}",
        f"- outside campus boundary: {len(outside)}",
        f"- contained footprint pairs (>= {CONTAINED_SHARE * 100:.0f}% of smaller): {len(contained_pairs)}",
        "",
        "### Inside buildings with building metadata",
        "",
        f"- with building:levels: {len(with_levels)}",
        f"- with height: {len(with_height)}",
        f"- with building type tag: {len(with_building_tag)}",
        f"- with amenity tag: {len(with_amenity)}",
    ]
    if type_counts:
        md.append("- building type distribution: " + ", ".join(f"{k}={v}" for k, v in sorted(type_counts.items())))
    md.append("")
    for f in inside:
        if f in with_levels or f in with_height or f in with_building_tag or f in with_amenity:
            bits = []
            if props(f).get("levels"):
                bits.append(f"building:levels={props(f).get('levels')}")
            if props(f).get("height"):
                bits.append(f"height={props(f).get('height')}")
            if props(f).get("building"):
                bits.append(f"building={props(f).get('building')}")
            if props(f).get("amenity"):
                bits.append(f"amenity={props(f).get('amenity')}")
            md.append(f"- {label(f)} — " + ", ".join(bits) + f" — {way_url(f)}")
    if not (with_levels or with_height or with_building_tag or with_amenity):
        md.append("- none (the fetched features carry no building metadata)")

    md += ["", "### Large unnamed inside buildings (name these in OSM)", ""]
    for i, f in enumerate(top_unnamed, 1):
        md.append(f"{i}. {way_url(f)} — {footprint_m2(geoms[osm_id(f)]):.0f} m2")
    if not top_unnamed:
        md.append("- none")

    md += ["", "### Contained footprints (possible duplicate or building part)", ""]
    if contained_pairs:
        for keep, drop, share in contained_pairs:
            md.append(
                f"- keep {label(keep)}; {label(drop)} is {share * 100:.0f}% contained — "
                "possible duplicate or building part, verify in OSM"
            )
    else:
        md.append("- none detected")

    md += ["", "### Named buildings", ""]
    for f in sorted(named, key=lambda x: (props(x).get("name") or "").lower()):
        md.append(f"- {props(f).get('name')} (osm_id={osm_id(f)}, {'inside' if f in inside else 'OUTSIDE'})")

    md += ["", "## Ranked list needing correction (inside boundary only)", ""]
    for i, (kind, area, f, reason) in enumerate(ranked, 1):
        md.append(f"{i}. [{kind}] {label(f)} — {area:.0f} m2 — {reason} — {way_url(f)}")
    if not ranked:
        md.append("- none")

    md += ["", "## Buildings outside the campus boundary (separate, not ranked)", ""]
    for f in outside:
        md.append(f"- {label(f)} — {way_url(f)}")
    if not outside:
        md.append("- none")

    os.makedirs("build", exist_ok=True)
    with open("OSM_AUDIT.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")

    # ---------------------------- HTML ------------------------------------
    css = (
        "body{font-family:system-ui,sans-serif;background:#f4f7fb;color:#10233a;padding:2rem;line-height:1.5}"
        "h1{color:#2f6fed}h2{margin-top:2.2rem;border-bottom:2px solid #d5dee9}"
        "table{border-collapse:collapse;width:100%;margin:.75rem 0}"
        "th,td{border:1px solid #d5dee9;padding:6px;text-align:left;vertical-align:top}"
        "th{background:#2f6fed;color:#fff}tr:nth-child(even){background:#eef3fa}"
        ".muted{color:#5a6b82}code{background:#e7edf7;padding:1px 4px;border-radius:3px}"
    )

    def table(headers: list[str], rows: list[str], empty: str) -> str:
        head = "".join(f"<th>{esc(h)}</th>" for h in headers)
        body = "".join(rows) or f"<tr><td colspan='{len(headers)}'>{esc(empty)}</td></tr>"
        return f"<table><tr>{head}</tr>{body}</table>"

    rows_meta = [
        f"<tr><td>{esc(label(f))}</td><td>{esc(str(props(f).get('levels') or ''))}</td>"
        f"<td>{esc(str(props(f).get('height') or ''))}</td><td>{esc(str(props(f).get('building') or ''))}</td>"
        f"<td>{esc(str(props(f).get('amenity') or ''))}</td><td><a href='{way_url(f)}'>way/{osm_id(f)}</a></td></tr>"
        for f in inside if f in with_levels or f in with_height or f in with_building_tag or f in with_amenity
    ]
    rows_unnamed = [
        f"<tr><td>{i}</td><td><a href='{way_url(f)}'>way/{osm_id(f)}</a></td>"
        f"<td>{footprint_m2(geoms[osm_id(f)]):.0f}</td></tr>"
        for i, f in enumerate(top_unnamed, 1)
    ]
    rows_contained = [
        f"<tr><td>{esc(label(keep))}</td><td>{esc(label(drop))}</td><td>{share * 100:.0f}%</td>"
        "<td>possible duplicate or building part, verify in OSM</td></tr>"
        for keep, drop, share in contained_pairs
    ]
    rows_ranked = [
        f"<tr><td>{i}</td><td>{esc(kind)}</td><td>{esc(label(f))}</td><td>{area:.0f}</td>"
        f"<td>{esc(reason)}</td><td><a href='{way_url(f)}'>way/{osm_id(f)}</a></td></tr>"
        for i, (kind, area, f, reason) in enumerate(ranked, 1)
    ]
    rows_outside = [
        f"<tr><td>{esc(label(f))}</td><td><a href='{way_url(f)}'>way/{osm_id(f)}</a></td></tr>"
        for f in outside
    ]
    rows_named = [
        f"<tr><td>{esc(props(f).get('name') or '')}</td><td>{osm_id(f)}</td>"
        f"<td>{'inside' if f in inside else 'outside'}</td></tr>"
        for f in sorted(named, key=lambda x: (props(x).get("name") or "").lower())
    ]

    html = (
        "<!doctype html>\n<html><head><meta charset='utf-8'>"
        "<title>OSM Audit — IIT Ropar Campus</title>"
        f"<style>{css}</style></head><body>\n"
        "<h1>OSM Audit — IIT Ropar Campus</h1>"
        f"<p class='muted'>Generated: {generated}</p>"
        "<h2>Campus boundary</h2>"
        "<h3>Bounding box</h3>"
        + table(["Field", "Value"], [
            f"<tr><td>south / north / west / east</td><td>{south} / {north} / {west} / {east}</td></tr>",
            f"<tr><td>centre</td><td>{bbox_centre_lat:.7f} N, {bbox_centre_lon:.7f} E</td></tr>",
            f"<tr><td>distance from anchor ({ANCHOR_LAT}, {ANCHOR_LON})</td><td>{bbox_dist_km:.2f} km</td></tr>",
            f"<tr><td>size</td><td>{bbox_width_km:.2f} km (N-S) x {bbox_height_km:.2f} km (E-W)</td></tr>",
            f"<tr><td>area</td><td>{bbox_area_km2:.2f} km2 = {bbox_area_km2 * ACRES_PER_KM2:.0f} acres</td></tr>",
        ], "no data")
        + "<h3>Actual boundary polygon (Nominatim)</h3>"
        + table(["Field", "Value"], [
            f"<tr><td>area</td><td>{boundary_area_km2:.3f} km2 = {boundary_area_km2 * ACRES_PER_KM2:.0f} acres</td></tr>",
            f"<tr><td>centroid</td><td>{boundary_centroid.y:.7f} N, {boundary_centroid.x:.7f} E</td></tr>",
        ], "no data")
        + "<h2>Buildings</h2>"
        f"<p>total <b>{len(buildings)}</b> · named <b>{len(named)}</b> · unnamed <b>{len(unnamed)}</b> · "
        f"inside <b>{len(inside)}</b> · outside <b>{len(outside)}</b> · "
        f"contained footprint pairs <b>{len(contained_pairs)}</b></p>"
        "<h2>Inside buildings with building metadata</h2>"
        f"<p>building:levels <b>{len(with_levels)}</b> · height <b>{len(with_height)}</b> · "
        f"building tag <b>{len(with_building_tag)}</b> · amenity <b>{len(with_amenity)}</b>"
        + ((" · types " + ", ".join(f"{esc(k)}={v}" for k, v in sorted(type_counts.items()))) if type_counts else "")
        + "</p>"
        + table(["Building", "building:levels", "height", "building", "amenity", "OSM"], rows_meta,
                "none (the fetched features carry no building metadata)")
        + "<h2>Large unnamed inside buildings (name these in OSM)</h2>"
        + table(["#", "OSM way", "Footprint m²"], rows_unnamed, "none")
        + "<h2>Contained footprints (possible duplicate or building part)</h2>"
        + table(["Keep", "Contained footprint", "Overlap", "Action"], rows_contained, "none detected")
        + "<h2>Named buildings</h2>"
        + table(["Name", "OSM id", "Boundary"], rows_named, "none")
        + "<h2>Ranked list needing correction (inside boundary only)</h2>"
        + table(["#", "Kind", "Building", "Footprint m²", "Reason", "OSM"], rows_ranked, "none")
        + "<h2>Buildings outside the campus boundary (separate, not ranked)</h2>"
        + table(["Building", "OSM"], rows_outside, "none")
        + "</body></html>\n"
    )
    with open("build/osm_audit.html", "w", encoding="utf-8") as fh:
        fh.write(html)

    print(
        f"OSM_AUDIT buildings={len(buildings)} named={len(named)} unnamed={len(unnamed)} "
        f"inside={len(inside)} outside={len(outside)} contained_pairs={len(contained_pairs)} "
        f"levels={len(with_levels)} height={len(with_height)} building_tag={len(with_building_tag)} "
        f"polygon={boundary_area_km2 * ACRES_PER_KM2:.0f} acres -> build/osm_audit.html + OSM_AUDIT.md"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
