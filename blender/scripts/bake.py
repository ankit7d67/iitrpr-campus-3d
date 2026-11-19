"""Headless Blender script: export the built campus scene to public/models/campus.glb.

Run:  blender -b build/campus.blend -P blender/scripts/bake.py

No textures and no lightmaps are baked: the campus.glb stays a low-poly mesh with four
materials, and lighting/shadows are computed at runtime by React Three Fiber (the app's
SunPanel changes the sun direction, so a baked shadow map would be wrong). Vertex-colour
AO, if added later, must keep the GLB under the material/texture budgets.
"""

import os

import bpy

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODEL = os.path.join(ROOT, "public", "models", "campus.glb")


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def add_window_mask(mat, wall_colour, window_colour, window_scale: float = 2.0) -> None:
    """Cheap procedural window rows via Wave texture bands + colour ramp. No extra geometry,
    no textures, no new material."""
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
    wave.bands_direction = "X"
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.45
    ramp.color_ramp.elements[0].color = wall_colour
    ramp.color_ramp.elements[1].position = 0.55
    ramp.color_ramp.elements[1].color = window_colour
    nt.links.new(tex.outputs["Generated"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Color"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return


def export_glb() -> None:
    os.makedirs(os.path.dirname(MODEL), exist_ok=True)
    wall = bpy.data.materials.get("MAT_wall")
    if wall is not None:
        add_window_mask(
            wall,
            (srgb_to_linear(0.79), srgb_to_linear(0.76), srgb_to_linear(0.71), 1.0),
            (srgb_to_linear(0.83), srgb_to_linear(0.87), srgb_to_linear(0.92), 1.0),
        )
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
