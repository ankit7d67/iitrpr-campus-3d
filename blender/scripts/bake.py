"""Headless Blender script: export the built campus scene to public/models/campus.glb.

Run:  blender -b build/campus.blend -P blender/scripts/bake.py

Two small baked textures keep the low-poly scene grounded without adding
materials (7-9):

  * `ground_bake.png` — a soft building shadow baked into the terrain's base
    colour for a fixed 10:30 IST summer sun (the default SunPanel time).
    Runtime directional shadows still follow the selected time; this is only a
    static contact cue, muted enough not to contradict a moving sun.
  * `window_emissive.png` — a 64px repeating atlas with one warm window tile.
    Repeating UVs on the BLDG facades make it glow as window rows at night;
    the web app only changes the material's emissive intensity (never geometry).

Ambient occlusion stays in per-vertex BYTE_COLOR attributes on the BLDG meshes.
The GLB therefore has 4 materials, 2 textures, and no extra triangles.
"""

import math
import os

import bpy
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODEL = os.path.join(ROOT, "public", "models", "campus.glb")
TEX_DIR = os.path.join(ROOT, "blender", "textures")

SHADOW_SIZE = 1024
SHADOW_FLOOR = 0.62          # ground brightness in full baked shadow
SUN_ELEV_DEG = 63.6         # 15 Jun, 10:30 IST — the app's default time
SUN_AZ_DEG = 99.9           # degrees clockwise from north
WINDOW_SIZE = 64
WINDOW_GLOW = (1.0, 0.72, 0.38)  # warm window colour in the emissive atlas


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c: float) -> float:
    c = min(1.0, max(0.0, c))
    return c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def convex_hull(points):
    """Monotone-chain 2-D hull (no shapely in Blender's Python)."""
    pts = sorted(set(points))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def point_in_poly(x: float, y: float, poly) -> bool:
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def write_image(name: str, pixels: np.ndarray, filename: str):
    """pixels: (H, W, 4) float32. Saves a PNG and returns the Blender image."""
    os.makedirs(TEX_DIR, exist_ok=True)
    img = bpy.data.images.get(name) or bpy.data.images.new(name, pixels.shape[1], pixels.shape[0], alpha=False)
    img.pixels.foreach_set(np.ascontiguousarray(pixels, dtype=np.float32).ravel())
    img.filepath_raw = os.path.join(TEX_DIR, filename)
    img.file_format = "PNG"
    img.save()
    return img


def make_window_emissive():
    """One warm window rectangle; UVs repeat it every 4 m horizontally / 3.5 m vertically."""
    n = WINDOW_SIZE
    px = np.zeros((n, n, 4), dtype=np.float32)
    px[:, :, 3] = 1.0
    px[22:42, 10:38, :3] = WINDOW_GLOW
    return write_image("window_emissive", px, "window_emissive.png")


def bake_ground_shadow(ground, buildings):
    """Rasterise a static sun shadow from building hulls into the terrain UV island.

    The directional shadow is baked at the default time only and blended with a
    generous penumbra, so it reads as contact darkening rather than a moving
    sun. Terrain slope shading is left to the runtime lights.
    """
    xs = [v.co.x for v in ground.data.vertices]
    ys = [v.co.y for v in ground.data.vertices]
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    w, h = max(xmax - xmin, 1.0), max(ymax - ymin, 1.0)
    n = SHADOW_SIZE

    # Scene axes are x=east, y=north. Shadow points opposite the sun's horizontal
    # direction; its length is height / tan(elevation).
    el = math.radians(SUN_ELEV_DEG)
    az = math.radians(SUN_AZ_DEG)
    length = 1.0 / math.tan(el)
    sx = -math.sin(az) * length
    sy = -math.cos(az) * length

    mask = np.zeros((n, n), dtype=np.float32)
    hulls = 0
    for obj in buildings:
        pts = [(v.co.x, v.co.y) for v in obj.data.vertices if v.co.x >= xmin and v.co.x <= xmax and v.co.y >= ymin and v.co.y <= ymax]
        if len(pts) < 3:
            continue
        hull = convex_hull(pts)
        if len(hull) < 3:
            continue
        zs = [v.co.z for v in obj.data.vertices]
        height = max(zs) - min(zs)
        if height <= 0:
            continue
        hulls += 1
        shadow = [(x + sx * height, y + sy * height) for x, y in hull]
        allx = [p[0] for p in hull] + [p[0] for p in shadow]
        ally = [p[1] for p in hull] + [p[1] for p in shadow]
        i0 = max(0, int((min(allx) - xmin) / w * n) - 2)
        i1 = min(n, int((max(allx) - xmin) / w * n) + 3)
        j0 = max(0, int((min(ally) - ymin) / h * n) - 2)
        j1 = min(n, int((max(ally) - ymin) / h * n) + 3)
        for j in range(j0, j1):
            y = ymin + (j + 0.5) / n * h
            for i in range(i0, i1):
                x = xmin + (i + 0.5) / n * w
                if point_in_poly(x, y, hull) or point_in_poly(x, y, shadow):
                    mask[j, i] = 1.0

    # 5-tap penumbra (~4 m on the ground at this resolution).
    soft = (mask + np.roll(mask, 1, 0) + np.roll(mask, -1, 0)
            + np.roll(mask, 1, 1) + np.roll(mask, -1, 1)) / 5.0
    factor = 1.0 - (1.0 - SHADOW_FLOOR) * soft

    base = bpy.data.materials["MAT_ground"].node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value
    rgb = np.array([base[0], base[1], base[2]], dtype=np.float32)[None, None, :] * factor[:, :, None]
    srgb = np.vectorize(linear_to_srgb)(rgb)
    px = np.ones((n, n, 4), dtype=np.float32)
    px[:, :, :3] = srgb
    img = write_image("ground_bake", px, "ground_bake.png")
    print(f"GROUND_SHADOW_OK hulls={hulls} shadow_coverage={100 * float((soft > 0.5).mean()):.1f}% "
          f"floor={SHADOW_FLOOR} size={n}")
    return img


def build_wall_material(mat, wall_colour, window_colour, window_scale: float = 2.0) -> None:
    """Procedural window rows via Wave texture bands + MixRGB, then AO (per-vertex BYTE_COLOR
    attribute "AO") multiplied in. No extra geometry, no textures, no new material."""
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.9
    tex = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (window_scale, window_scale, window_scale)
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MIX"
    mix.inputs["Fac"].default_value = 0.0
    mix.inputs["Color1"].default_value = wall_colour
    mix.inputs["Color2"].default_value = window_colour
    mix2 = nt.nodes.new("ShaderNodeMixRGB")
    mix2.blend_type = "MULTIPLY"
    mix2.inputs["Fac"].default_value = 1.0
    mix2.inputs["Color2"].default_value = (1.0, 1.0, 1.0, 1.0)
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "AO"
    nt.links.new(tex.outputs["Generated"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Color"], mix.inputs["Fac"])
    nt.links.new(mix.outputs["Color"], mix2.inputs["Color1"])
    nt.links.new(attr.outputs["Color"], mix2.inputs["Color2"])
    nt.links.new(mix2.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    # Night glow: the repeating window atlas is the ONLY emissive source, so
    # walls stay dark and only the little window tiles light up.
    em = nt.nodes.new("ShaderNodeTexImage")
    em.name = "WindowEmissive"
    em.image = make_window_emissive()
    em.extension = "REPEAT"
    em.interpolation = "Closest"
    nt.links.new(em.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = 1.0


def wire_ground_texture(img) -> None:
    mat = bpy.data.materials.get("MAT_ground")
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.get("GroundShadow") or nt.nodes.new("ShaderNodeTexImage")
    tex.name = "GroundShadow"
    tex.image = img
    for link in list(bsdf.inputs["Base Color"].links):
        nt.links.remove(link)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])


def bake_ao(objects) -> None:
    """Bake ambient occlusion into per-vertex BYTE_COLOR attributes on the BLDG meshes.
    Vertical AO gradient: ~0.55 at the plinth base rising to ~1.0 at the roof top."""
    baked = 0
    for o in objects:
        if not o.name.startswith("BLDG_"):
            continue
        mesh = o.data
        if mesh is None or not mesh.vertices:
            continue
        zs = [v.co.z for v in mesh.vertices]
        height = max(zs) - min(zs)
        if height <= 0.0:
            continue
        z0 = min(zs)
        attr = mesh.color_attributes.get("AO") or mesh.color_attributes.new(name="AO", type="BYTE_COLOR", domain="POINT")
        for i, v in enumerate(mesh.vertices):
            t = (v.co.z - z0) / height
            ao = min(1.0, max(0.0, 0.55 + 0.45 * t))
            attr.data[i].color = (ao, ao, ao, 1.0)
        baked += 1
    print(f"AO_OK baked_meshes={baked}")


def export_glb() -> None:
    os.makedirs(os.path.dirname(MODEL), exist_ok=True)
    objects = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    wall = bpy.data.materials.get("MAT_wall")
    if wall is not None:
        build_wall_material(
            wall,
            (srgb_to_linear(0.79), srgb_to_linear(0.76), srgb_to_linear(0.71), 1.0),
            (srgb_to_linear(0.83), srgb_to_linear(0.87), srgb_to_linear(0.92), 1.0),
        )
    bake_ao(objects)
    ground = bpy.data.objects.get("GROUND")
    if ground is not None:
        wire_ground_texture(bake_ground_shadow(
            ground, [o for o in objects if o.name.startswith("BLDG_")]))
    bpy.ops.export_scene.gltf(
        filepath=MODEL,
        export_format="GLB",
        export_apply=True,
        export_extras=True,
        export_cameras=False,
        export_lights=False,
        export_yup=True,
    )


def main() -> None:
    objects = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    tris = sum(len(o.data.loop_triangles) if o.data.loop_triangles else 0 for o in objects)
    if not tris:
        for o in objects:
            o.data.calc_loop_triangles()
        tris = sum(len(o.data.loop_triangles) for o in objects)
    export_glb()
    size = os.path.getsize(MODEL)
    print(f"GLB_OK objects={len(objects)} meshes={len(bpy.data.meshes)} tris={tris} "
          f"materials={len(bpy.data.materials)} size={size} bytes -> public/models/campus.glb")


if __name__ == "__main__":
    main()
