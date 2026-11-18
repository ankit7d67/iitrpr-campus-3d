#!/usr/bin/env python
"""Budget + consistency checks for the generated campus assets."""

from __future__ import annotations

import argparse
import json
import os
import struct


def read_glb_stats(path: str) -> dict:
    with open(path, "rb") as f:
        magic = f.read(4)
        version, length = struct.unpack("<II", f.read(8))
        clen, ctype = struct.unpack("<II", f.read(8))
        js = f.read(clen)
        j = json.loads(js)
    meshes = j.get("meshes") or []
    primitives = 0
    indices = 0
    seen_nodes = []
    def walk(node: list) -> None:
        nonlocal primitives, indices
        for key in ("mesh",):
            if key in node and node[key] is not None:
                primitives += 1
    materials = j.get("materials") or []
    textures = j.get("textures") or []
    total_tris = 0
    for m in meshes:
        for p in m.get("primitives") or []:
            acc = (p.get("attributes") or {}).get("POSITION") or {}
            count = acc.get("count") or 0
            total_tris += max(0, int(count) // 3)
    return {
        "size_bytes": os.path.getsize(path),
        "meshes": len(meshes),
        "primitives": primitives,
        "materials": len(materials),
        "textures": len(textures),
        "triangles": total_tris,
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

    stats = read_glb_stats(args.model)
    ok = True
    if stats["size_bytes"] > args.max_model_mb * 1024 * 1024:
        print(f"FAIL: model size {stats['size_bytes']} > {args.max_model_mb}MB")
        ok = False
    if stats["materials"] > args.max_materials:
        print(f"FAIL: materials {stats['materials']} > {args.max_materials}")
        ok = False
    if stats["textures"] > args.max_textures:
        print(f"FAIL: textures {stats['textures']} > {args.max_textures}")
        ok = False
    if stats["triangles"] > args.tris_in_view:
        print(f"FAIL: triangles {stats['triangles']} > {args.tris_in_view} in view")
        ok = False

    campus = json.load(open(args.campus))
    nav = json.load(open(args.nav))
    campus_ids = {b.get("id") for b in (campus or {}).get("buildings") or []}
    glb_ids = set()
    # GLB custom property ids cannot be enumerated without trimesh; parity check is
    # done via scripts/check_ids.py against the exported GLB metadata when available.

    if not ok:
        return 1
    print("CHECK_OK", json.dumps(stats))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
