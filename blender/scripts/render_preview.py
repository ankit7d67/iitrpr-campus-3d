"""Render PNG previews of the Blender campus scene into build/preview/.

Run:  blender -b build/campus.blend -P blender/scripts/render_preview.py

Writes main.png (three-quarter view), aerial.png (top-down) and close.png (near Nalanda
library if that building exists). EEVEE Next is tried first; if the headless GPU context is
unavailable the script falls back to Cycles on CPU.
"""

import json
import math
import os

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIR = os.path.join(ROOT, "build", "preview")


def scene_bounds() -> tuple[Vector, Vector]:
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or obj.name in {"GROUND"}:
            continue
        for corner in obj.bound_box:
            p = obj.matrix_world @ Vector(corner)
            mins = Vector((min(mins[i], p[i]) for i in range(3)))
            maxs = Vector((max(maxs[i], p[i]) for i in range(3)))
    if mins.x > 1e8:
        return Vector((-100, -100, 0)), Vector((100, 100, 20))
    return mins, maxs


def add_camera() -> bpy.types.Object:
    cam_data = bpy.data.cameras.new("PREVIEW_CAM")
    cam_data.lens = 45
    cam_data.clip_start = 1.0
    cam_data.clip_end = 50000.0
    cam = bpy.data.objects.new("PREVIEW_CAM", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    target = bpy.data.objects.new("PREVIEW_TARGET", None)
    target.location = Vector((0, 0, 0))
    bpy.context.collection.objects.link(target)
    con = cam.constraints.new(type="TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    return cam


def add_light() -> None:
    data = bpy.data.lights.new("PREVIEW_SUN", type="SUN")
    data.energy = 3.0
    data.angle = math.radians(8)
    sun = bpy.data.objects.new("PREVIEW_SUN", data)
    sun.rotation_euler = (math.radians(50), 0.0, math.radians(35))
    bpy.context.collection.objects.link(sun)


def setup_world() -> None:
    world = bpy.data.worlds.new("PREVIEW_WORLD") if not bpy.data.worlds else bpy.data.worlds[0]
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.72, 0.78, 0.86, 1.0)
        bg.inputs[1].default_value = 1.0


def place(cam: bpy.types.Object, target: Vector, direction: Vector, distance: float) -> None:
    d = direction.normalized() * distance
    cam.location = target + d


def render(path: str) -> None:
    scene = bpy.context.scene
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = path
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
        scene.eevee.taa_render_samples = 32
        bpy.ops.render.render(write_still=True)
    except Exception as exc:  # headless GPU context missing
        print(f"EEVEE failed ({exc}); falling back to Cycles")
        scene.render.engine = "CYCLES"
        scene.cycles.samples = 16
        scene.cycles.use_denoising = True
        bpy.ops.render.render(write_still=True)


def project(lat: float, lon: float, lat0: float, lon0: float) -> Vector:
    phi = math.radians(lat)
    m_lat = 111132.92 - 559.82 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi)
    return Vector(((lon - lon0) * m_lon, (lat - lat0) * m_lat, 0.0))


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    setup_world()
    add_light()
    cam = add_camera()
    mins, maxs = scene_bounds()
    centre = (mins + maxs) / 2.0
    size = max(maxs.x - mins.x, maxs.y - mins.y)
    bpy.data.objects["PREVIEW_TARGET"].location = centre

    place(cam, centre, Vector((1.1, -1.5, 0.85)), size * 1.15)
    render(os.path.join(OUT_DIR, "main.png"))

    place(cam, centre, Vector((0.15, -0.15, 1.0)), size * 1.25)
    render(os.path.join(OUT_DIR, "aerial.png"))

    close_target = centre
    campus_path = os.path.join(ROOT, "public", "data", "campus.json")
    bbox_path = os.path.join(ROOT, "data-src", "campus_bbox.json")
    if os.path.exists(campus_path) and os.path.exists(bbox_path):
        campus = json.load(open(campus_path))
        bb = json.load(open(bbox_path))
        south, north, west, east = (float(x) for x in bb["boundingbox"][:4])
        lat0, lon0 = (south + north) / 2.0, (west + east) / 2.0
        for b in campus.get("buildings", []):
            if "nalanda" in (b.get("name") or "").lower():
                close_target = project(b["location"]["lat"], b["location"]["lon"], lat0, lon0)
                close_target.z = 8.0
                break
    bpy.data.objects["PREVIEW_TARGET"].location = close_target
    place(cam, close_target, Vector((1.0, -1.2, 0.5)), size * 0.30)
    render(os.path.join(OUT_DIR, "close.png"))

    print(f"PREVIEW_OK -> {OUT_DIR}")


if __name__ == "__main__":
    main()
