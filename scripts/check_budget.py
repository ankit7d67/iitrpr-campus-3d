#!/usr/bin/env python
"""Budget + consistency checks for the generated campus assets.

Checks (AGENTS.md):
  * GLB <= 5 MB
  * materials <= 4, textures <= 2
  * triangles in view <= 150,000
  * ids identical across the GLB (node names/extras), campus.json and nav.json
"""

from __future__ import annotations

import argparse
import json
import os
import struct


def read_glb(path: str) -> dict:
    with open(path, "rb") as f:
        magic = f.read(4)
        if magic != b"glTF":
            raise SystemExit(f"FAIL: {path} is not a GLB")
        _version, _length = struct.unpack("<II", f.read(8))
        clen, _ctype = struct.unpack("<II", f.read(8))
        js = f.read(clen)
    return json.loads(js)


def glb_stats(path: str) -> dict:
    j = read_glb(path)
    accessors = j.get("accessors") or []
    triangles = 0
    primitives = 0
    for mesh in j.get("meshes") or []:
        for prim in mesh.get("primitives") or []:
            primitives += 1
            if "indices" in prim:
                count = accessors[prim["indices"]].get("count") or 0
            else:
                count = accessors[(prim.get("attributes") or {}).get("POSITION", 0)].get("count") or 0
            triangles += count // 3

    glb_ids = set()
    for node in j.get("nodes") or []:
        name = node.get("name") or ""
        extras = node.get("extras") or {}
        bid = extras.get("bid")
        if isinstance(bid, str):
            glb_ids.add(bid)
        elif name.startswith("BLDG_"):
            glb_ids.add(name)

    return {
        "size_bytes": os.path.getsize(path),
        "nodes": len(j.get("nodes") or []),
        "meshes": len(j.get("meshes") or []),
        "primitives": primitives,
        "materials": len(j.get("materials") or []),
        "textures": len(j.get("textures") or []),
        "triangles": triangles,
        "building_ids": sorted(glb_ids - {"GROUND", "ROAD_ALL"}),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--campus", default="public/data/campus.json")
    ap.add_argument("--nav", default="public/data/nav.json")
    ap.add_argument("--model", default="public/models/campus.glb")
    ap.add_argument("--scatter", default="public/data/scatter.json")
    ap.add_argument("--tris-in-view", type=int, default=150000)
    ap.add_argument("--max-model-mb", type=float, default=5.0)
    ap.add_argument("--max-materials", type=int, default=4)
    ap.add_argument("--max-textures", type=int, default=2)
    args = ap.parse_args()

    stats = glb_stats(args.model)
    failures: list[str] = []

    if stats["size_bytes"] > args.max_model_mb * 1024 * 1024:
        failures.append(f"model size {stats['size_bytes'] / 1e6:.2f} MB > {args.max_model_mb} MB")
    if stats["materials"] > args.max_materials:
        failures.append(f"materials {stats['materials']} > {args.max_materials}")
    if stats["textures"] > args.max_textures:
        failures.append(f"textures {stats['textures']} > {args.max_textures}")
    if stats["triangles"] > args.tris_in_view:
        failures.append(f"triangles {stats['triangles']} > {args.tris_in_view} in view")

    campus = json.load(open(args.campus))
    nav = json.load(open(args.nav))
    campus_ids = {b.get("id") for b in (campus or {}).get("buildings") or []}
    nav_ids = {n.get("id") for n in (nav or {}).get("nodes") or [] if str(n.get("id", "")).startswith("BLDG_")}
    glb_ids = set(stats["building_ids"])

    if not campus_ids:
        failures.append("campus.json has no buildings")
    if campus_ids != glb_ids:
        failures.append(
            f"GLB ids != campus.json ids (missing in GLB: {sorted(campus_ids - glb_ids)[:5]}, "
            f"extra in GLB: {sorted(glb_ids - campus_ids)[:5]})"
        )
    if campus_ids != nav_ids:
        failures.append(
            f"nav.json ids != campus.json ids (missing in nav: {sorted(campus_ids - nav_ids)[:5]}, "
            f"extra in nav: {sorted(nav_ids - campus_ids)[:5]})"
        )
    if not (nav or {}).get("links"):
        failures.append("nav.json has no links")

    scatter = json.load(open(args.scatter)) if os.path.exists(args.scatter) else []
    if not scatter:
        failures.append("scatter.json is empty")

    for f in failures:
        print(f"FAIL: {f}")
    if failures:
        return 1

    print(
        "CHECK_OK",
        json.dumps({
            "size_mb": round(stats["size_bytes"] / 1e6, 2),
            "triangles": stats["triangles"],
            "materials": stats["materials"],
            "textures": stats["textures"],
            "buildings": len(campus_ids),
            "nav_nodes": len((nav or {}).get("nodes") or []),
            "nav_links": len((nav or {}).get("links") or []),
            "scatter": len(scatter),
        }),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
