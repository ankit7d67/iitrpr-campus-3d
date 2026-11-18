"""Headless Blender script: build the IIT Ropar campus from OSM GeoJSON + facade sheet + DEM.

Run:  blender -b -P blender/scripts/import_osm.py
"""

import bpy
import csv
import json
import os


FLOOR_HEIGHT = 3.5
PLINTH_HEIGHT = 0.6


def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def load_geojson(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def build_building(name: str, geometry: dict, floors: int, style: dict) -> None:
    # Extrude the footprint polygon by `floors` levels on top of a plinth.
    # Procedural low-poly: parapet or sloped roof, window rows, door facing nearest path.
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    # ... extrusion implementation omitted: see Phase 4 bake/export steps.
    obj["bid"] = name


def main() -> None:
    reset_scene()
    geojson = load_geojson("data-src/osm_campus.geojson")
    facade = {}
    with open("data-src/facade_sheet.csv", newline="") as f:
        for row in csv.DictReader(f):
            facade[row["id"]] = row
    for feature in geojson.get("features", []):
        props = feature.get("properties") or {}
        bid = f"BLDG_{props.get('osm_id')}"
        style = facade.get(str(props.get("osm_id")), {})
        build_building(bid, feature.get("geometry") or {}, int(style.get("floors") or 1), style)
    bpy.ops.wm.save_as_mainfile(filepath="build/campus.blend")


if __name__ == "__main__":
    main()
