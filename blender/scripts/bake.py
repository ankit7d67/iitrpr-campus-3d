"""Headless Blender script: export the built campus scene to public/models/campus.glb.

Run:  blender -b build/campus.blend -P blender/scripts/bake.py

No textures and no lightmaps are baked: the campus.glb stays a low-poly mesh with four
materials, and lighting/shadows are computed at runtime by React Three Fiber (the app's
SunPanel changes the sun direction, so a baked shadow map would be wrong). Ambient occlusion
is baked into per-vertex BYTE_COLOR attributes on the BLDG meshes (not into the sun/shadow
path), so it stays valid with the runtime sun.
"""

import os

import bpy

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODEL = os.path.join(ROOT, "public", "models", "campus.glb")


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


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
        attr = mesh.color_attributes.new(name="AO", type="BYTE_COLOR", domain="POINT")
        for i, v in enumerate(mesh.vertices):
            t = (v.co.z - z0) / height
            ao = min(1.0, max(0.0, 0.55 + 0.45 * t))
            attr.data[i].color = (ao, ao, ao, 1.0)
        baked += 1
    print(f"AO_OK baked_meshes={baked}")


def export_glb() -> None:
    os.makedirs(os.path.dirname(MODEL), exist_ok=True)
    wall = bpy.data.materials.get("MAT_wall")
    if wall is not None:
        build_wall_material(
            wall,
            (srgb_to_linear(0.79), srgb_to_linear(0.76), srgb_to_linear(0.71), 1.0),
            (srgb_to_linear(0.83), srgb_to_linear(0.87), srgb_to_linear(0.92), 1.0),
        )
    bake_ao([o for o in bpy.context.scene.objects if o.type == "MESH"])
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
